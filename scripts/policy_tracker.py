#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人社补贴政策追踪（西南四省）- 纯文本消息版
使用 msg_type: text，彻底避免 URL 中文字符导致的 230001 错误
"""
import os
import requests
import json
import re
import time
from datetime import datetime
from common.feishu import get_tenant_access_token

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# ========== 敏感词屏蔽规则（精简） ==========
SENSITIVE_RULES = [
    {"type": "any", "words": ["人力社", "卜帖", "贴 补", "发放", "裁员名单"]},
    {"type": "all", "words": ["国家", "补贴通知"]},
    {"type": "all", "words": ["补贴", "申领"]},
    {"type": "regex", "pattern": r"(zip|exe|rar|pdf|doc|docx)$"},
]


def clean_text(text):
    """清洗敏感词，保证返回非空字符串"""
    if not text:
        return "无"
    cleaned = str(text)
    for rule in SENSITIVE_RULES:
        if rule["type"] == "all" and all(w in cleaned for w in rule["words"]):
            for w in rule["words"]:
                cleaned = cleaned.replace(w, "***")
        elif rule["type"] == "any":
            for w in rule["words"]:
                cleaned = cleaned.replace(w, "***")
        elif rule["type"] == "regex":
            cleaned = re.sub(rule["pattern"], "***", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else "无"


def generate_policy_report():
    """调用 DeepSeek 生成政策追踪报告"""
    today = datetime.now().strftime("%Y年%m月%d日")
    system_prompt = """你是人社政策情报分析AI。搜索2026年1月1日之后新发布的企业补贴政策，覆盖四川省、重庆市、云南省、贵州省，只输出一个Markdown表格，表头：省份 | 城市 | 政策名称 | 核心申请条件 | 补贴标准/金额 | 开放申请及截止日期 | 政策原文链接。政策名称列用[名称](URL)格式。只输出表格，不要其他内容。"""
    user_prompt = f"生成2026年人社补贴政策追踪报告（西南四省），政策发布日期2026年1月1日之后，截止当前日期（{today}）仍未过期。"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
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
    """解析 Markdown 表格，返回行列表"""
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
    """提取 Markdown 链接，返回 (显示文本, URL)"""
    match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', text)
    if match:
        return match.group(1), match.group(2)
    return text, None


def send_text_message(access_token, receive_id, rows):
    """
    发送飞书纯文本消息（msg_type: text）
    每条消息最多 10 条政策，超过则分批
    纯文本消息中的 URL 不会被飞书校验，彻底避免 230001 错误
    """
    if not receive_id:
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置")
        return

    # 按省份分组
    province_groups = {}
    for row in rows:
        if len(row) < 7:
            continue
        prov = row[0]
        province_groups.setdefault(prov, []).append(row)

    for province, province_rows in province_groups.items():
        total = len(province_rows)
        MAX_PER_BATCH = 10
        for start in range(0, total, MAX_PER_BATCH):
            batch = province_rows[start:start + MAX_PER_BATCH]
            batch_num = start // MAX_PER_BATCH + 1
            total_batches = (total + MAX_PER_BATCH - 1) // MAX_PER_BATCH

            # 构造纯文本消息内容
            lines = []
            title = f"2026年人社补贴政策追踪 · {province}"
            if total_batches > 1:
                title += f"（{batch_num}/{total_batches}）"
            lines.append(title)
            lines.append("=" * 50)

            for idx, row in enumerate(batch):
                province_raw, city_raw, policy_raw, condition_raw, subsidy_raw, deadline_raw, link_raw = row[:7]

                # 提取政策名称和链接
                display_name, link_url = extract_link(policy_raw)
                display_name = clean_text(display_name) if display_name else "政策"
                _, link_from_raw = extract_link(link_raw)
                final_link = link_from_raw if link_from_raw else link_url
                final_link = final_link if final_link else ""

                # 清洗各字段
                city_cleaned = clean_text(city_raw)
                condition_cleaned = clean_text(condition_raw)[:80]  # 截断防止过长
                subsidy_cleaned = clean_text(subsidy_raw)[:60]
                deadline_cleaned = clean_text(deadline_raw) if deadline_raw else "详见原文"

                # 组装单条政策
                line = f"\n📍 {city_cleaned}  ⏰ {deadline_cleaned}"
                line += f"\n📄 {display_name}"
                line += f"\n📌 {condition_cleaned}"
                line += f"\n💰 {subsidy_cleaned}"
                if final_link:
                    line += f"\n🔗 {final_link}"
                lines.append(line)
                lines.append("-" * 40)

            footer = f"\n📊 本页 {len(batch)} 条，{province} 共 {total} 条"
            if total_batches > 1:
                footer += f"（第 {batch_num}/{total_batches} 部分）"
            lines.append(footer)

            # 拼接消息正文
            text_content = "\n".join(lines)

            # 发送纯文本消息
            send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            payload = {
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": text_content}, ensure_ascii=False)
            }

            resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
            if resp.status_code != 200:
                print(f"  ❌ {province} 第 {batch_num} 批发送失败: {resp.text}")
                resp.raise_for_status()
            else:
                print(f"  ✅ {province} 第 {batch_num}/{total_batches} 批发送成功（{len(batch)} 条）")
            time.sleep(1.5)


def main():
    print("=" * 50)
    print("📋 人社补贴政策追踪（西南四省）")
    print("=" * 50)

    print("\n1. 生成政策追踪报告...")
    md_content = generate_policy_report()
    print("=== DeepSeek 返回的完整 Markdown 内容 ===")
    print(md_content)
    print("=== 内容结束 ===")

    print("\n2. 解析 Markdown 表格...")
    rows = parse_markdown_table_to_list(md_content)
    if not rows:
        print("  ❌ 未能解析出表格数据")
        return
    print(f"  ✅ 解析成功，表头: 7 列，数据: {len(rows)} 行")

    print("\n3. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    print("\n4. 发送纯文本消息...")
    send_text_message(token, RECEIVE_OPEN_ID_POLICY, rows)

    print("\n✅ 政策追踪报告发送完成！")


if __name__ == "__main__":
    main()
