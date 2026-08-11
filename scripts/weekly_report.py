import os
import requests
from datetime import datetime, timedelta
from common.feishu import get_tenant_access_token, upload_image, send_image_message
from common.image import markdown_to_image

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID = os.environ.get("RECEIVE_OPEN_ID")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

def generate_weekly_report():
    """调用 DeepSeek API 生成周报 Markdown"""
    today = datetime.now().strftime("%Y年%m月%d日")
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y年%m月%d日")

    system_prompt = f"""你是农牧行业人力资源情报AI。
请搜索 {last_week} 至 {today} 期间关于农牧、生猪养殖、饲料成本、农业人才、HR策略、招聘趋势、薪酬福利的最新资讯，生成专业周报。
要求：必须联网获取真实信息，来源限白名单（巨潮、证券时报、第一财经、猎聘、人社部等），每条信息标注来源和链接，不得涉及新希望六和。
输出纯Markdown格式，包含标题、数据速览、关键结论、5-8条要闻、竞品对比表、专项洞察、行动建议表。"""

    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请生成 {today} 的周报。"}
        ],
        "temperature": 0.3,
        "stream": False
    }
    resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=180)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def main():
    print("1. 生成周报 Markdown...")
    md = generate_weekly_report()
    print("--- 原始 Markdown 内容（前500字符）---")
    print(md[:500])  # 只打印前500字符，避免太长
    print("------------------------------------")
    print("2. 渲染为图片...")
    # ... 后续代码不变
    image_path = markdown_to_image(md, "weekly_report.png")
    print("3. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
    print("4. 上传图片...")
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_key = upload_image(token, image_bytes)
    print("5. 发送私聊消息...")
    send_image_message(token, RECEIVE_OPEN_ID, image_key)
    print("完成！")

if __name__ == "__main__":
    main()
