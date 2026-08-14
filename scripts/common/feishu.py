import requests
import json
import re

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
    在飞书文档中创建表格
    headers: 表头列表，如 ['省份', '城市', '政策名称', '核心申请条件', '补贴标准/金额', '开放申请及截止日期', '政策原文链接']
    rows: 数据行列表，每行是一个字典，key 为表头字段
    """
    root_block_id = doc_id
    update_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children"
    headers_req = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 1. 创建表格
    table_block = {
        "block_type": 11,  # 表格块
        "table": {
            "column_count": len(headers),
            "row_count": len(rows) + 1  # + 表头行
        }
    }
    resp = requests.post(update_url, headers=headers_req, json={"children": [table_block]}, timeout=60)
    resp.raise_for_status()
    table_id = resp.json()["data"]["children"][0]["block_id"]
    print(f"  📊 表格创建成功，列数: {len(headers)}，行数: {len(rows) + 1}")
    
    # 2. 构建表格内容（表头 + 数据行）
    # 获取表格的 children 接口（用于添加行）
    table_children_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{table_id}/children"
    
    # 2.1 添加表头行
    header_row_id = _add_table_row(table_children_url, headers_req, headers, is_header=True)
    print(f"  📌 表头行创建成功")
    
    # 2.2 添加数据行
    for idx, row in enumerate(rows):
        # 将行数据按 headers 顺序转为列表
        row_data = [row.get(h, '') for h in headers]
        _add_table_row(table_children_url, headers_req, row_data, is_header=False, row_idx=idx)
        if (idx + 1) % 10 == 0:
            print(f"  ✅ 已写入 {idx + 1}/{len(rows)} 行")
    
    print(f"  ✅ 表格写入完成，共 {len(rows)} 行数据")
    return table_id


def _add_table_row(table_children_url, headers, cells_data, is_header=False, row_idx=0):
    """
    在表格中添加一行
    table_children_url: 表格的 children 接口 URL
    headers: 请求头
    cells_data: 单元格数据列表
    is_header: 是否为表头行
    """
    # 创建行
    row_block = {
        "block_type": 12,  # 表格行
        "table_row": {}
    }
    resp = requests.post(table_children_url, headers=headers, json={"children": [row_block]}, timeout=60)
    resp.raise_for_status()
    row_id = resp.json()["data"]["children"][0]["block_id"]
    
    # 创建单元格
    cells_url = f"{table_children_url.replace('/children', '')}/{row_id}/children"
    
    for col_idx, cell_data in enumerate(cells_data):
        # 每个单元格是一个 block
        cell_block = {
            "block_type": 13,  # 表格单元格
            "table_cell": {}
        }
        resp_cell = requests.post(cells_url, headers=headers, json={"children": [cell_block]}, timeout=60)
        if resp_cell.status_code != 200:
            print(f"    ⚠️ 第 {row_idx + 1} 行第 {col_idx + 1} 列单元格创建失败")
            continue
        cell_id = resp_cell.json()["data"]["children"][0]["block_id"]
        
        # 向单元格写入内容
        cell_content_url = f"{cells_url.replace('/children', '')}/{cell_id}/children"
        content_to_write = _build_cell_content(cell_data, is_header)
        if content_to_write:
            resp_content = requests.post(cell_content_url, headers=headers, json={"children": content_to_write}, timeout=60)
            if resp_content.status_code != 200:
                print(f"    ⚠️ 第 {row_idx + 1} 行第 {col_idx + 1} 列内容写入失败")
    
    return row_id


def _build_cell_content(cell_data, is_header):
    """
    构建单元格内容
    如果 cell_data 是链接格式 [文本](URL)，则创建带链接的文本块
    """
    if not cell_data:
        return None
    
    # 检测是否包含 Markdown 链接 [文本](URL)
    link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', cell_data)
    if link_match:
        text = link_match.group(1)
        url = link_match.group(2)
        # 只显示文本，实际链接通过飞书文档的链接功能
        # 飞书文档中，链接是通过 text_run 的 style 实现的
        block = {
            "block_type": 3,  # 文本块
            "text": {
                "elements": [
                    {
                        "text_run": {
                            "content": text,
                            "text_element_style": {
                                "link": url  # 飞书文档链接
                            }
                        }
                    }
                ]
            }
        }
        # 如果是表头，加粗
        if is_header:
            block["text"]["elements"][0]["text_run"]["text_element_style"]["bold"] = True
        return [block]
    
    # 普通文本
    block = {
        "block_type": 3,
        "text": {
            "elements": [
                {"text_run": {"content": cell_data}}
            ]
        }
    }
    if is_header:
        block["text"]["elements"][0]["text_run"]["text_element_style"] = {"bold": True}
    
    return [block]


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
