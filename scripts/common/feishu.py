import requests
import json
import re

# ========== 原有函数 ==========

def get_tenant_access_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret}, timeout=30)
    resp.raise_for_status()
    return resp.json()["tenant_access_token"]


def upload_image(access_token, image_bytes):
    url = "https://open.feishu.cn/open-apis/im/v1/images"
    files = {"image": ("report.png", image_bytes, "image/png")}
    data = {"image_type": "message"}
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    resp.raise_for_status()
    return resp.json()["data"]["image_key"]


def send_image_message(access_token, receive_id, image_key):
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


# ========== 云文档相关 ==========

def create_doc(access_token, title):
    create_url = "https://open.feishu.cn/open-apis/docx/v1/documents"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(create_url, headers=headers, json={"title": title}, timeout=30)
    resp.raise_for_status()
    doc_id = resp.json()["data"]["document"]["document_id"]
    print(f"  📄 文档创建成功，ID: {doc_id}")
    return doc_id


def update_doc_content(access_token, doc_id, content):
    """
    向云文档写入内容（直接把 Markdown 作为纯文本写入）
    """
    root_block_id = doc_id
    update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    lines = content.split('\n')
    chunks = []
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > 2000:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += line + "\n"
    if current_chunk:
        chunks.append(current_chunk)

    for idx, chunk in enumerate(chunks):
        block = {
            "block_type": 3,
            "text": {
                "elements": [
                    {"text_run": {"content": chunk}}
                ]
            }
        }
        resp = requests.post(update_url, headers=headers, json={"children": [block]}, timeout=60)
        if resp.status_code == 200:
            print(f"  ✅ 第 {idx+1} 段写入成功")
        else:
            print(f"  ⚠️ 第 {idx+1} 段写入失败: {resp.text}")

    print(f"  ✅ 文档内容写入完成，共 {len(chunks)} 段")


def send_doc_link_message(access_token, receive_id, doc_id, region="西南四省"):
    """
    发送飞书云文档链接消息
    """
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置，请设置 GitHub Secret")
        return

    doc_url = f"https://newhope1982.feishu.cn/docx/{doc_id}"
    message_text = f"📋 **2026年人社补贴政策追踪（{region}）**\n\n政策追踪报告已生成，点击查看：\n{doc_url}"

    send_url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": message_text})
    }
    resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ 发送消息失败: {resp.text}")
        resp.raise_for_status()
    print(f"  ✅ 文档链接已发送")
