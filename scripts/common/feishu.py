import requests
import json

# ========== 原有函数 ==========

def get_tenant_access_token(app_id, app_secret):
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret}, timeout=30)
    resp.raise_for_status()
    return resp.json()["tenant_access_token"]

def upload_image(access_token, image_bytes):
    """上传图片，返回 image_key"""
    url = "https://open.feishu.cn/open-apis/im/v1/images"
    files = {"image": ("report.png", image_bytes, "image/png")}
    data = {"image_type": "message"}
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    resp.raise_for_status()
    return resp.json()["data"]["image_key"]

def send_image_message(access_token, receive_id, image_key):
    """发送图片私聊消息"""
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


# ========== 新增：飞书云文档相关 ==========

def create_doc(access_token, title, content):
    """
    创建飞书云文档并写入内容
    返回 doc_id
    """
    # 1. 创建空文档
    create_url = "https://open.feishu.cn/open-apis/docx/v1/documents"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    create_payload = {
        "title": title
    }
    resp = requests.post(create_url, headers=headers, json=create_payload, timeout=30)
    resp.raise_for_status()
    doc_id = resp.json()["data"]["document"]["document_id"]
    print(f"  📄 文档创建成功，ID: {doc_id}")

    # 2. 获取文档根节点 block_id
    root_block_id = doc_id
    update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children"
    
    # 3. 直接把完整内容作为一个文本块写入
    # 限制内容长度，避免超出 API 限制
    max_content_length = 30000
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n...（内容过长，已截断）"
    
    block = {
        "block_type": 3,  # 文本块
        "text": {
            "elements": [
                {"text_run": {"content": content}}
            ]
        }
    }
    
    update_payload = {"children": [block]}
    resp = requests.post(update_url, headers=headers, json=update_payload, timeout=60)
    if resp.status_code == 400:
        print("  ⚠️ 单块写入失败，尝试分段写入...")
        # 分段写入
        chunk_size = 2000
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        success_count = 0
        for idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            block = {
                "block_type": 3,
                "text": {
                    "elements": [
                        {"text_run": {"content": chunk}}
                    ]
                }
            }
            try:
                resp2 = requests.post(update_url, headers=headers, json={"children": [block]}, timeout=60)
                if resp2.status_code == 200:
                    success_count += 1
                    print(f"    ✅ 第 {idx+1} 段写入成功")
                else:
                    print(f"    ⚠️ 第 {idx+1} 段写入失败 (状态码: {resp2.status_code})")
            except Exception as e:
                print(f"    ⚠️ 第 {idx+1} 段写入失败: {e}")
        print(f"  ✅ 文档内容分段写入完成，成功 {success_count}/{len(chunks)} 段")
    else:
        resp.raise_for_status()
        print(f"  ✅ 文档内容写入完成")
    
    return doc_id

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
