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
    在飞书文档中创建表格（分步创建：表格 → 行 → 单元格 → 内容）
    """
    root_block_id = doc_id
    headers_req = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # 1. 创建表格（必须包含 property 字段）
    table_block = {
        "block_type": 11,
        "table": {
            "property": {
                "column_count": len(headers),
                "row_count": len(rows) + 1
            }
        }
    }
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_block_id}/children",
        headers=headers_req,
        json={"children": [table_block]},
        timeout=60
    )
    if resp.status_code != 200:
        print(f"  ❌ 创建表格失败: {resp.text}")
        resp.raise_for_status()
    table_id = resp.json()["data"]["children"][0]["block_id"]
    print(f"  📊 表格创建成功，ID: {table_id}")
    
    # 2. 遍历所有行和列，逐个创建
    all_data = [headers] + rows
    for row_idx, row_data in enumerate(all_data):
        # 2.1 创建行
        row_block = {"block_type": 12, "table_row": {}}
        resp = requests.post(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{table_id}/children",
            headers=headers_req,
            json={"children": [row_block]},
            timeout=60
        )
        if resp.status_code != 200:
            print(f"  ❌ 第 {row_idx+1} 行创建失败: {resp.text}")
            resp.raise_for_status()
        row_id = resp.json()["data"]["children"][0]["block_id"]
        
        # 2.2 为该行创建单元格
        for col_idx, cell_data in enumerate(row_data):
            cell_block = {"block_type": 13, "table_cell": {}}
            resp = requests.post(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{row_id}/children",
                headers=headers_req,
                json={"children": [cell_block]},
                timeout=60
            )
            if resp.status_code != 200:
                print(f"    ⚠️ 第 {row_idx+1} 行第 {col_idx+1} 列单元格创建失败: {resp.text}")
                continue
            cell_id = resp.json()["data"]["children"][0]["block_id"]
            
            # 2.3 向单元格写入内容
            # 检测是否为链接格式 [文本](URL)
            link_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', cell_data)
            if link_match:
                text = link_match.group(1)
                url = link_match.group(2)
                content_block = {
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
                    }
                }
            else:
                content_block = {
                    "block_type": 3,
                    "text": {
                        "elements": [
                            {"text_run": {"content": cell_data}}
                        ]
                    }
                }
            # 表头行加粗
            if row_idx == 0:
                if "text_element_style" not in content_block["text"]["elements"][0]["text_run"]:
                    content_block["text"]["elements"][0]["text_run"]["text_element_style"] = {}
                content_block["text"]["elements"][0]["text_run"]["text_element_style"]["bold"] = True
            
            resp = requests.post(
                f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{cell_id}/children",
                headers=headers_req,
                json={"children": [content_block]},
                timeout=60
            )
            if resp.status_code != 200:
                print(f"    ⚠️ 第 {row_idx+1} 行第 {col_idx+1} 列内容写入失败: {resp.text}")
        
        if (row_idx + 1) % 5 == 0:
            print(f"  ✅ 已完成 {row_idx + 1}/{len(all_data)} 行")
    
    print(f"  ✅ 表格写入完成，共 {len(rows)} 行数据")
    return table_id
