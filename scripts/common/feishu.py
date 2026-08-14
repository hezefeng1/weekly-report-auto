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

    # 2. 文档根节点就是 doc_id 本身
    root_block_id = doc_id
    update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children"
    
    # 3. 将 Markdown 内容转换为飞书 block 结构
    lines = content.split('\n')
    all_blocks = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 检测 Markdown 标题
        if line.startswith('# '):
            all_blocks.append({
                "block_type": 1,  # 标题1
                "heading1": {"content": line[2:].strip()}
            })
        elif line.startswith('## '):
            all_blocks.append({
                "block_type": 2,  # 标题2
                "heading2": {"content": line[3:].strip()}
            })
        elif line.startswith('|') and '---' in line:
            # 表格分隔行，跳过
            continue
        else:
            # 普通文本（包括表格行）
            all_blocks.append({
                "block_type": 3,
                "text": {"elements": [{"text_run": {"content": line}}]}
            })
    
    # 如果没有内容，加一个占位
    if not all_blocks:
        all_blocks.append({
            "block_type": 3,
            "text": {"elements": [{"text_run": {"content": "暂无政策数据"}}]}
        })
    
    # 4. 分批写入
    batch_size = 20
    for i in range(0, len(all_blocks), batch_size):
        batch = all_blocks[i:i+batch_size]
        update_payload = {"children": batch}
        resp = requests.post(update_url, headers=headers, json=update_payload, timeout=60)
        if resp.status_code == 400:
            print(f"  ⚠️ 第 {i//batch_size + 1} 批写入失败 (400)，尝试逐条写入...")
            # 逐个写入，跳过有问题的块
            for block in batch:
                try:
                    resp2 = requests.post(update_url, headers=headers, json={"children": [block]}, timeout=60)
                    if resp2.status_code != 200:
                        print(f"    ⚠️ 跳过问题块: {block.get('block_type')}")
                except Exception as e:
                    print(f"    ⚠️ 跳过问题块: {e}")
            continue
        resp.raise_for_status()
        print(f"  ✅ 写入第 {i//batch_size + 1} 批，共 {len(batch)} 个块")
    
    print(f"  ✅ 文档内容写入完成，共 {len(all_blocks)} 个块")
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
