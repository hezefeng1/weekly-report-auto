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


# ========== 云文档相关（分步创建表格） ==========

def create_doc(access_token, title):
    create_url = "https://open.feishu.cn/open-apis/docx/v1/documents"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(create_url, headers=headers, json={"title": title}, timeout=30)
    resp.raise_for_status()
    doc_id = resp.json()["data"]["document"]["document_id"]
    print(f"  📄 文档创建成功，ID: {doc_id}")
    return doc_id


def _create_text_block(content, is_bold=False):
    """创建文本块（block_type: 3）"""
    element = {"text_run": {"content": content}}
    if is_bold:
        element["text_run"]["text_element_style"] = {"bold": True}
    return {
        "block_type": 3,
        "text": {
            "elements": [element]
        }
    }


def _clean_cell_content(content):
    """清洗单元格内容，只保留纯文本"""
    # 去除 Markdown 链接语法 [文本](URL) -> 只保留文本
    clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
    # 去除多余的 | 分隔符
    clean = clean.replace('|', ' ')
    # 去除连续的多个空格
    clean = re.sub(r'[ \t]+', ' ', clean)
    return clean.strip()


def update_doc_with_table(access_token, doc_id, rows_data):
    """
    分步创建表格：先创建表头行，再逐行追加数据
    rows_data: 二维数组，第一行作为表头
    """
    if not rows_data or len(rows_data) == 0:
        print("  ❌ 没有数据")
        return

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    col_count = len(rows_data[0])
    row_count = len(rows_data)

    # 清洗所有数据：去除链接格式，只保留纯文本
    cleaned_rows = []
    for row in rows_data:
        cleaned_row = [_clean_cell_content(cell) for cell in row]
        cleaned_rows.append(cleaned_row)

    # 1. 创建表格（只创建表头行，不创建完整表格）
    # 先创建一个只有表头行的表格
    table_block = {
        "block_type": 11,
        "table": {
            "property": {
                "column_size": col_count,
                "row_size": 1  # 先只创建表头行
            }
        }
    }
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
        headers=headers,
        json={"children": [table_block]},
        timeout=60
    )
    if resp.status_code != 200:
        print(f"  ❌ 创建表格失败: {resp.text}")
        resp.raise_for_status()
    table_id = resp.json()["data"]["children"][0]["block_id"]
    print(f"  📊 表格创建成功，列数: {col_count}")

    # 2. 添加表头行
    _append_table_row(access_token, doc_id, table_id, cleaned_rows[0], is_header=True)

    # 3. 逐行添加数据
    for idx, row in enumerate(cleaned_rows[1:], start=1):
        _append_table_row(access_token, doc_id, table_id, row, is_header=False)
        if idx % 5 == 0:
            print(f"  ✅ 已添加 {idx}/{len(cleaned_rows)-1} 行")

    print(f"  ✅ 表格写入完成，共 {len(cleaned_rows)} 行")


def _append_table_row(access_token, doc_id, table_id, row_data, is_header=False):
    """向表格追加一行"""
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # 创建行
    row_block = {"block_type": 12, "table_row": {}}
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{table_id}/children",
        headers=headers,
        json={"children": [row_block]},
        timeout=60
    )
    if resp.status_code != 200:
        print(f"  ⚠️ 行创建失败")
        return
    row_id = resp.json()["data"]["children"][0]["block_id"]

    # 为该行创建单元格
    for col_idx, cell_data in enumerate(row_data):
        # 创建单元格
        cell_block = {"block_type": 13, "table_cell": {}}
        resp = requests.post(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{row_id}/children",
            headers=headers,
            json={"children": [cell_block]},
            timeout=60
        )
        if resp.status_code != 200:
            continue
        cell_id = resp.json()["data"]["children"][0]["block_id"]

        # 写入单元格内容
        text_block = _create_text_block(cell_data, is_bold=is_header)
        resp = requests.post(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{cell_id}/children",
            headers=headers,
            json={"children": [text_block]},
            timeout=60
        )
        if resp.status_code != 200:
            # 单个单元格失败不影响整体
            pass


def send_doc_link_message(access_token, receive_id, doc_id, region="西南四省"):
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置")
        return

    doc_url = f"https://newhope1982.feishu.cn/docx/{doc_id}"
    message_text = f"📋 **2026年人社补贴政策追踪（{region}）**\n\n政策追踪报告已生成，点击查看：\n{doc_url}"

    send_url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
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
