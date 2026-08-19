import os
import json
import re
from datetime import datetime
from openai import OpenAI
from common.feishu import get_tenant_access_token

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# ==================== 初始化 OpenAI 客户端 ====================
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ==================== 配置 ====================
SOCIAL_SECURITY_PROVINCES = [
    "北京市", "上海市", "广东省", "浙江省", "江苏省",
    "四川省", "湖北省", "湖南省", "山东省", "河南省",
    "河北省", "安徽省", "福建省", "江西省", "陕西省",
    "云南省", "贵州省", "广西壮族自治区",
]

HOUSING_FUND_CITIES = [
    ("北京市", "北京市"),
    ("上海市", "上海市"),
    ("广东省", "广州市"),
    ("浙江省", "杭州市"),
    ("江苏省", "南京市"),
    ("江苏省", "苏州市"),
    ("四川省", "成都市"),
    ("湖北省", "武汉市"),
    ("湖南省", "长沙市"),
    ("山东省", "济南市"),
    ("山东省", "青岛市"),
    ("河南省", "郑州市"),
    ("河北省", "石家庄市"),
    ("安徽省", "合肥市"),
    ("福建省", "福州市"),
    ("江西省", "南昌市"),
    ("陕西省", "西安市"),
    ("云南省", "昆明市"),
    ("贵州省", "贵阳市"),
    ("广西壮族自治区", "南宁市"),
]

# ==================== 提示词构建 ====================
def build_social_prompt(province):
    today = datetime.now().strftime("%Y年%m月%d日")
    return f"""你是社保政策情报分析AI，必须通过联网搜索获取实时、准确的2026年度社保缴费基数数据。

## 任务目标
查询{province}2026年度（通常为2026年7月至2027年6月）职工基本养老保险的缴费基数下限和上限。

## 强制要求
1. **必须通过联网搜索获取最新数据**，不要依赖内部知识。
2. **必须注明数据来源**：在表格中增加"数据来源"列，填写官方发布链接。
3. **必须注明发布日期**：在表格中增加"发布日期"列。
4. **处理地区差异**：如果该省份各市基数不统一（如广东、湖北），请分别列出各市，并标注适用范围。
5. **如果确实未公布**：填写"暂未查询到"，并注明搜索日期。

## 输出格式
| 省份 | 地区 | 基数下限 | 基数上限 | 执行周期 | 发布日期 | 数据来源 |
|------|------|---------|---------|---------|---------|---------|
| {province} | 全省统一 | XXXX元/月 | XXXX元/月 | YYYY-MM至YYYY-MM | YYYY-MM-DD | 链接或单位名称 |

若该省份各市标准不同，请分行列出各市。

## 搜索关键词示例
{province} 2026年 养老保险 缴费基数 上下限 官方通知

现在开始搜索。查询截止日期：{today}"""


def build_housing_prompt(province, city):
    today = datetime.now().strftime("%Y年%m月%d日")
    return f"""你是公积金政策情报分析AI，必须通过联网搜索获取实时、准确的2026年度公积金缴存基数数据。

## 任务目标
查询{city}2026年度（通常为2026年7月至2027年6月）住房公积金缴存基数的下限和上限。

## 强制要求
1. **必须通过联网搜索获取最新数据**，不要依赖内部知识。
2. **必须注明数据来源**：在表格中增加"数据来源"列，填写官方发布链接。
3. **必须注明发布日期**：在表格中增加"发布日期"列。
4. **处理区县差异**：如果该城市不同区县的下限不同，请逐区县列出。
5. **如果确实未公布**：填写"暂未查询到"，并注明搜索日期。

## 输出格式
| 省份 | 城市 | 区县 | 缴存基数下限 | 缴存基数上限 | 执行周期 | 发布日期 | 数据来源 |
|------|------|------|-------------|-------------|---------|---------|---------|
| {province} | {city} | 全市统一 | XXXX元/月 | XXXX元/月 | YYYY-MM至YYYY-MM | YYYY-MM-DD | 链接或单位名称 |

若各区县下限不同，请分行列出各区县。

## 搜索关键词示例
{city} 2026年 公积金 缴存基数 上下限 官方通知

现在开始搜索。查询截止日期：{today}"""


# ==================== 查询函数（Responses API） ====================
def query_with_search(prompt, region_name, retries=2):
    """使用 Responses API 进行联网搜索查询"""
    for attempt in range(retries):
        try:
            print(f"  📡 查询: {region_name} (尝试 {attempt+1}/{retries})")
            
            response = client.responses.create(
                model="deepseek-v4-flash",
                instructions="你是一名社保公积金政策分析师。必须通过联网搜索获取最新官方数据。",
                input=prompt,
                tools=[{"type": "web_search"}],
                temperature=0.0,
            )
            
            # 提取返回内容
            content = response.output_text
            return content
            
        except Exception as e:
            if attempt < retries - 1:
                print(f"    ⚠️ 重试中...")
                continue
            else:
                raise e
    return None


