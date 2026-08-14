import requests
import json
import re
import uuid

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


# ========== 飞书云文档相关 ==========

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


def update_doc_with_table(access_token, doc_id, headers, rows):
    """
    在飞书文档中创建表格（使用 /descendant 接口一次性创建完整表格）
    """
    root_block_id = doc_id
    headers_req = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 构建完整表格树
    all_data = [headers] + rows
    row_count = len(all_data)
    col_count = len(headers)

    # 生成唯一 ID
    table_id = f"table_{uuid.uuid4().hex[:8]}"

    # 构建 descendants 和 children_id
    descendants = []
    children_id = []

    # 1. 创建表格块（block_type: 31）
    table_block = {
        "block_id": table_id,
        "block_type": 31,
        "table": {
            "property": {
                "row_size": row_count,
                "column_size": col_count
            }
        },
        "children": []  # 这里放单元格的 block_id
    }

    # 2. 创建所有单元格（block_type: 32）
    for row_idx, row_data in enumerate(all_data):
        for col_idx, cell_data in enumerate(row_data):
            cell_id = f"cell_{row_idx}_{col_idx}_{uuid.uuid4().hex[:4]}"

            # 单元格块
            cell_block = {
                "block_id": cell_id,
                "block_type": 32,  # 表格单元格
                "table_cell": {},
                "children": []  # 这里放单元格内的文本块
            }

            # 向单元格写入内容
            link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', cell_data)
            if link_match:
                text = link_match.group(1)
                url = link_match.group(2)
                text_block = {
                    "block_id": f"text_{row_idx}_{col_idx}_{uuid.uuid4().hex[:4]}",
                    "block_type": 3,
                    "text": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": text,
                                    "text_element_style": {
                                        "link": url
                                    }
                                }
                            }
                        ]
                    },
                    "children": []
                }
                # 表头行加粗
                if row_idx == 0:
                    text_block["text"]["elements"][0]["text_run"]["text_element_style"]["bold"] = True
                cell_block["children"].append(text_block["block_id"])
                descendants.append(text_block)
            else:
                text_block = {
                    "block_id": f"text_{row_idx}_{col_idx}_{uuid.uuid4().hex[:4]}",
                    "block_type": 3,
                    "text": {
                        "elements": [
                            {"text_run": {"content": cell_data if cell_data else ""}}
                        ]
                    },
                    "children": []
                }
                if row_idx == 0:
                    text_block["text"]["elements"][0]["text_run"]["text_element_style"] = {"bold": True}
                cell_block["children"].append(text_block["block_id"])
                descendants.append(text_block)

            table_block["children"].append(cell_id)
            descendants.append(cell_block)

    descendants.append(table_block)
    children_id.append(table_id)

    # 3. 调用 /descendant 接口
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/descendant"
    payload = {
        "index": 0,
        "children_id": children_id,
        "descendants": descendants
    }

    resp = requests.post(url, headers=headers_req, json=payload, timeout=120)
    if resp.status_code != 200:
        print(f"  ❌ 创建表格失败: {resp.text}")
        resp.raise_for_status()

    print(f"  📊 表格创建成功，共 {len(rows)} 行数据")
    return table_id


def parse_markdown_table_to_rows(markdown_text):
    """
    解析 Markdown 表格，返回 headers 和 rows
    """
    lines = markdown_text.strip().split('\n')
    if len(lines) < 2:
        return None, None

    # 跳过分隔行（|---|）
    data_lines = [line for line in lines if '---' not in line]
    if len(data_lines) < 2:
        return None, None

    # 解析表头
    header_line = data_lines[0]
    headers = [h.strip() for h in header_line.split('|') if h.strip()]

    # 解析数据行
    rows = []
    for line in data_lines[1:]:
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if cells:
            row_dict = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row_dict[headers[i]] = cell
            rows.append(row_dict)

    return headers, rows
