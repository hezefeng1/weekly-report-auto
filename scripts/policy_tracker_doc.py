import os
import requests
import json
import re
from datetime import datetime, timedelta
from common.feishu import get_tenant_access_token, create_doc, send_doc_link_message, update_doc_content

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")


def generate_policy_report():
    today = datetime.now().strftime("%Y年%m月%d日")

    system_prompt = """你是人社政策情报分析AI。

任务：搜索2026年1月1日之后新发布的企业补贴政策，覆盖四川省、重庆市、云南省、贵州省，输出纯文本表格格式政策追踪报告。

## 强制限制

### 绝对禁止
- 禁止生成任何中间文件
- 禁止在最终文档中添加总结、建议等额外文字
- 禁止输出官网首页链接（必须输出政策原文链接）
- 禁止链接带追踪参数
- 禁止使用短链接

### 明确排除的文件类型
- 标题包含"公示"的所有文件
- "灵活就业社保补贴"相关文件
- "创业担保贷款"相关文件

### 明确排除的链接类型
- 官网首页
- 栏目页
- 列表页

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

## 核心信息要素（7个字段）

省份、城市、政策名称、核心申请条件、补贴标准/金额、开放申请及截止日期、政策原文链接

## 输出格式（纯文本表格，不使用 | 分隔符）

只生成一个纯文本表格，使用空格对齐，参考以下示例格式：

省份         城市         政策名称                 核心申请条件       补贴标准/金额    开放申请及截止日期      政策原文链接
--------------------------------------------------------------------------------------------------------
四川省       成都市       2026年稳岗返还通知       参保企业...        30%-60%         2026-01-15至2026-12-31  http://xxx.gov.cn/xxx
四川省       绵阳市       企业吸纳就业补贴         招用高校毕业生...  1000元/人       2026-03-01至2026-11-30  http://xxx.gov.cn/xxx

注意：
- 不使用 `|` 分隔符
- 列之间用至少 2 个空格分隔
- 政策名称列只显示名称，不包含链接语法
- 原文链接单独作为最后一列显示完整 URL
- 无新政策的城市：不输出该城市
- 表格必须完整，包含所有 7 列

请开始生成报告。"""

    user_prompt = f"请生成2026年人社补贴政策追踪报告（西南四省），政策发布日期为2026年1月1日之后，截止当前日期（{today}）仍未过期的政策。严格按照纯文本表格格式输出，不使用 | 分隔符。"

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


def main():
    print("=" * 50)
    print("📋 人社补贴政策追踪（西南四省）- 云文档版")
    print("=" * 50)

    print("\n1. 生成政策追踪报告...")
    md_content = generate_policy_report()
    print("=== DeepSeek 返回的完整内容 ===")
    print(md_content)
    print("=== 内容结束 ===")

    print("\n2. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    print("\n3. 创建飞书云文档...")
    doc_id = create_doc(token, "2026年人社补贴政策追踪（西南四省）")

    print("\n4. 写入文档内容...")
    update_doc_content(token, doc_id, md_content)

    print("\n5. 发送文档链接...")
    send_doc_link_message(token, RECEIVE_OPEN_ID_POLICY, doc_id, "西南四省")

    print("\n✅ 政策追踪报告发送完成！")


if __name__ == "__main__":
    main()
