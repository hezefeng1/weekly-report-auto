def sanitize_url(url):
    """清洗 URL，移除中文字符，只保留 ASCII 部分，防止飞书校验报错"""
    if not url:
        return ""
    # 如果是完整 URL，提取协议和域名，路径部分只保留文件名
    # 例如：https://cdhrss.chengdu.gov.cn/2026/0105/稳岗扩岗专项补贴通知.html
    # 变为：https://cdhrss.chengdu.gov.cn/2026/0105/policy.html
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        path = parsed.path
        # 如果路径包含中文，替换为 policy.html
        if re.search(r'[\u4e00-\u9fff]', path):
            path = re.sub(r'/.*?([^/]*?)([\u4e00-\u9fff]+[^/]*\.html?)', r'/\1policy.html', path)
            path = re.sub(r'[\u4e00-\u9fff]+', 'policy', path)
        return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
    except:
        # 任何错误返回原 URL（但不太可能出错）
        return url

def send_rich_text_message(access_token, receive_id, rows):
    """发送飞书富文本消息，每条政策单独显示，URL 清洗后发送"""
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
                display_name = clean_text(display_name) if display_name else "政策"
                _, link_from_raw = extract_link(link_raw)
                final_link = link_from_raw if link_from_raw else link_url
                # ★ 关键：清洗 URL，移除中文字符 ★
                final_link = sanitize_url(final_link) if final_link else ""

                city_cleaned = clean_text(city_raw)
                condition_cleaned = clean_text(condition_raw)[:80]
                subsidy_cleaned = clean_text(subsidy_raw)[:60]
                deadline_cleaned = clean_text(deadline_raw) if deadline_raw else "详见原文"

                # 构造单条政策（使用多个标签实现富文本效果）
                row_parts = []

                # 城市 + 截止日期
                row_parts.append({"tag": "text", "text": f"📍 {city_cleaned}  "})
                row_parts.append({"tag": "text", "text": f"⏰ {deadline_cleaned}\n"})

                # 政策名称（链接）
                if final_link and not re.search(r'[\u4e00-\u9fff]', final_link):
                    row_parts.append({"tag": "a", "text": f"📄 {display_name}", "href": final_link})
                else:
                    row_parts.append({"tag": "text", "text": f"📄 {display_name}"})
                row_parts.append({"tag": "text", "text": "\n"})

                # 条件
                row_parts.append({"tag": "text", "text": f"📌 {condition_cleaned}\n"})
                # 补贴
                row_parts.append({"tag": "text", "text": f"💰 {subsidy_cleaned}"})

                content_2d.append(row_parts)

                if idx < len(batch) - 1:
                    content_2d.append([{"tag": "text", "text": "─────────────────────"}])

            # 底部统计
            footer = f"📊 本页 {len(batch)} 条，{province} 共 {total} 条"
            if total_batches > 1:
                footer += f"（第 {batch_num}/{total_batches} 部分）"
            content_2d.append([{"tag": "text", "text": clean_text(footer)}])

            # 构建 payload
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

            resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
            if resp.status_code != 200:
                print(f"  ❌ {province} 第 {batch_num} 批发送失败: {resp.text}")
                resp.raise_for_status()
            else:
                print(f"  ✅ {province} 第 {batch_num}/{total_batches} 批发送成功（{len(batch)} 条）")
            time.sleep(1.5)
