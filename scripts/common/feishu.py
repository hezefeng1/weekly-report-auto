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


def _clean_content_for_doc(content):
    """清洗内容，使其符合飞书云文档 API 的要求"""
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        # 1. 移除行首尾空白
        line = line.strip()
        if not line:
            continue
        # 2. 将连续的多个空格替换为单个空格
        line = re.sub(r'[ \t]+', ' ', line)
        # 3. 移除特殊字符（保留中文、英文、数字、常用标点）
        line = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\.\,\-\(\)\:\/\%\~\=\+\_\&\?\!\@\#\$]', '', line)
        # 4. 截断超长行
        if len(line) > 800:
            line = line[:800] + '...'
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)


def update_doc_content(access_token, doc_id, content):
    """
    向云文档写入内容（清洗后写入）
    """
    # 清洗内容
    cleaned_content = _clean_content_for_doc(content)
    if not cleaned_content:
        cleaned_content = "暂无政策数据"

    root_block_id = doc_id
    update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 按行拆分，每段不超过 1500 字符
    lines = cleaned_content.split('\n')
    chunks = []
    current_chunk = ""
    for line in lines:
        # 每行本身可能很长（表格行），如果单行超过 800 字符已经截断了
        if len(current_chunk) + len(line) + 1 > 1500:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += line + "\n"
    if current_chunk:
        chunks.append(current_chunk)

    # 如果没有任何内容，写入占位符
    if not chunks:
        chunks = ["暂无政策数据"]

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
