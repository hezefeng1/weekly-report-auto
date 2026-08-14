import requests
import json

# ========== 原有函数保持不变 ==========

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
    # 1. 创建文档
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

    # 2. 更新文档内容
    # 直接将 Markdown 内容作为纯文本写入
    # 飞书云文档的 block 结构较为复杂，使用纯文本块保持简单
    update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children"
    
    # 将内容按行拆分成多个文本块
    lines = content.split('\n')
    children = []
    current_paragraph = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_paragraph:
                children.append({
                    "block_type": 3,  # 文本块
                    "text": {"elements": [{"text_run": {"content": current_paragraph}}]}
                })
                current_paragraph = ""
            continue
        
        # 检测 Markdown 标题
        if line.startswith('# '):
            if current_paragraph:
                children.append({
                    "block_type": 3,
                    "text": {"elements": [{"text_run": {"content": current_paragraph}}]}
                })
                current_paragraph = ""
            children.append({
                "block_type": 1,  # 标题1
                "heading1": {"content": line[2:].strip()}
            })
        elif line.startswith('## '):
            if current_paragraph:
                children.append({
                    "block_type": 3,
                    "text": {"elements": [{"text_run": {"content": current_paragraph}}]}
                })
                current_paragraph = ""
            children.append({
                "block_type": 2,  # 标题2
                "heading2": {"content": line[3:].strip()}
            })
        elif line.startswith('|') and '---' in line:
            # 表格分隔行，跳过
            continue
        elif line.startswith('|') or '|' in line:
            # 表格行：保持原样显示
            children.append({
                "block_type": 3,
                "text": {"elements": [{"text_run": {"content": line}}]}
            })
        else:
            # 普通文本
            if current_paragraph:
                current_paragraph += " " + line
            else:
                current_paragraph = line
    
    # 处理最后一段
    if current_paragraph:
        children.append({
            "block_type": 3,
            "text": {"elements": [{"text_run": {"content": current_paragraph}}]}
        })
    
    # 如果内容为空，添加占位文本
    if not children:
        children.append({
            "block_type": 3,
            "text": {"elements": [{"text_run": {"content": "暂无政策数据"}}]}
        })
    
    # 分批写入（防止一次写入过多导致超时）
    batch_size = 50
    for i in range(0, len(children), batch_size):
        batch = children[i:i+batch_size]
        update_payload = {"children": batch}
        resp = requests.post(update_url, headers=headers, json=update_payload, timeout=60)
        resp.raise_for_status()
        print(f"  ✅ 写入第 {i//batch_size + 1} 批，共 {len(batch)} 个块")
    
    print(f"  ✅ 文档内容写入完成，共 {len(children)} 个块")
    return doc_id

def send_doc_link_message(access_token, receive_id, doc_id, region="西南四省"):
    """发送飞书云文档链接消息"""
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
