import os
import requests
import json
from common.feishu import get_tenant_access_token

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")

print("1. 获取 token...")
token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
print(f"   token 获取成功，前20字符: {token[:20] if token else 'None'}")

print("2. 构建飞书官方示例格式的富文本...")

# ========== 严格按照飞书官方文档格式 ==========
# 官方文档: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/im-v1/message/create_json
post_content = {
    "zh_cn": {
        "title": "测试标题",
        "content": [
            [
                {
                    "tag": "text",
                    "text": "这是一条测试消息"
                }
            ]
        ]
    }
}

# 注意：这里 post_content 是直接放在 "post" 下的
payload = {
    "receive_id": RECEIVE_OPEN_ID_POLICY,
    "msg_type": "post",
    "content": json.dumps({"post": post_content}, ensure_ascii=False)
}

print(f"   content 序列化后长度: {len(payload['content'])}")
print(f"   payload 完整内容: {json.dumps(payload, ensure_ascii=False)}")

print("3. 发送请求...")
url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

resp = requests.post(url, headers=headers, json=payload, timeout=10)
print(f"状态码: {resp.status_code}")
print(f"响应内容: {resp.text}")
