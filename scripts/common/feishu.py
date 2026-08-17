import requests
import json
import re

# ========== 原有函数（两个周报使用） ==========

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


# ========== 云文档相关（新增） ==========

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
    将 Markdown 内容转换为纯文本，并写入云文档
    """
    # 1. 解析 Markdown 表格，转为纯文本表格
    lines = content.split('\n')
    table_rows = []
    in_table = False
    headers = []
    for line in lines:
        if line.strip().startswith('|') and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if not in_table:
                headers = cells
                in_table = True
            else:
                # 清理链接，只保留 URL
                clean_cells = []
                for cell in cells:
                    # 提取 Markdown 链接中的 URL
                    link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', cell)
                    if link_match:
                        clean_cells.append(link_match.group(2))  # 只保留 URL
                    else:
                        clean_cells.append(cell)
                table_rows.append(clean_cells)
        elif in_table and line.strip() == '':
            break

    # 2. 构建纯文本表格（用空格对齐）
    if table_rows:
        all_rows = [headers] + table_rows
        col_widths = []
        for row in all_rows:
            for i, cell in enumerate(row):
                if i >= len(col_widths):
                    col_widths.append(0)
                col_widths[i] = max(col_widths[i], len(cell))
        # 至少宽度为 10
        col_widths = [max(w, 10) for w in col_widths]
        text_lines = []
        # 表头
        header_line = '  '.join(cell.ljust(col_widths[i]) for i, cell in enumerate(headers))
        text_lines.append(header_line)
        text_lines.append('-' * len(header_line))
        for row in table_rows:
            line = '  '.join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))
            text_lines.append(line)
        plain_content = '\n'.join(text_lines)
    else:
        plain_content = content  # 如果不是表格，直接使用原内容

    # 3. 写入云文档（分块）
    root_block_id = doc_id
    update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children"
    headers_api = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 将内容分段，每段不超过 2000 字符
    chunks = []
    chunk_size = 2000
    for i in range(0, len(plain_content), chunk_size):
        chunks.append(plain_content[i:i+chunk_size])

    for idx, chunk in enumerate(chunks):
        block = {
            "block_type": 3,
            "text": {
                "elements": [
                    {"text_run": {"content": chunk}}
                ]
            }
        }
        resp = requests.post(update_url, headers=headers_api, json={"children": [block]}, timeout=60)
        if resp.status_code == 200:
            print(f"  ✅ 第 {idx+1} 段写入成功")
        else:
            print(f"  ⚠️ 第 {idx+1} 段写入失败: {resp.text}")

    print(f"  ✅ 文档内容写入完成，共 {len(chunks)} 段")


def send_doc_link_message(access_token, receive_id, doc_id, region="西南四省"):
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置，请设置 GitHub Secret")
        return

    doc_url = f"https://feishu.cn/docs/{doc_id}"
    message_text = f"📋 **2026年人社补贴政策追踪（{region}）**\n\n政策追踪报告已生成，点击查看：\n{doc_url}"

    # receive_id_type 必须作为查询参数
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
