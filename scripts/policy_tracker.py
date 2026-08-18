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

# 城市官网首页映射（根据实际地址调整）
CITY_WEBSITE = {
    "成都市": "http://cdhrss.chengdu.gov.cn",
    "绵阳市": "http://rsj.my.gov.cn",
    "德阳市": "http://rsj.deyang.gov.cn",
    "泸州市": "http://rsj.luzhou.gov.cn",
    "南充市": "http://rsj.nanchong.gov.cn",
    "宜宾市": "http://rsj.yibin.gov.cn",
    "达州市": "http://rsj.dazhou.gov.cn",
    "广安市": "http://rsj.guang-an.gov.cn",
    "眉山市": "http://rsj.ms.gov.cn",
    "自贡市": "http://rsj.zg.gov.cn",
    "乐山市": "http://rsj.leshan.gov.cn",
    "广元市": "http://rsj.cngy.gov.cn",
    "资阳市": "http://rsj.ziyang.gov.cn",
    "西昌市": "http://rsj.xichang.gov.cn",
    "重庆市": "http://rlsbj.cq.gov.cn",
    "昆明市": "http://rsj.km.gov.cn",
    "曲靖市": "http://rsj.qj.gov.cn",
    "德宏傣族景颇族自治州": "http://rsj.dh.gov.cn",
    "贵阳市": "http://rsj.guiyang.gov.cn",
    "遵义市": "http://rsj.zunyi.gov.cn",
    "毕节市": "http://rsj.bijie.gov.cn",
    "六盘水市": "http://rsj.gzlps.gov.cn",
    "黔东南苗族侗族自治州": "http://rsj.qdn.gov.cn",
    "黔西南布依族苗族自治州": "http://rsj.qxn.gov.cn",
}


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


def get_website_by_city(city):
    if city in CITY_WEBSITE:
        return CITY_WEBSITE[city]
    # 尝试去掉“市”后匹配
    city_simple = city.replace("市", "")
    for key in CITY_WEBSITE:
        if key.replace("市", "") == city_simple:
            return CITY_WEBSITE[key]
    return f"https://www.baidu.com/s?wd={city} 人社局"


def send_rich_text_message(access_token, receive_id, rows, region="西南四省"):
    """发送富文本消息 - 最安全结构（每段一个元素）"""
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置")
        return

    # 只发前8条（确保极简）
    rows_to_send = rows[:8]

    # 构建 content 二维数组
    content_blocks = []

    # 标题
    content_blocks.append([
        {"tag": "text", "text": f"📋 2026年人社补贴政策追踪（{region}）"}
    ])
    content_blocks.append([
        {"tag": "text", "text": " "}
    ])

    # 逐条政策
    for idx, row in enumerate(rows_to_send):
        if len(row) < 5:
            continue
        province = row[0] if len(row) > 0 else ""
        city = row[1] if len(row) > 1 else ""
        policy_name_raw = row[2] if len(row) > 2 else ""
        deadline = row[5] if len(row) > 5 else "详见原文"

        # 提取纯文本名称
        display_name, _ = extract_link(policy_name_raw)
        if not display_name:
            display_name = policy_name_raw
        # 截断过长的名称（可选）
        if len(display_name) > 50:
            display_name = display_name[:47] + "..."

        # 获取官网首页
        website = get_website_by_city(city)

        # 段落1：省份+城市（text）
        content_blocks.append([
            {"tag": "text", "text": f"📍 {province}｜{city}"}
        ])

        # 段落2：政策名称（text，不加链接，避免a标签）
        content_blocks.append([
            {"tag": "text", "text": f"   {display_name}"}
        ])

        # 段落3：官网链接（单独一个a标签）
        content_blocks.append([
            {"tag": "a", "text": "🏢 当地人社局官网", "href": website}
        ])

        # 段落4：截止日期（text）
        content_blocks.append([
            {"tag": "text", "text": f"   ⏰ 截止：{deadline}"}
        ])

        # 分隔线（除了最后一条）
        if idx < len(rows_to_send) - 1:
            content_blocks.append([
                {"tag": "text", "text": "─────────────────────"}
            ])

    # 底部统计
    total = len(rows)
    if total > 8:
        content_blocks.append([
            {"tag": "text", "text": f"📊 共 {total} 条政策（仅展示前8条）"}
        ])
    else:
        content_blocks.append([
            {"tag": "text", "text": f"📊 共 {total} 条政策"}
        ])

    # 构造 post 内容
    post_content = {
        "post": {
            "zh_cn": {
                "title": "2026年人社补贴政策追踪报告",
                "content": content_blocks
            }
        }
    }

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # content 必须为 JSON 字符串
    payload = {
        "receive_id": receive_id,
        "msg_type": "post",
        "content": json.dumps(post_content, ensure_ascii=False)
    }

    # 打印完整 payload（脱敏 receive_id）
    payload_debug = payload.copy()
    payload_debug["receive_id"] = "***"
    print(f"  📤 完整 Payload（脱敏）:\n{json.dumps(payload_debug, ensure_ascii=False, indent=2)}")

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ 发送失败: {resp.text}")
        resp.raise_for_status()

    print(f"  ✅ 富文本消息发送成功，共 {len(rows_to_send)} 条政策")


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

    print("\n4. 发送富文本消息...")
    send_rich_text_message(token, RECEIVE_OPEN_ID_POLICY, rows, "西南四省")

    print("\n✅ 政策追踪报告发送完成！")


if __name__ == "__main__":
    main()