# ==================== 解析函数 ====================
def parse_markdown_table_to_list(markdown_text):
    """解析 Markdown 表格，支持不同列数"""
    if not markdown_text:
        return None
    
    # 提取代码块内的表格，或直接使用 Markdown 表格
    # 先尝试提取 ```markdown 或 ``` 代码块
    code_block_match = re.search(r'```(?:markdown)?\s*\n(.*?)\n```', markdown_text, re.DOTALL)
    if code_block_match:
        markdown_text = code_block_match.group(1)
    
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


# ==================== 发送函数 ====================
def send_rich_text_message(access_token, receive_id, rows, title, headers):
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置")
        return

    md_lines = []
    md_lines.append(f"📋 {title}\n")
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "|" + "|".join(["------"] * len(headers)) + "|"
    md_lines.append(header_line)
    md_lines.append(separator_line)

    for row in rows:
        if len(row) < len(headers):
            continue
        while len(row) < len(headers):
            row.append("")
        md_lines.append("| " + " | ".join(row) + " |")

    md_content = "\n".join(md_lines)

    send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "receive_id": receive_id,
        "msg_type": "post",
        "content": json.dumps({
            "zh_cn": {
                "title": title,
                "content": [
                    [{"tag": "md", "text": md_content}]
                ]
            }
        })
    }

    resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ 发送失败: {resp.text}")
        resp.raise_for_status()

    print(f"  ✅ 发送成功")


# ==================== 主程序 ====================
def main():
    print("=" * 50)
    print("📋 2026年社保公积金基数追踪（Responses API + 联网搜索）")
    print("=" * 50)

    # ---------- 社保 ----------
    print("\n🔹 查询社保基数...")
    social_rows = []
    for province in SOCIAL_SECURITY_PROVINCES:
        try:
            prompt = build_social_prompt(province)
            result = query_with_search(prompt, province)
            rows = parse_markdown_table_to_list(result)
            if rows:
                social_rows.extend(rows)
                print(f"    ✅ {province} 成功 ({len(rows)} 行)")
            else:
                print(f"    ⚠️ {province} 无数据")
        except Exception as e:
            print(f"    ❌ {province} 失败: {e}")

    # ---------- 公积金 ----------
    print("\n🔹 查询公积金基数...")
    fund_rows = []
    for province, city in HOUSING_FUND_CITIES:
        try:
            prompt = build_housing_prompt(province, city)
            result = query_with_search(prompt, city)
            rows = parse_markdown_table_to_list(result)
            if rows:
                fund_rows.extend(rows)
                print(f"    ✅ {city} 成功 ({len(rows)} 行)")
            else:
                print(f"    ⚠️ {city} 无数据")
        except Exception as e:
            print(f"    ❌ {city} 失败: {e}")

    # ---------- 发送 ----------
    if not social_rows and not fund_rows:
        print("\n❌ 未获取到任何数据")
        return

    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    if social_rows:
        # 检测表格列数动态调整表头
        first_row_len = len(social_rows[0])
        if first_row_len >= 7:
            headers = ["省份", "地区", "基数下限", "基数上限", "执行周期", "发布日期", "数据来源"]
        elif first_row_len >= 5:
            headers = ["省份", "基数下限", "基数上限", "执行周期", "数据来源"]
        else:
            headers = ["省份", "基数下限", "基数上限", "执行周期"]
        
        print("\n📤 发送社保基数消息...")
        send_rich_text_message(
            token,
            RECEIVE_OPEN_ID_POLICY,
            social_rows,
            "2026年社保缴费基数（联网搜索）",
            headers
        )

    if fund_rows:
        first_row_len = len(fund_rows[0])
        if first_row_len >= 8:
            headers = ["省份", "城市", "区县", "下限", "上限", "执行周期", "发布日期", "数据来源"]
        elif first_row_len >= 6:
            headers = ["省份", "城市", "区县", "下限", "上限", "执行周期"]
        else:
            headers = ["省份", "城市", "下限", "上限"]
        
        print("\n📤 发送公积金基数消息...")
        send_rich_text_message(
            token,
            RECEIVE_OPEN_ID_POLICY,
            fund_rows,
            "2026年公积金缴存基数（联网搜索）",
            headers
        )

    print("\n✅ 全部完成！")


if __name__ == "__main__":
    main()
