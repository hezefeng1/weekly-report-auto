import os
import requests
import json
import re
from datetime import datetime, timedelta
from common.feishu import get_tenant_access_token

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")


def generate_policy_report():
    """调用 DeepSeek API 生成政策追踪报告"""
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
- 搜索结果页
- 摘要页

## 城市清单

**四川省**：达州市、德阳市、乐山市、泸州市、眉山市、绵阳市、南充市、西昌市、资阳市、自贡市、成都市、广安市、广元市

**重庆市**：重庆市

**云南省**：德宏傣族景颇族自治州、昆明市、曲靖市

**贵州省**：毕节市、贵阳市、黔东南苗族侗族自治州、遵义市、六盘水市、黔西南布依族苗族自治州

## 搜索要求

### 政策范围
- 部门来源：人社局、就业局相关政策
- 补贴类型（针对企业的奖补）：
  - 稳岗补贴/稳岗返还补贴
  - 就业补贴、培训补贴
  - 残疾人安置补贴
  - 扩岗补贴、吸纳就业补贴
  - 招工/用工/招聘补贴
  - 见习补贴/见习基地
  - 岗位补贴、引才奖励
  - 返乡就业补助、跨省就业补助

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

### 链接质量要求
- URL 必须是政策原文页面的直接链接，不含 `?` 或 `&` 追踪参数
- 禁止输出搜索结果页、列表页、摘要页的链接
- 链接格式必须为 `http://xxx.gov.cn/xxx/xxx.html` 形式
- 如果无法获取稳定的政策原文链接，宁可该条政策不输出

### 数据处理规则
- 省级政策覆盖多个城市：城市列用顿号分隔
- 市级政策：城市列填写具体城市名称
- 同一城市多个政策：每个政策单独一行
- 无新政策的城市：不输出该城市

## 输出前自检清单

- [ ] 日期合规：开放申请日期 ≥ 2026-01-01
- [ ] 日期有效：截止日期 > 当前日期
- [ ] 链接原文合规：URL含 /art/、/zhengce/、/policy/ 等路径
- [ ] 链接无追踪参数：URL不含 ? 或 &
- [ ] 来源合规：仅gov.cn官方域名
- [ ] 无公示文件
- [ ] 格式极简：仅表格，无多余文字

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
    """
    解析 Markdown 表格，返回 headers 和 rows（列表形式）
    """
    lines = markdown_text.strip().split('\n')
    if len(lines) < 2:
        return None, None

    data_lines = [line for line in lines if '---' not in line]
    if len(data_lines) < 2:
        return None, None

    header_line = data_lines[0]
    headers = [h.strip() for h in header_line.split('|') if h.strip()]

    rows = []
    for line in data_lines[1:]:
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if cells:
            rows.append(cells)

    return headers, rows


def extract_link(text):
    """提取 Markdown 链接 [文本](URL) 中的 URL，返回 (显示文本, URL)"""
    match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', text)
    if match:
        return match.group(1), match.group(2)
    return text, None


def send_rich_text_message(access_token, receive_id, rows, region="西南四省"):
    """发送飞书富文本消息（完整 6 列表格）"""
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置，请设置 GitHub Secret")
        return

    md_lines = []
    md_lines.append(f"# 📋 2026年人社补贴政策追踪（{region}）\n")

    # 完整 6 列表头（去掉政策原文链接列，因为链接已嵌入政策名称）
    md_lines.append("| 省份 | 城市 | 政策名称 | 核心申请条件 | 补贴标准/金额 | 截止日期 |")
    md_lines.append("|------|------|----------|--------------|----------------|----------|")

    policy_count = 0
    max_policies = 20
    for row in rows:
        if policy_count >= max_policies:
            break
        if len(row) < 7:
            continue
        province = row[0]
        city = row[1]
        policy_name_raw = row[2]
        condition = row[3] if len(row) > 3 else "—"
        subsidy = row[4] if len(row) > 4 else "—"
        deadline = row[5] if len(row) > 5 else "详见原文"

        display_name, link_url = extract_link(policy_name_raw)

        if link_url:
            # 清理链接中的追踪参数
            clean_url = re.sub(r'\?.*$', '', link_url)
            policy_cell = f"[{display_name}]({clean_url})"
        else:
            policy_cell = display_name

        md_lines.append(f"| {province} | {city} | {policy_cell} | {condition} | {subsidy} | {deadline} |")
        policy_count += 1

    total_count = len(rows)
    if total_count > max_policies:
        md_lines.append(f"\n📊 共找到 {total_count} 条政策，当前展示前 {max_policies} 条")
    else:
        md_lines.append(f"\n📊 共找到 {total_count} 条政策")

    md_content = "\n".join(md_lines)

    send_url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "receive_id": receive_id,
        "msg_type": "post",
        "content": json.dumps({
            "zh_cn": {
                "title": f"2026年人社补贴政策追踪（{region}）",
                "content": [
                    [{"tag": "md", "text": md_content}]
                ]
            }
        })
    }

    resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ 发送消息失败: {resp.text}")
        resp.raise_for_status()

    print(f"  ✅ 富文本消息发送成功，共 {policy_count} 条政策")


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
    headers, rows = parse_markdown_table_to_list(md_content)
    if not headers or not rows:
        print("  ❌ 未能解析出表格数据，请检查 DeepSeek 输出格式")
        return

    print(f"  ✅ 解析成功，表头: {len(headers)} 列，数据: {len(rows)} 行")

    print("\n3. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    print("\n4. 发送富文本消息...")
    send_rich_text_message(token, RECEIVE_OPEN_ID_POLICY, rows, "西南四省")

    print("\n✅ 政策追踪报告发送完成！")


if __name__ == "__main__":
    main()
