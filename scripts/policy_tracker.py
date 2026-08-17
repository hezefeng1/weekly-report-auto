import os
import requests
import json
import re
import time
from datetime import datetime
from common.feishu import get_tenant_access_token

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")


# ========== 敏感词屏蔽规则（精简，保留核心） ==========
SENSITIVE_RULES = [
    {"type": "any", "words": ["人力社"]},
    {"type": "any", "words": ["卜帖"]},
    {"type": "any", "words": ["贴 补"]},
    {"type": "any", "words": ["发放"]},
    {"type": "any", "words": ["裁员名单"]},
    {"type": "all", "words": ["国家", "补贴通知"]},
    {"type": "all", "words": ["补贴", "申领"]},
    {"type": "regex", "pattern": r"(zip|exe|rar|pdf|doc|docx)$"},
]


def clean_text_for_audit(text):
    """清洗文本，保证返回非空字符串"""
    if not text:
        return "无"
    cleaned = str(text)
    for rule in SENSITIVE_RULES:
        if rule["type"] == "all":
            words = rule["words"]
            if all(w in cleaned for w in words):
                for w in words:
                    cleaned = cleaned.replace(w, "***")
        elif rule["type"] == "regex":
            pattern = rule["pattern"]
            if re.search(pattern, cleaned, re.IGNORECASE):
                cleaned = re.sub(pattern, "***", cleaned, flags=re.IGNORECASE)
        elif rule["type"] == "any":
            for w in rule["words"]:
                cleaned = cleaned.replace(w, "***")
    cleaned = cleaned.strip()
    # 去除多余空白和换行
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned if cleaned else "无"


def generate_policy_report():
    """调用 DeepSeek API 生成政策追踪报告"""
    today = datetime.now().strftime("%Y年%m月%d日")
    system_prompt = """你是人社政策情报分析AI。
任务：搜索2026年1月1日之后新发布的企业补贴政策，覆盖四川省、重庆市、云南省、贵州省，输出表格格式政策追踪报告。

## 强制限制
- 禁止生成任何中间文件
- 禁止在最终文档中添加总结、建议等额外文字
- 禁止输出官网首页链接（必须输出政策原文链接）
- 禁止链接带追踪参数
- 禁止使用短链接
- 链接必须指向政策原文页面

## 明确排除
- 标题包含"公示"的所有文件
- 任何涉及资金分配、补贴发放名单的公示文件
- "灵活就业社保补贴"相关文件
- "创业担保贷款"相关文件
- 官网首页、栏目页、列表页、转发/转载页面

## 城市清单
四川省：达州市、德阳市、乐山市、泸州市、眉山市、绵阳市、南充市、西昌市、资阳市、自贡市、成都市、广安市、广元市
重庆市：重庆市
云南省：德宏傣族景颇族自治州、昆明市、曲靖市
贵州省：毕节市、贵阳市、黔东南苗族侗族自治州、遵义市、六盘水市、黔西南布依族苗族自治州

## 搜索要求
- 部门来源：人社局、就业局相关政策
- 补贴类型：稳岗补贴/稳岗返还、就业补贴、培训补贴、残疾人安置补贴、扩岗补贴、吸纳就业补贴、招工补贴、见习补贴、岗位补贴、引才奖励、返乡就业补贴、跨省就业补助
- 发布日期：2026年1月1日之后
- 截止日期必须晚于当前日期

## 输出格式
只生成一个 Markdown 表格，表头：省份 | 城市 | 政策名称 | 核心申请条件 | 补贴标准/金额 | 开放申请及截止日期 | 政策原文链接
政策名称列使用 `[政策名称](政策原文URL)` 格式。
请开始生成报告。"""

    user_prompt = f"请生成2026年人社补贴政策追踪报告（西南四省），政策发布日期为2026年1月1日之后，截止当前日期（{today}）仍未过期的政策。严格按照固定格式输出。"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.3,
        "stream": False
    }
    print("  📡 正在联网搜索西南四省人社补贴政策...")
    resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=300)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    print(f"  ✅ 生成完成，共 {len(content)} 字符")
    return content


def parse_markdown_table_to_list(markdown_text):
    """解析 Markdown 表格，返回行列表"""
    lines = markdown_text.strip().split('\n')
    if len(lines) < 2:
        return None
    data_lines = [line for line in lines if '---' not in line]
    if len(data_lines) < 2:
        return None
    rows = []
    for line in data_lines[1:]:
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if cells:
            rows.append(cells)
    return rows


