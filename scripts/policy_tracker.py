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

print("2. 构建最小化富文本消息...")
# 严格按照飞书官方示例构建
post_content = {
    "post": {
        "zh_cn": {
            "title": "测试标题",
            "content": [
                [
                    {"tag": "text", "text": "这是一条测试消息"}
                ]
            ]
        }
    }
}

# 将 content 序列化为字符串
content_str = json.dumps(post_content, ensure_ascii=False)
print(f"   content 字符串长度: {len(content_str)}")
print(f"   content 前100字符: {content_str[:100]}...")

payload = {
    "receive_id": RECEIVE_OPEN_ID_POLICY,
    "msg_type": "post",
    "content": content_str  # 直接传序列化后的字符串
}

print("3. 发送请求...")
url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 打印完整 payload 用于调试
print(f"   payload: {json.dumps(payload, ensure_ascii=False)[:500]}...")

resp = requests.post(url, headers=headers, json=payload, timeout=10)
print(f"状态码: {resp.status_code}")
print(f"响应内容: {resp.text}")
