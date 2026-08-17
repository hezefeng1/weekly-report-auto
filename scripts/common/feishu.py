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


# ========== 云文档相关（表格 block 方式） ==========

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


def update_doc_with_table(access_token, doc_id, rows_data):
    """
    在云文档中创建真正的表格（block_type: 11）
    rows_data: 二维数组，第一行作为表头
    """
    root_block_id = doc_id
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    if not rows_data or len(rows_data) == 0:
        # 无数据，写入提示
        return update_doc_content(access_token, doc_id, "暂无政策数据")

    col_count = len(rows_data[0])
    row_count = len(rows_data)

    # 1. 创建表格
    table_block = {
        "block_type": 11,
        "table": {
            "property": {
                "column_size": col_count,
                "row_size": row_count
            }
        }
    }
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children",
        headers=headers,
        json={"children": [table_block]},
        timeout=60
    )
    if resp.status_code != 200:
        print(f"  ❌ 创建表格失败: {resp.text}")
        resp.raise_for_status()
    table_id = resp.json()["data"]["children"][0]["block_id"]
    print(f"  📊 表格创建成功，列数: {col_count}，行数: {row_count}")

    # 2. 逐行创建
    for row_idx, row in enumerate(rows_data):
        # 2.1 创建行
        row_block = {"block_type": 12, "table_row": {}}
        resp = requests.post(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{table_id}/children",
            headers=headers,
            json={"children": [row_block]},
            timeout=60
        )
        if resp.status_code != 200:
            print(f"  ⚠️ 第 {row_idx+1} 行创建失败")
            continue
        row_id = resp.json()["data"]["children"][0]["block_id"]

        # 2.2 为该行创建单元格
        for col_idx, cell_data in enumerate(row):
            # 创建单元格
            cell_block = {"block_type": 13, "table_cell": {}}
            resp = requests.post(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{row_id}/children",
                headers=headers,
                json={"children": [cell_block]},
                timeout=60
            )
            if resp.status_code != 200:
                print(f"    ⚠️ 第 {row_idx+1} 行第 {col_idx+1} 列单元格创建失败")
                continue
            cell_id = resp.json()["data"]["children"][0]["block_id"]

            # 写入单元格内容
            is_header = (row_idx == 0)
            # 清理链接格式，只保留 URL 或纯文本
            clean_text = cell_data
            # 如果是链接格式 [文本](URL)，提取文本
            link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', cell_data)
            if link_match:
                clean_text = link_match.group(1)  # 只保留显示文本

            text_block = _create_text_block(clean_text, is_bold=is_header)
            resp = requests.post(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{cell_id}/children",
                headers=headers,
                json={"children": [text_block]},
                timeout=60
            )
            if resp.status_code != 200:
                print(f"    ⚠️ 第 {row_idx+1} 行第 {col_idx+1} 列内容写入失败")

        if (row_idx + 1) % 5 == 0:
            print(f"  ✅ 已完成 {row_idx + 1}/{row_count} 行")

    print(f"  ✅ 表格写入完成，共 {row_count} 行")
    return table_id


def update_doc_content(access_token, doc_id, content):
    """向云文档写入纯文本（备用方案）"""
    root_block_id = doc_id
    update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    text_block = _create_text_block(content)
    resp = requests.post(update_url, headers=headers, json={"children": [text_block]}, timeout=60)
    if resp.status_code == 200:
        print(f"  ✅ 文档内容写入完成")
    else:
        print(f"  ⚠️ 写入失败: {resp.text}")


def send_doc_link_message(access_token, receive_id, doc_id, region="西南四省"):
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置，请设置 GitHub Secret")
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