def extract_link(text):
    """提取 Markdown 链接，返回 (显示文本, URL)"""
    match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', text)
    if match:
        return match.group(1), match.group(2)
    return text, None


def send_rich_text_message(access_token, receive_id, rows, region="西南四省"):
    """按省份分组发送飞书富文本消息"""
    if not receive_id:
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置")
        return

    # 按省份分组
    province_groups = {}
    for row in rows:
        if len(row) < 7:
            continue
        prov = row[0]
        province_groups.setdefault(prov, []).append(row)

    for province, province_rows in province_groups.items():
        total = len(province_rows)
        MAX_PER_BATCH = 15
        for start in range(0, total, MAX_PER_BATCH):
            batch = province_rows[start:start + MAX_PER_BATCH]
            batch_num = start // MAX_PER_BATCH + 1
            total_batches = (total + MAX_PER_BATCH - 1) // MAX_PER_BATCH

            # ----- 构造 content 二维数组 -----
            content_2d = []

            # 标题
            title = f"2026年人社补贴政策追踪 · {province}"
            if total_batches > 1:
                title += f"（{batch_num}/{total_batches}）"
            content_2d.append([{"tag": "text", "text": clean_text_for_audit(title)}])

            # 分隔线
            content_2d.append([{"tag": "text", "text": "─────────────────────"}])

            # 每条政策
            for row in batch:
                province_raw, city_raw, policy_raw, _, _, deadline_raw, _ = row[:7]

                province_cleaned = clean_text_for_audit(province_raw)
                city_cleaned = clean_text_for_audit(city_raw)
                display_name, link_url = extract_link(policy_raw)
                display_name = clean_text_for_audit(display_name) if display_name else "政策"
                deadline_cleaned = clean_text_for_audit(deadline_raw) if deadline_raw else "详见原文"

                # 地点 + 截止日期
                location_text = f"📍 {province_cleaned}｜{city_cleaned}  ⏰ {deadline_cleaned}"
                content_2d.append([{"tag": "text", "text": location_text}])

                # 政策链接
                if link_url:
                    content_2d.append([{"tag": "a", "text": f"📄 {display_name}", "href": link_url}])
                else:
                    content_2d.append([{"tag": "text", "text": f"📄 {display_name}"}])

                # 分隔线
                content_2d.append([{"tag": "text", "text": "─────────────────────"}])

            # 底部统计
            footer = f"📊 本页 {len(batch)} 条，{province} 共 {total} 条"
            if total_batches > 1:
                footer += f"（第 {batch_num}/{total_batches} 部分）"
            content_2d.append([{"tag": "text", "text": clean_text_for_audit(footer)}])

            # ----- 构建完整 payload -----
            post_content = {
                "post": {
                    "zh_cn": {
                        "title": f"人社补贴政策 · {province}",
                        "content": content_2d
                    }
                }
            }
            content_json = json.dumps(post_content, ensure_ascii=False)

            # 打印调试信息（关键！）
            print(f"\n  🔍 调试：准备发送 {province} 第 {batch_num} 批")
            print(f"  🔍 content 前 500 字符：\n{content_json[:500]}...")
            print(f"  🔍 content 总长度：{len(content_json)}")

            payload = {
                "receive_id": receive_id,
                "msg_type": "post",
                "content": content_json
            }

            send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
            if resp.status_code != 200:
                print(f"  ❌ {province} 第 {batch_num} 批发送失败")
                print(f"  ❌ 响应内容：{resp.text}")
                resp.raise_for_status()
            else:
                print(f"  ✅ {province} 第 {batch_num}/{total_batches} 批发送成功（{len(batch)} 条）")
            time.sleep(1)


def main():
    print("=" * 50)
    print("📋 人社补贴政策追踪（西南四省）")
    print("=" * 50)

    print("\n1. 生成政策追踪报告...")
    md_content = generate_policy_report()
    print("=== DeepSeek 返回的完整内容 ===")
    print(md_content)
    print("=== 内容结束 ===")

    print("\n2. 解析表格...")
    rows = parse_markdown_table_to_list(md_content)
    if not rows:
        print("  ❌ 未能解析出表格数据")
        return
    print(f"  ✅ 解析成功，共 {len(rows)} 条政策")

    print("\n3. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    print("\n4. 按省份分组发送富文本消息（已清洗敏感词，自动分批）...")
    send_rich_text_message(token, RECEIVE_OPEN_ID_POLICY, rows, "西南四省")

    print("\n✅ 政策追踪报告发送完成！")


if __name__ == "__main__":
    main()
