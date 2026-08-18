import os
import requests
import json
import re
from datetime import datetime
from common.feishu import get_tenant_access_token

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# ==================== 屏蔽词规则 ====================
SENSITIVE_RULES_RAW = """
发放,http
贴 补
卜帖
人力社,高温补贴
国家,高温补贴
最新卜帖
^(通 知\.)
(zip|exe|rar|
pdf|doc|docx)$
人力社
^(\d|\_|\.|\-)
*(zip|exe|rar)$
一业一查
部门联合双随机抽查工作计划
人力社,津贴
人力社,补助
人力社,补贴
人力社,居民补贴
人力社,综合补贴
人力社,个人补贴
人力社,补贴
居 民补 贴
综 合补 贴
京东商城,国家补贴
京东商城,平台补贴
工资补贴,扫描二维码
社保局工资补贴
人力社,工资补贴
薪资补贴,微信扫码
人力社,薪资补贴
人力社,社保补贴
人社部个人劳动补贴
国家财政部补贴
社保补贴,微信扫码
人社局,补贴
国家,补贴通知
补贴,申领
裁员名单
""".strip().splitlines()

def load_sensitive_rules(lines):
    rules = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        keywords = [kw.strip() for kw in line.split(',') if kw.strip()]
        if keywords:
            rules.append(keywords)
    return rules

SENSITIVE_RULES = load_sensitive_rules(SENSITIVE_RULES_RAW)

def filter_sensitive(text):
    if not text:
        return text
    text_lower = text.lower()
    for keywords in SENSITIVE_RULES:
        if all(kw.lower() in text_lower for kw in keywords):
            for kw in keywords:
                text = text.replace(kw, "***")
                kw_no_space = kw.replace(" ", "")
                if kw_no_space != kw:
                    text = text.replace(kw_no_space, "***")
    return text
# ==================================================


def generate_policy_report():
    today = datetime.now().strftime("%Y年%m月%d日")
    system_prompt = """你是人社政策情报分析AI。

任务：搜索2026年1月1日之后新发布的企业补贴政策，覆盖四川省、重庆市、云南省、贵州省，输出表格格式政策追踪报告。

## 强制限制

### 绝对禁止
- 禁止生成任何中间文件
- 禁止在最终文档中添加总结、建议等额外文字
- 禁止输出官网首页链接（必须输出政策原文链接）
- 禁止链接带追踪参数
- 禁止使用短链接
- 链接必须指向政策原文页面

### 明确排除的文件类型
- 标题包含"公示"的所有文件
- 任何涉及资金分配、补贴发放名单的公示文件
- "灵活就业社保补贴"相关文件
- "创业担保贷款"相关文件

### 明确排除的链接类型
- 官网首页
- 栏目页
- 列表页
- 转发/转载页面

## 城市清单

**四川省**：达州市、德阳市、乐山市、泸州市、眉山市、绵阳市、南充市、西昌市、资阳市、自贡市、成都市、广安市、广元市

**重庆市**：重庆市

**云南省**：德宏傣族景颇族自治州、昆明市、曲靖市

**贵州省**：毕节市、贵阳市、黔东南苗族侗族自治州、遵义市、六盘水市、黔西南布依族苗族自治州

## 搜索要求

### 政策范围
- 部门来源：人社局、就业局相关政策
- 补贴类型（针对企业的奖补）：稳岗补贴/稳岗返还、就业补贴、培训补贴、残疾人安置补贴、扩岗补贴、吸纳就业补贴、招工补贴、见习补贴、岗位补贴、引才奖励、返乡就业补贴、跨省就业补助

### 时间范围
- 发布日期：2026年1月1日之后
- 截止日期必须晚于当前日期

## 核心信息要素

| 字段 | 要求 |
|------|------|
| 省份 | 政策发布省份 |
| 城市 | 适用城市（多个用顿号分隔） |
| 政策名称 | 完整政策标题（作为链接文字） |
| 核心申请条件 | 企业适用条件 |
| 补贴标准/金额 | 具体金额或比例 |
| 开放申请及截止日期 | 格式：YYYY-MM-DD |
| 政策原文链接 | 可点击的官方政策原文URL |

## 搜索关键词组合

对每个城市使用以下关键词搜索（site:.gov.cn）：
稳岗补贴、稳岗返还、就业补贴、培训补贴、扩岗补贴、吸纳就业补贴、招工补贴、见习补贴、引才奖励、返乡就业补贴、残疾人安置补贴

## 输出格式

### 格式要求
- 只生成一个 Markdown 表格
- 表格表头：省份 | 城市 | 政策名称 | 核心申请条件 | 补贴标准/金额 | 开放申请及截止日期 | 政策原文链接
- 政策名称列：使用 `[政策名称](政策原文URL)` 格式

### 数据处理规则
- 省级政策覆盖多个城市：城市列用顿号分隔
- 市级政策：城市列填写具体城市名称
- 同一城市多个政策：每个政策单独一行
- 无新政策的城市：不输出该城市

请开始生成报告。"""

    user_prompt = f"请生成2026年人社补贴政策追踪报告（西南四省），政策发布日期为2026年1月1日之后，截止当前日期（{today}）仍未过期的政策。严格按照固定格式输出。"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
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
    match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', text)
    if match:
        return match.group(1), match.group(2)
    return text, None


