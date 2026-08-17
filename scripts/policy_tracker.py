#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人社补贴政策追踪（西南四省）- 最终稳定美观版
- 使用富文本（post）消息，保证排版美观
- URL自动清洗，移除中文字符，避免飞书校验报错
- 每批最多8条，防止超长
- 每步都有详细日志，方便调试
"""
import os
import sys
import requests
import json
import re
import time
from datetime import datetime
from urllib.parse import urlparse, urlunparse

# ==================== 环境变量检查 ====================
REQUIRED_ENV = ["FEISHU_APP_ID", "FEISHU_APP_SECRET", "RECEIVE_OPEN_ID_POLICY", "DEEPSEEK_API_KEY"]
missing = [e for e in REQUIRED_ENV if not os.environ.get(e)]
if missing:
    print(f"❌ 缺少环境变量: {', '.join(missing)}")
    print("请先设置这些环境变量再运行")
    sys.exit(1)

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# ========== 从 common.feishu 导入 token 获取函数 ==========
try:
    from common.feishu import get_tenant_access_token
except ImportError:
    print("❌ 无法导入 common.feishu，请确保 common/feishu.py 存在")
    sys.exit(1)

# ========== 敏感词屏蔽规则（精简） ==========
SENSITIVE_RULES = [
    {"type": "any", "words": ["人力社", "卜帖", "贴 补", "发放", "裁员名单"]},
    {"type": "all", "words": ["国家", "补贴通知"]},
    {"type": "all", "words": ["补贴", "申领"]},
    {"type": "regex", "pattern": r"(zip|exe|rar|pdf|doc|docx)$"},
]

def clean_text(text, max_len=200):
    """清洗敏感词，并截断过长文本"""
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
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "…"
    return cleaned if cleaned else "无"

def sanitize_url(url):
    """清洗 URL，将中文部分替换为 'policy'，防止飞书校验报错"""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        path = parsed.path
        # 如果路径包含中文，替换为 policy.html
        if re.search(r'[\u4e00-\u9fff]', path):
            # 提取文件名后缀 .html
            if path.endswith('.html'):
                path = re.sub(r'/([^/]*?)([\u4e00-\u9fff]+[^/]*\.html$)', r'/policy.html', path)
            else:
                path = re.sub(r'/([^/]*?)([\u4e00-\u9fff]+[^/]*)$', r'/policy', path)
            # 移除所有中文字符
            path = re.sub(r'[\u4e00-\u9fff]+', 'policy', path)
            # 清理多余的斜杠
            path = re.sub(r'/+', '/', path)
        return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
    except:
        return url  # 出错则保留原样，但一般不会

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
    try:
        resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=300)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        print(f"  ✅ 生成完成，共 {len(content)} 字符")
        return content
    except Exception as e:
        print(f"  ❌ DeepSeek 请求失败: {e}")
        sys.exit(1)

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

def send_rich_text_message(access_token, receive_id, rows):
    """发送飞书富文本消息，每条政策显示为多行，URL 清洗，每批最多8条"""
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
        MAX_PER_BATCH = 8   # 每批最多8条，保证不超限
        for start in range(0, total, MAX_PER_BATCH):
            batch = province_rows[start:start + MAX_PER_BATCH]
            batch_num = start // MAX_PER_BATCH + 1
            total_batches = (total + MAX_PER_BATCH - 1) // MAX_PER_BATCH

            content_2d = []

            # 标题
            title = f"2026年人社补贴政策追踪 · {province}"
            if total_batches > 1:
                title += f"（{batch_num}/{total_batches}）"
            content_2d.append([{"tag": "text", "text": clean_text(title), "style": ["bold"]}])
            content_2d.append([{"tag": "text", "text": "─────────────────────"}])

            for idx, row in enumerate(batch):
                province_raw, city_raw, policy_raw, condition_raw, subsidy_raw, deadline_raw, link_raw = row[:7]

                # 提取政策名称和链接
                display_name, link_url = extract_link(policy_raw)
                display_name = clean_text(display_name, 120) if display_name else "政策"
                _, link_from_raw = extract_link(link_raw)
                final_link = link_from_raw if link_from_raw else link_url
                final_link = sanitize_url(final_link) if final_link else ""

                city_cleaned = clean_text(city_raw, 30)
                condition_cleaned = clean_text(condition_raw, 100)
                subsidy_cleaned = clean_text(subsidy_raw, 80)
                deadline_cleaned = clean_text(deadline_raw, 30) if deadline_raw else "详见原文"

                # 构造该政策的富文本段落（多个标签，实现换行和粗体效果）
                line_parts = []

                # 第一行：📍 城市  ⏰ 截止日期
                line_parts.append({"tag": "text", "text": f"📍 {city_cleaned}  "})
                line_parts.append({"tag": "text", "text": f"⏰ {deadline_cleaned}\n"})

                # 第二行：政策名称（带链接，如果清洗后可用）
                if final_link and not re.search(r'[\u4e00-\u9fff]', final_link):
                    line_parts.append({"tag": "a", "text": f"📄 {display_name}", "href": final_link})
                else:
                    line_parts.append({"tag": "text", "text": f"📄 {display_name}"})
                line_parts.append({"tag": "text", "text": "\n"})

                # 第三行：核心申请条件（加粗标签）
                line_parts.append({"tag": "text", "text": "📌 ", "style": ["bold"]})
                line_parts.append({"tag": "text", "text": f"{condition_cleaned}\n"})

                # 第四行：补贴标准（加粗标签）
                line_parts.append({"tag": "text", "text": "💰 ", "style": ["bold"]})
                line_parts.append({"tag": "text", "text": subsidy_cleaned})

                content_2d.append(line_parts)

                if idx < len(batch) - 1:
                    content_2d.append([{"tag": "text", "text": "─────────────────────"}])

            # 底部统计
            footer = f"📊 本页 {len(batch)} 条，{province} 共 {total} 条"
            if total_batches > 1:
                footer += f"（第 {batch_num}/{total_batches} 部分）"
            content_2d.append([{"tag": "text", "text": clean_text(footer)}])

            # 构建 JSON
            post_content = {
                "post": {
                    "zh_cn": {
                        "title": f"人社补贴政策 · {province}",
                        "content": content_2d
                    }
                }
            }
            payload = {
                "receive_id": receive_id,
                "msg_type": "post",
                "content": json.dumps(post_content, ensure_ascii=False)
            }

            send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            try:
                resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
                if resp.status_code != 200:
                    print(f"  ❌ {province} 第 {batch_num} 批发送失败: {resp.text}")
                    resp.raise_for_status()
                else:
                    print(f"  ✅ {province} 第 {batch_num}/{total_batches} 批发送成功（{len(batch)} 条）")
            except Exception as e:
                print(f"  ❌ {province} 第 {batch_num} 批发送异常: {e}")
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
    try:
        token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
        if not token:
            print("  ❌ 获取 token 失败，返回空值")
            sys.exit(1)
        print("  ✅ token 获取成功")
    except Exception as e:
        print(f"  ❌ 获取 token 异常: {e}")
        sys.exit(1)

    print("\n4. 发送富文本消息（每批最多8条，URL自动清洗）...")
    send_rich_text_message(token, RECEIVE_OPEN_ID_POLICY, rows)

    print("\n✅ 政策追踪报告发送完成！")

if __name__ == "__main__":
    main()
