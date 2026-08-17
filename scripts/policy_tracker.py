import os
import requests
import json

# ====== 从环境变量读取旧应用信息 ======
APP_ID = os.environ.get("FEISHU_APP_ID")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
OPEN_ID = os.environ.get("RECEIVE_OPEN_ID_POLICY")

if not APP_ID or not APP_SECRET or not OPEN_ID:
    print("❌ 请设置环境变量")
    exit(1)

print("=" * 60)
print("旧应用富文本逐步测试（从最简单开始）")
print("=" * 60)

# 获取 token
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},
    timeout=10
)
data = resp.json()
token = data.get("tenant_access_token")
if not token:
    print(f"❌ 获取 token 失败: {data}")
    exit(1)
print(f"✅ token: {token[:20]}...\n")

# ====== 测试1：最简单富文本（只写一句话） ======
print("【测试1】最简单的富文本（一句话）")
payload1 = {
    "receive_id": OPEN_ID,
    "msg_type": "post",
    "content": json.dumps({
        "post": {
            "zh_cn": {
                "title": "测试1",
                "content": [[{"tag": "text", "text": "Hello"}]]
            }
        }
    }, ensure_ascii=False)
}
resp1 = requests.post(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=payload1,
    timeout=10
)
print(f"状态码: {resp1.status_code}")
print(f"响应: {resp1.text}\n")

if resp1.status_code != 200:
    print("❌ 最简单的富文本就失败了，说明旧应用富文本通道有问题")
    exit(1)

# ====== 测试2：加城市 + 截止日期 ======
print("【测试2】城市 + 截止日期（无URL、无条件和补贴）")
payload2 = {
    "receive_id": OPEN_ID,
    "msg_type": "post",
    "content": json.dumps({
        "post": {
            "zh_cn": {
                "title": "测试2",
                "content": [
                    [{"tag": "text", "text": "📍 成都市  ⏰ 2026-07-01至2026-09-30"}]
                ]
            }
        }
    }, ensure_ascii=False)
}
resp2 = requests.post(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=payload2,
    timeout=10
)
print(f"状态码: {resp2.status_code}")
print(f"响应: {resp2.text}\n")

if resp2.status_code != 200:
    print("❌ 加城市和截止日期后失败，问题在日期格式")
    exit(1)

# ====== 测试3：加政策名称（无URL） ======
print("【测试3】城市 + 截止日期 + 政策名称（无URL）")
payload3 = {
    "receive_id": OPEN_ID,
    "msg_type": "post",
    "content": json.dumps({
        "post": {
            "zh_cn": {
                "title": "测试3",
                "content": [
                    [{"tag": "text", "text": "📍 成都市  ⏰ 2026-07-01至2026-09-30  📄 稳岗扩岗专项补贴"}]
                ]
            }
        }
    }, ensure_ascii=False)
}
resp3 = requests.post(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=payload3,
    timeout=10
)
print(f"状态码: {resp3.status_code}")
print(f"响应: {resp3.text}\n")

if resp3.status_code != 200:
    print("❌ 加政策名称后失败，问题在政策名称文本")
    exit(1)

# ====== 测试4：加URL（纯文本URL，不用a标签） ======
print("【测试4】城市 + 截止日期 + 政策名称 + 纯文本URL")
payload4 = {
    "receive_id": OPEN_ID,
    "msg_type": "post",
    "content": json.dumps({
        "post": {
            "zh_cn": {
                "title": "测试4",
                "content": [
                    [{"tag": "text", "text": "📍 成都市  ⏰ 2026-07-01至2026-09-30  📄 稳岗扩岗专项补贴  🔗 https://cdhrss.chengdu.gov.cn/2026wggx"}]
                ]
            }
        }
    }, ensure_ascii=False)
}
resp4 = requests.post(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=payload4,
    timeout=10
)
print(f"状态码: {resp4.status_code}")
print(f"响应: {resp4.text}\n")

if resp4.status_code != 200:
    print("❌ 加URL后失败，问题在URL文本")
    exit(1)

# ====== 测试5：加条件和补贴（完整内容） ======
print("【测试5】完整内容（城市 + 截止日期 + 政策名称 + URL + 条件 + 补贴）")
full_text = "📍 成都市  ⏰ 2026-07-01至2026-09-30  📄 稳岗扩岗专项补贴  📌 企业2026年1-6月社保参保人数不低于2025年同期，且未裁员或裁员率≤5.5%  💰 按2026年6月参保人数×500元/人，最高50万元  🔗 https://cdhrss.chengdu.gov.cn/2026wggx"
payload5 = {
    "receive_id": OPEN_ID,
    "msg_type": "post",
    "content": json.dumps({
        "post": {
            "zh_cn": {
                "title": "测试5",
                "content": [
                    [{"tag": "text", "text": full_text}]
                ]
            }
        }
    }, ensure_ascii=False)
}
resp5 = requests.post(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=payload5,
    timeout=10
)
print(f"状态码: {resp5.status_code}")
print(f"响应: {resp5.text}\n")

if resp5.status_code != 200:
    print("❌ 加条件和补贴后失败，问题在条件或补贴字段中的特殊字符（≤、×、%等）")
else:
    print("✅ 所有测试通过！旧应用富文本完全正常")
