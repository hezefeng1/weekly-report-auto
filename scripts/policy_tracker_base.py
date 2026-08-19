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

# ==================== 提示词（参考政策追踪格式） ====================
def build_social_prompt(province):
    today = datetime.now().strftime("%Y年%m月%d日")
    system_prompt = f"""你是社保政策情报分析AI。

任务：查询{province}2026年度（或2026年7月至2027年6月社保年度）职工基本养老保险缴费基数上下限。

## 强制限制

### 绝对禁止
- 禁止生成任何中间文件
- 禁止在最终文档中添加总结、建议等额外文字
- 禁止输出官网首页链接（必须输出政策原文链接）
- 禁止链接带追踪参数

### 数据要求
- 社保基数：优先查找职工基本养老保险的缴费基数上下限
- 如果数据未公布，填写"待公布"
- 必须注明执行周期（如：2026-07至2027-06）

## 输出格式
只生成一个 Markdown 表格，表头如下：
| 省份 | 社保基数下限 | 社保基数上限 | 执行周期 |
|------|-------------|-------------|----------|

## 输出前自检清单
- [ ] 数据来源为省级人社部门官方发布
- [ ] 上下限数字格式正确（如：XXXX元/月）
- [ ] 执行周期格式正确（YYYY-MM至YYYY-MM）
- [ ] 无多余文字，仅表格

请开始查询。"""

    user_prompt = f"请查询{province}2026年度职工基本养老保险缴费基数上下限（截至{today}已公布的最新数据）。严格按照表格格式输出。"
    return system_prompt, user_prompt


def build_housing_prompt(province, city):
    today = datetime.now().strftime("%Y年%m月%d日")
    system_prompt = f"""你是公积金政策情报分析AI。

任务：查询{city}2026年度（或2026年7月至2027年6月年度）住房公积金缴存基数上下限。

## 强制限制

### 绝对禁止
- 禁止生成任何中间文件
- 禁止在最终文档中添加总结、建议等额外文字
- 禁止输出官网首页链接
- 禁止链接带追踪参数

### 数据要求
- 公积金下限：通常与当地最低工资标准挂钩，同一城市不同区县可能不同。
- 如果存在区县差异，请逐区县列出；若全市统一，则写"全市统一"。
- 如果数据未公布，填写"待公布"
- 必须注明执行周期

## 输出格式
只生成一个 Markdown 表格，表头如下：
| 省份 | 城市 | 区县 | 公积金下限 | 公积金上限 | 执行周期 |
|------|------|------|-----------|-----------|----------|

注意：若各区县不同，请分行列出；若全市统一，区县列写"全市统一"。

## 输出前自检清单
- [ ] 数据来源为市级公积金管理中心官方发布
- [ ] 下限、上限数字格式正确（如：XXXX元/月）
- [ ] 执行周期格式正确（YYYY-MM至YYYY-MM）
- [ ] 若存在区县差异，已分行列出
- [ ] 无多余文字，仅表格

请开始查询。"""

    user_prompt = f"请查询{city}2026年度住房公积金缴存基数上下限，注意区县差异（截至{today}已公布的最新数据）。严格按照表格格式输出。"
    return system_prompt, user_prompt


# ==================== 查询函数 ====================
def query_data(system_prompt, user_prompt, region_name):
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
        "temperature": 0.1,
        "stream": False
    }

    print(f"  📡 查询: {region_name}")
    resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=300)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return content


def parse_markdown_table_to_list(markdown_text):
    if not markdown_text:
        return None
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
    print("📋 2026年社保公积金基数追踪")
    print("=" * 50)

    # ---------- 1. 社保 ----------
    print("\n🔹 查询社保基数（省级统一）...")
    social_rows = []
    for province in SOCIAL_SECURITY_PROVINCES:
        try:
            sys_prompt, user_prompt = build_social_prompt(province)
            md = query_data(sys_prompt, user_prompt, province)
            rows = parse_markdown_table_to_list(md)
            if rows:
                social_rows.extend(rows)
                print(f"    ✅ {province} 成功")
            else:
                print(f"    ⚠️ {province} 无数据")
        except Exception as e:
            print(f"    ❌ {province} 失败: {e}")

    # ---------- 2. 公积金 ----------
    print("\n🔹 查询公积金基数（市级，含区县差异）...")
    fund_rows = []
    for province, city in HOUSING_FUND_CITIES:
        try:
            sys_prompt, user_prompt = build_housing_prompt(province, city)
            md = query_data(sys_prompt, user_prompt, city)
            rows = parse_markdown_table_to_list(md)
            if rows:
                fund_rows.extend(rows)
                print(f"    ✅ {city} 成功")
            else:
                print(f"    ⚠️ {city} 无数据")
        except Exception as e:
            print(f"    ❌ {city} 失败: {e}")

    # ---------- 3. 发送 ----------
    if not social_rows and not fund_rows:
        print("\n❌ 未获取到任何数据")
        return

    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    if social_rows:
        print("\n📤 发送社保基数消息...")
        send_rich_text_message(
            token,
            RECEIVE_OPEN_ID_POLICY,
            social_rows,
            "2026年社保缴费基数（省级统一）",
            ["省份", "基数下限", "基数上限", "执行周期"]
        )

    if fund_rows:
        print("\n📤 发送公积金基数消息...")
        send_rich_text_message(
            token,
            RECEIVE_OPEN_ID_POLICY,
            fund_rows,
            "2026年公积金缴存基数（市级/区县）",
            ["省份", "城市", "区县", "下限", "上限", "执行周期"]
        )

    print("\n✅ 全部完成！")


if __name__ == "__main__":
    main()
