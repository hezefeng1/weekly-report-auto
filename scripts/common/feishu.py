import requests
import json
import re

# ========== 原有函数（两个周报使用，保持不变） ==========

def get_tenant_access_token(app_id, app_secret):
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret}, timeout=30)
    resp.raise_for_status()
    return resp.json()["tenant_access_token"]


def upload_image(access_token, image_bytes):
    """上传图片，返回 image_key（两个周报使用）"""
    url = "https://open.feishu.cn/open-apis/im/v1/images"
    files = {"image": ("report.png", image_bytes, "image/png")}
    data = {"image_type": "message"}
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    resp.raise_for_status()
    return resp.json()["data"]["image_key"]


def send_image_message(access_token, receive_id, image_key):
    """发送图片私聊消息（两个周报使用）"""
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "receive_id": receive_id,
        "msg_type": "image",
        "content": json.dumps({"image_key": image_key})
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ========== 新增函数（政策追踪云文档版使用，不影响两个周报） ==========

def create_doc(access_token, title):
    """创建飞书云文档（空文档）"""
    create_url = "https://open.feishu.cn/open-apis/docx/v1/documents"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    create_payload = {"title": title}
    resp = requests.post(create_url, headers=headers, json=create_payload, timeout=30)
    resp.raise_for_status()
    doc_id = resp.json()["data"]["document"]["document_id"]
    print(f"  📄 文档创建成功，ID: {doc_id}")
    return doc_id


def update_doc_content(access_token, doc_id, content):
    """向云文档写入内容（纯文本块）"""
    root_block_id = doc_id
    update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    lines = content.split('\n')
    blocks = []
    for line in lines:
        if line.strip():
            blocks.append({
                "block_type": 3,
                "text": {
                    "elements": [
                        {"text_run": {"content": line}}
                    ]
                }
            })

    if not blocks:
        blocks.append({
            "block_type": 3,
            "text": {
                "elements": [
                    {"text_run": {"content": "暂无政策数据"}}
                ]
            }
        })

    batch_size = 20
    for i in range(0, len(blocks), batch_size):
        batch = blocks[i:i+batch_size]
        resp = requests.post(update_url, headers=headers, json={"children": batch}, timeout=60)
        if resp.status_code != 200:
            print(f"  ⚠️ 第 {i//batch_size + 1} 批写入失败: {resp.text}")
        else:
            print(f"  ✅ 第 {i//batch_size + 1} 批写入成功")

    print(f"  ✅ 文档内容写入完成，共 {len(blocks)} 个块")


def send_doc_link_message(access_token, receive_id, doc_id, region="西南四省"):
    """发送飞书云文档链接消息"""
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置，请设置 GitHub Secret")
        return None

    doc_url = f"https://feishu.cn/docs/{doc_id}"
    message_text = f"📋 **2026年人社补贴政策追踪（{region}）**\n\n政策追踪报告已生成，点击查看：\n{doc_url}"

    send_url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "receive_id": receive_id,
        "receive_id_type": "open_id",
        "msg_type": "text",
        "content": json.dumps({"text": message_text})
    }
    resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    print(f"  ✅ 文档链接已发送")
    return resp.json()