def send_card_message(access_token, receive_id, rows, region="西南四省"):
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置")
        return

    # 限制最多10行，卡片表格不宜太多
    rows_to_send = rows[:10]

    # 构建表格行
    table_rows = []
    for row in rows_to_send:
        if len(row) < 5:
            continue
        province = row[0] if len(row) > 0 else ""
        city = row[1] if len(row) > 1 else ""
        policy_name_raw = row[2] if len(row) > 2 else ""
        deadline = row[5] if len(row) > 5 else "详见原文"

        # 过滤屏蔽词（纯文本部分）
        province = filter_sensitive(province)
        city = filter_sensitive(city)
        deadline = filter_sensitive(deadline)

        display_name, link_url = extract_link(policy_name_raw)
        if not display_name:
            display_name = policy_name_raw
        display_name = filter_sensitive(display_name)
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."

        # 表格每一行数据
        row_cells = [
            {"text": province},
            {"text": city},
            {"text": display_name, "href": link_url} if link_url else {"text": display_name},
            {"text": deadline}
        ]
        table_rows.append(row_cells)

    if not table_rows:
        print("  ⚠️ 没有有效的政策数据可展示")
        return

    # ✅ 修正后的卡片结构：扁平化，顶层直接是 config 和 elements
    card = {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"📋 2026年人社补贴政策追踪（{region}）"
            }
        },
        "elements": [
            {
                "tag": "table",
                "columns": [
                    {"name": "省份", "width": 80},
                    {"name": "城市", "width": 80},
                    {"name": "政策名称", "width": 200},
                    {"name": "截止日期", "width": 120}
                ],
                "rows": table_rows,
                "paginate": True,
                "page_size": 10
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"📊 共 {len(rows)} 条政策（仅展示前10条）"
                    }
                ]
            }
        ]
    }

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "receive_id": receive_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False)
    }

    # 打印完整入参（脱敏）
    print("\n" + "=" * 60)
    print("📤 完整入参（脱敏 receive_id）:")
    print("=" * 60)
    debug_payload = payload.copy()
    debug_payload["receive_id"] = "***"
    print(json.dumps(debug_payload, ensure_ascii=False, indent=2))
    print("=" * 60 + "\n")

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ 发送失败: {resp.text}")
        resp.raise_for_status()

    print(f"  ✅ 卡片消息发送成功，共 {len(rows_to_send)} 条政策")


def main():
    print("=" * 50)
    print("📋 人社补贴政策追踪（西南四省）")
    print("=" * 50)

    print("\n1. 生成政策追踪报告...")
    md_content = generate_policy_report()
    print("=== DeepSeek 返回的完整 Markdown 内容 ===")
    print(md_content)
    print("=== 内容结束 ===")

    print("\n2. 解析 Markdown 表格...")
    rows = parse_markdown_table_to_list(md_content)
    if not rows:
        print("  ❌ 未能解析出表格数据")
        return

    print(f"  ✅ 解析成功，表头: {len(rows[0])} 列，数据: {len(rows)} 行")

    print("\n3. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    print("\n4. 发送消息卡片...")
    send_card_message(token, RECEIVE_OPEN_ID_POLICY, rows, "西南四省")

    print("\n✅ 政策追踪报告发送完成！")


if __name__ == "__main__":
    main()
