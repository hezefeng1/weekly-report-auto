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

print("2. 发送纯文本消息...")
url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
payload = {
    "receive_id": RECEIVE_OPEN_ID_POLICY,
    "msg_type": "text",
    "content": json.dumps({"text": "Hello, 这是纯文本测试"})
}
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

resp = requests.post(url, headers=headers, json=payload, timeout=10)
print(f"状态码: {resp.status_code}")
print(f"响应内容: {resp.text}")
