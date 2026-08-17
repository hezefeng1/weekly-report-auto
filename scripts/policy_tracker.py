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

print("\n2. 测试1: 使用官方文档示例格式...")
# 官方文档示例格式
content_obj = {
    "post": {
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
}

payload = {
    "receive_id": RECEIVE_OPEN_ID_POLICY,
    "msg_type": "post",
    "content": json.dumps(content_obj, ensure_ascii=False)
}

print(f"   content: {payload['content']}")

url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

resp = requests.post(url, headers=headers, json=payload, timeout=10)
print(f"   状态码: {resp.status_code}")
print(f"   响应: {resp.text}")

print("\n3. 测试2: 使用 msg_type=text 验证通道...")
payload_text = {
    "receive_id": RECEIVE_OPEN_ID_POLICY,
    "msg_type": "text",
    "content": json.dumps({"text": "通道测试成功"})
}
resp2 = requests.post(url, headers=headers, json=payload_text, timeout=10)
print(f"   状态码: {resp2.status_code}")
print(f"   响应: {resp2.text}")
