import os
import requests
import json
from common.feishu import get_tenant_access_token

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")

token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

def send_post(content_2d, title="测试富文本"):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    post_content = {"post": {"zh_cn": {"title": title, "content": content_2d}}}
    payload = {
        "receive_id": RECEIVE_OPEN_ID_POLICY,
        "msg_type": "post",
        "content": json.dumps(post_content, ensure_ascii=False)
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.text}")
    return resp.status_code == 200

print("=== 测试1: 最简单的富文本（单个text标签）===")
send_post([
    [{"tag": "text", "text": "Hello 富文本"}]
])

print("\n=== 测试2: 两个段落的富文本 ===")
send_post([
    [{"tag": "text", "text": "第一段"}],
    [{"tag": "text", "text": "第二段"}]
])

print("\n=== 测试3: 带分隔线的富文本 ===")
send_post([
    [{"tag": "text", "text": "标题"}],
    [{"tag": "text", "text": "─────────────────────"}],
    [{"tag": "text", "text": "内容"}]
])
