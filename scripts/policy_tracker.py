#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人社补贴政策追踪（西南四省）- 最终完整版（含调试日志）
- 使用富文本（post）消息
- 每条政策只用一个 text 标签
- URL 自动清洗，移除中文字符
- 每批最多 10 条
- 打印飞书响应，便于排查消息未送达问题
"""
import os
import sys
import requests
import json
import re
import time
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from common.feishu import get_tenant_access_token

# ========== 环境变量检查 ==========
REQUIRED_ENV = ["FEISHU_APP_ID", "FEISHU_APP_SECRET", "RECEIVE_OPEN_ID_POLICY", "DEEPSEEK_API_KEY"]
missing = [e for e in REQUIRED_ENV if not os.environ.get(e)]
if missing:
    print(f"❌ 缺少环境变量: {', '.join(missing)}")
    sys.exit(1)

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# ========== 敏感词清洗 ==========
def clean_text(text, max_len=300):
    if not text:
        return "无"
    cleaned = str(text)
    for old, new in [("人力社", "***"), ("卜帖", "***"), ("贴 补", "***"), ("发放", "***"), ("裁员名单", "***")]:
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "…"
    return cleaned if cleaned else "无"

# ========== URL 清洗，移除中文字符 ==========
def sanitize_url(url):
    """将 URL 路径中的中文字符替换为 'policy'，保留域名和后缀"""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        path = parsed.path
        if re.search(r'[\u4e00-\u9fff]', path):
            if path.endswith('.html'):
                path = re.sub(r'/([^/]*?)([\u4e00-\u9fff]+[^/]*\.html)$', r'/policy.html', path)
            elif path.endswith('.htm'):
                path = re.sub(r'/([^/]*?)([\u4e00-\u9fff]+[^/]*\.htm)$', r'/policy.htm', path)
            else:
                path = re.sub(r'/([^/]*?)([\u4e00-\u9fff]+[^/]*)$', r'/policy', path)
            path = re.sub(r'/+', '/', path)
        return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
    except:
        return url

def generate_policy_report():
    today = datetime.now().strftime("%Y年%m月%d日")
    system_prompt = """你是人社政策情报分析AI。搜索2026年1月1日之后新发布的企业补贴政策，覆盖四川省、重庆市、云南省、贵州省，只输出一个Markdown表格，表头：省份 | 城市 | 政策名称 | 核心申请条件 | 补贴标准/金额 | 开放申请及截止日期 | 政策原文链接。政策名称列用[名称](URL)格式。只输出表格，不要其他内容。"""
    user_prompt = f"生成2026年人社补贴政策追踪报告（西南四省），政策发布日期2026年1月1日之后，截止当前日期（{today}）仍未过期。"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.3,
        "stream": False
    }
    print("  📡 正在联网搜索西南四省人社补贴政策...")
    resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=300)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    print(f"  ✅ 生成完成，共 {len(content)} 字符")
    return content

def parse_markdown_table_to_list(markdown_text):
    lines = markdown_text.strip().split('\n')
    if len(lines) < 2:
        return None
    data_lines = [line for line in lines if '---' not in line]
    if len(data_lines) < 2:
        return None
    rows = []
    for line in data_lines[1:]:
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if cells:
            rows.append(cells)
    return rows

def extract_link(text):
    match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', text)
    if match:
        return match.group(1), match.group(2)
    return text, None

def send_rich_text_message(access_token, receive_id, rows):
    if not receive_id:
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置")
        return

    # 打印接收人ID（脱敏显示前后几位）
    masked = receive_id[:4] + "****" + receive_id[-4:] if len(receive_id) > 8 else receive_id
    print(f"  📤 接收人 (open_id): {masked}")

    groups = {}
    for row in rows:
        if len(row) < 7:
            continue
        prov = row[0]
        groups.setdefault(prov, []).append(row)

    print(f"  📊 省份分组: {list(groups.keys())}")

    for province, province_rows in groups.items():
        total = len(province_rows)
        MAX_PER_BATCH = 10
        for start in range(0, total, MAX_PER_BATCH):
            batch = province_rows[start:start + MAX_PER_BATCH]
            batch_num = start // MAX_PER_BATCH + 1
            total_batches = (total + MAX_PER_BATCH - 1) // MAX_PER_BATCH

            content_2d = []

            title = f"2026年人社补贴政策追踪 · {province}"
            if total_batches > 1:
                title += f"（{batch_num}/{total_batches}）"
            content_2d.append([{"tag": "text", "text": clean_text(title)}])
            content_2d.append([{"tag": "text", "text": "─────────────────────"}])

            for idx, row in enumerate(batch):
                province_raw, city_raw, policy_raw, condition_raw, subsidy_raw, deadline_raw, link_raw = row[:7]

                name, url = extract_link(policy_raw)
                _, link_from_raw = extract_link(link_raw)
                final_url = link_from_raw if link_from_raw else url
                final_url = sanitize_url(final_url) if final_url else ""

                name = clean_text(name, 60)
                city = clean_text(city_raw, 20)
                condition = clean_text(condition_raw, 80)
                subsidy = clean_text(subsidy_raw, 60)
                deadline = clean_text(deadline_raw, 30) if deadline_raw else "详见原文"

                line = f"📍 {city}  ⏰ {deadline}  📄 {name}  📌 {condition}  💰 {subsidy}"
                if final_url:
                    line += f"  🔗 {final_url}"

                content_2d.append([{"tag": "text", "text": line}])
                if idx < len(batch) - 1:
                    content_2d.append([{"tag": "text", "text": "─────────────────────"}])

            footer = f"📊 本页 {len(batch)} 条，{province} 共 {total} 条"
            if total_batches > 1:
                footer += f"（第 {batch_num}/{total_batches} 部分）"
            content_2d.append([{"tag": "text", "text": clean_text(footer)}])

            post_content = {"post": {"zh_cn": {"title": f"人社补贴政策 · {province}", "content": content_2d}}}
            payload = {
                "receive_id": receive_id,
                "msg_type": "post",
                "content": json.dumps(post_content, ensure_ascii=False)
            }

            print(f"  📤 发送 {province} 第 {batch_num}/{total_batches} 批（{len(batch)} 条）...")
            print(f"     payload 大小: {len(json.dumps(payload))} 字节")

            url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                print(f"     HTTP 状态码: {resp.status_code}")
                print(f"     响应内容: {resp.text}")

                if resp.status_code != 200:
                    print(f"  ❌ {province} 第 {batch_num} 批发送失败")
                    resp.raise_for_status()
                else:
                    data = resp.json()
                    if data.get('code') == 0:
                        msg_id = data.get('data', {}).get('message_id')
                        print(f"  ✅ {province} 第 {batch_num}/{total_batches} 批发送成功，message_id: {msg_id}")
                    else:
                        print(f"  ⚠️ 飞书返回非零 code: {data}")
            except Exception as e:
                print(f"  ❌ 发送异常: {e}")
                raise

            time.sleep(1.5)

def main():
    print("=" * 50)
    print("📋 人社补贴政策追踪（西南四省）")
    print("=" * 50)

    print("\n🔍 检查环境变量...")
    print(f"  FEISHU_APP_ID: {'已设置' if FEISHU_APP_ID else '❌ 未设置'}")
    print(f"  FEISHU_APP_SECRET: {'已设置' if FEISHU_APP_SECRET else '❌ 未设置'}")
    print(f"  RECEIVE_OPEN_ID_POLICY: {'已设置' if RECEIVE_OPEN_ID_POLICY else '❌ 未设置'}")
    print(f"  DEEPSEEK_API_KEY: {'已设置' if DEEPSEEK_API_KEY else '❌ 未设置'}")

    print("\n1. 生成政策追踪报告...")
    md_content = generate_policy_report()
    print("=== DeepSeek 返回的完整 Markdown 内容 ===")
    print(md_content)
    print("=== 内容结束 ===")

    print("\n2. 解析 Markdown 表格...")
    rows = parse_markdown_table_to_list(md_content)
    if not rows:
        print("  ❌ 未能解析出表格数据")
        sys.exit(1)
    print(f"  ✅ 解析成功，表头: 7 列，数据: {len(rows)} 行")

    print("\n3. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
    if not token:
        print("  ❌ 获取 token 失败")
        sys.exit(1)
    print("  ✅ token 获取成功")

    print("\n4. 发送富文本消息（每批最多10条，URL自动清洗）...")
    send_rich_text_message(token, RECEIVE_OPEN_ID_POLICY, rows)

    print("\n✅ 政策追踪报告发送完成！")

if __name__ == "__main__":
    main()
