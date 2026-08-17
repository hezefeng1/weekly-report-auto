import os
import requests
import json

# 从环境变量读取（你已经在环境里更新了）
APP_ID = os.environ.get("FEISHU_APP_ID")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
OPEN_ID = os.environ.get("RECEIVE_OPEN_ID_POLICY")

if not APP_ID or not APP_SECRET or not OPEN_ID:
    print("❌ 请设置环境变量 FEISHU_APP_ID, FEISHU_APP_SECRET, RECEIVE_OPEN_ID_POLICY")
    exit(1)

print("1. 获取 token...")
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},
    timeout=10
)
data = resp.json()
if data.get("code") != 0:
    print(f"❌ 获取 token 失败: {data}")
    exit(1)

token = data.get("tenant_access_token")
print(f"   ✅ token: {token[:20]}...")

print("\n2. 发送最简单的富文本消息...")
payload = {
    "receive_id": OPEN_ID,
    "msg_type": "post",
    "content": json.dumps({
        "post": {
            "zh_cn": {
                "title": "测试",
                "content": [[{"tag": "text", "text": "新应用富文本测试"}]]
            }
        }
    }, ensure_ascii=False)
}

resp = requests.post(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=payload,
    timeout=10
)
print(f"状态码: {resp.status_code}")
print(f"响应: {resp.text}")
