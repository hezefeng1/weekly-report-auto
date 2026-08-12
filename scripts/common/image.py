import os
import tempfile
import re
from playwright.sync_api import sync_playwright

def markdown_to_image(markdown_text, output_path="report.png"):
    """
    将人力资源周报 Markdown 内容渲染为 PNG 信息图
    覆盖所有已知格式变体，不依赖固定章节号或行号
    """
    print("=== 开始渲染图片 ===")

    raw_lines = markdown_text.split('\n')
    
    # ===== 预处理：去除行首 > 符号 =====
    lines = []
    for line in raw_lines:
        cleaned = re.sub(r'^>\s*', '', line)
        lines.append(cleaned)
    
    # ===== 1. 提取标题和日期 =====
    title = "农牧行业人力资源周报"
    report_date = ""
    for line in lines[:15]:
        if '# 农牧行业人力资源周报' in line:
            date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', line)
            if date_match:
                report_date = date_match.group(1)
            title = line.replace('#', '').strip()
        elif '报告周期' in line or '发布日期' in line:
            report_date = line.strip()

    if not report_date:
        import datetime
        report_date = datetime.datetime.now().strftime("%Y年%m月%d日")

    # ===== 2. 提取核心数据速览表 =====
    table_data = []
    in_table = False
    table_end_markers = ['人力资源要闻', '竞品HR动态', '行动建议', '专项关注']
    
    for i, line in enumerate(lines):
        if '核心数据速览' in line:
            in_table = True
            continue
        if in_table and line.startswith('##'):
            if any(marker in line for marker in table_end_markers):
                in_table = False
                continue
        if in_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 3:
                header_text = ''.join(cells)
                if '关键指标' in header_text:
                    is_header = False
                    for kw in ['本期数据', '本周数据', '本期动态', '本期', '趋势']:
                        if kw in header_text:
                            is_header = True
                            break
                    if is_header:
                        continue
                has_data = any(re.search(r'[\d,]+\.?\d*', c) for c in cells[:2])
                has_indicator = any(kw in cells[0] for kw in ['招聘', '薪酬', '流动', '政策', '兽医', '育种', '养殖'])
                if has_data or has_indicator:
                    while len(cells) < 3:
                        cells.append('')
                    cells = [re.sub(r'\*\*', '', c) for c in cells]
                    table_data.append(cells[:3])

    # ===== 3. 提取竞品对比表 =====
    competitor_data = []
    in_competitor = False

    for line in lines:
        if '竞品HR动态' in line or '竞品对比' in line or '行业竞品HR动态' in line:
            in_competitor = True
            continue
        if in_competitor:
            if line.startswith('##') and '竞品' not in line and 'HR动态' not in line:
                in_competitor = False
                continue
            if '|' in line and '---' not in line:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if len(cells) < 4:
                    continue
                header_text = ''.join(cells)
                # 检测表头：企业 + 招聘策略
                if ('企业' in header_text and '招聘策略' in header_text):
                    continue
                # 检测数据行：企业名在第一列
                first_cell = cells[0].replace('**', '').strip()
                if any(kw in first_cell for kw in ['牧原', '温氏', '海大', '双胞胎', '正大']):
                    while len(cells) < 6:
                        cells.append('—')
                    cells = [c.replace('**', '') for c in cells]
                    competitor_data.append(cells[:6])

    # ===== 4. 提取人力资源要闻 =====
    news_items = []
    in_news = False
    for line in lines:
        if '人力资源要闻' in line:
            in_news = True
            continue
        if in_news:
            if line.startswith('##') and '要闻' not in line and '人力资源' not in line:
                in_news = False
                continue
            if '[' in line and '](' in line and '|' in line:
                title_match = re.search(r'\[([^\]]+)\]\([^\)]+\)', line)
                title_text = title_match.group(1) if title_match else ""
                source_match = re.search(r'【来源：([^】]+)】', line)
                source_text = source_match.group(1) if source_match else ""
                if title_text and len(title_text) > 5:
                    display_text = title_text
                    if source_text:
                        if '巨潮资讯' in source_text:
                            source_text = '巨潮'
                        elif '证券时报' in source_text:
                            source_text = '证券时报'
                        elif '第一财经' in source_text:
                            source_text = '第一财经'
                        else:
                            source_text = source_text[:6]
                        display_text += f"（{source_text}）"
                    if len(display_text) > 60:
                        display_text = display_text[:60] + "..."
                    news_items.append(display_text)
        if len(news_items) >= 5:
            break

    # ===== 5. 提取关键结论 =====
    conclusions = []
    summary_keywords = ['本期摘要', '本期核心摘要', '本周关键结论', '关键结论', '本期关键结论', '本期关键信号']
    in_summary = False
    for line in lines:
        matched = False
        for kw in summary_keywords:
            if kw in line:
                matched = True
                break
        if matched:
            in_summary = True
            clean = line.strip()
            for kw in summary_keywords:
                clean = clean.replace(kw, '')
            clean = clean.strip()
            if clean.startswith('：'):
                clean = clean[1:].strip()
            if clean.startswith(':'):
                clean = clean[1:].strip()
            clean = re.sub(r'\*\*', '', clean)
            if clean and len(clean) > 10 and len(clean) < 300:
                items = re.split(r'[①②③④⑤⑥⑦⑧⑨⑩]', clean)
                items = [item.strip() for item in items if item.strip()]
                if items:
                    for item in items:
                        item = re.sub(r'\*\*', '', item)
                        if item:
                            conclusions.append('• ' + item[:150])
                else:
                    conclusions.append('• ' + clean[:150])
            continue
        
        if in_summary:
            if line.strip() == '':
                continue
            if line.startswith('##') or line.startswith('---'):
                in_summary = False
                continue
            clean = line.strip()
            if clean.startswith('-'):
                clean = clean[1:].strip()
            if clean.startswith('>'):
                clean = clean[1:].strip()
            clean = re.sub(r'\*\*', '', clean)
            if clean and len(clean) > 10 and len(clean) < 250:
                conclusions.append('• ' + clean)
                if len(conclusions) >= 5:
                    break

    # ===== 6. 提取HR行动建议 =====
    action_items = []
    in_action = False
    action_skip = ['HR行动建议', '维度', '具体建议', '数据/案例支撑']
    for line in lines:
        if '行动建议' in line or 'HR行动建议' in line:
            in_action = True
            continue
        if in_action:
            if line.startswith('##') and '行动' not in line and '建议' not in line:
                in_action = False
                continue
            if '|' in line and '---' not in line:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if len(cells) >= 2:
                    header_text = ''.join(cells)
                    if any(kw in header_text for kw in action_skip):
                        continue
                    if len(cells) >= 2:
                        first_cell = cells[0]
                        if first_cell and len(first_cell) > 2 and not re.match(r'^[\d]+$', first_cell):
                            cleaned_cells = [re.sub(r'\*\*', '', c) for c in cells]
                            action_items.append(cleaned_cells[:3] if len(cleaned_cells) >= 3 else cleaned_cells[:2])

    # =========================================================
    # ===== 7. 提取本周卡片数据（从固定区块精确抓取） =====
    # =========================================================

    card_mapping = {
        '关键人才争夺': '关键人才争夺',
        '组织效能': '组织效能',
        '人才结构': '人才结构',
        '竞品动作': '竞品动作',
    }
    card_values = {v: '--' for v in card_mapping.values()}

    in_card_section = False
    for line in lines:
        if '本周卡片数据' in line:
            in_card_section = True
            continue
        if in_card_section:
            if line.startswith('##') and '卡片' not in line:
                in_card_section = False
                continue
            for card_key in card_mapping.keys():
                if line.startswith(f'- {card_key}'):
                    content = line.replace(f'- {card_key}', '').strip()
                    if content.startswith('：'):
                        content = content[1:].strip()
                    if content.startswith(':'):
                        content = content[1:].strip()
                    if content:
                        card_values[card_key] = content
                    break

    cards_raw = [
        {"label": "关键人才争夺", "value": card_values['关键人才争夺']},
        {"label": "组织效能", "value": card_values['组织效能']},
        {"label": "人才结构", "value": card_values['人才结构']},
        {"label": "竞品动作", "value": card_values['竞品动作']},
    ]

    # =========================================================
    # ===== 8. 卡片两行拆分 + 生成 HTML =====
    # =========================================================

    cards = []
    for card in cards_raw:
        value = card['value']
        label = card['label']
        first_line = value
        second_line = None
        
        if isinstance(value, str) and '|' in value:
            parts = value.split('|', 1)
            first_line = parts[0].strip()
            second_line = parts[1].strip()
            if first_line and first_line[0] in ['↑', '↓']:
                first_line = f'<span class="up">{first_line[0]}</span>{first_line[1:]}'
        else:
            first_line = value
        
        cards.append({
            'label': label,
            'first_line': first_line,
            'second_line': second_line
        })

    cards_html = ''
    for card in cards:
        if card['second_line']:
            cards_html += f'''
            <div class="card">
                <div class="card-value">{card['first_line']}</div>
                <div class="card-sub">{card['second_line']}</div>
                <div class="card-label">{card['label']}</div>
            </div>
            '''
        else:
            cards_html += f'''
            <div class="card">
                <div class="card-value">{card['first_line']}</div>
                <div class="card-label">{card['label']}</div>
            </div>
            '''

    table_html = ''
    if table_data:
        table_html = '<table><thead><tr><th>指标</th><th>本期数据</th><th>趋势</th></tr></thead><tbody>'
        for row in table_data[:10]:
            table_html += '<tr>'
            for cell in row:
                clean_cell = re.sub(r'\*\*', '', cell)
                table_html += f'<td>{clean_cell if clean_cell else "--"}</td>'
            table_html += '</tr>'
        table_html += '</tbody></table>'
    else:
        table_html = '<p style="color:#999;text-align:center;">暂无数据</p>'

    conclusions_html = ''
    if conclusions:
        for c in conclusions[:5]:
            conclusions_html += f'<li>{c}</li>'
    else:
        conclusions_html = '<li>暂无关键结论</li>'

    news_html = ''
    if news_items:
        for item in news_items[:6]:
            news_html += f'<li>{item}</li>'
    else:
        news_html = '<li>暂无要闻</li>'

    competitor_html = ''
    if competitor_data:
        competitor_html = '<table><thead><tr><th>企业</th><th>招聘策略</th><th>人才培养</th><th>薪酬激励</th><th>组织/人效</th><th>最新动态</th></tr></thead><tbody>'
        for row in competitor_data[:5]:
            competitor_html += '<tr>'
            for cell in row:
                competitor_html += f'<td>{cell if cell else "--"}</td>'
            competitor_html += '</tr>'
        competitor_html += '</tbody></table>'
    else:
        competitor_html = '<p style="color:#999;text-align:center;">暂无竞品数据</p>'

    action_html = ''
    if action_items:
        for row in action_items[:4]:
            if len(row) >= 2:
                title_part = row[0]
                desc_part = row[1] if len(row) > 1 else ""
                action_html += f'''
                <div class="action-item">
                    <div class="action-title">{title_part}</div>
                    <div class="action-desc">{desc_part}</div>
                </div>
                '''
    else:
        action_html = '<div class="action-item">暂无行动建议</div>'

    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
            background: #e8ecf1;
            display: flex;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            width: 1100px;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        .header {{
            background: #1a3a5c;
            padding: 28px 40px 22px 40px;
            color: white;
        }}
        .header-title {{
            font-size: 28px;
            font-weight: 700;
            letter-spacing: 2px;
        }}
        .header-sub {{
            font-size: 14px;
            opacity: 0.7;
            margin-top: 6px;
            display: flex;
            justify-content: space-between;
        }}
        .header-sub span {{
            background: rgba(255,255,255,0.12);
            padding: 2px 14px;
            border-radius: 12px;
            font-size: 12px;
        }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            padding: 24px 40px 20px 40px;
            background: #f5f7fa;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 16px 12px 14px 12px;
            text-align: center;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            border-left: 4px solid #1a3a5c;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 80px;
            min-width: 0;
            word-break: break-word;
        }}
        .card-value {{
            font-size: 20px;
            font-weight: 700;
            color: #1a3a5c;
            line-height: 1.3;
            max-width: 100%;
            text-align: center;
        }}
        .card-value .up {{ color: #2e7d32; }}
        .card-value .down {{ color: #c62828; }}
        .card-sub {{
            font-size: 15px;
            color: #555;
            margin-top: 2px;
            font-weight: 500;
            max-width: 100%;
            text-align: center;
        }}
        .card-label {{ font-size: 13px; color: #888; margin-top: 6px; }}
        .body-content {{ padding: 20px 40px 30px 40px; }}
        .section {{ margin-bottom: 24px; }}
        .section-title {{
            font-size: 18px;
            font-weight: 700;
            color: #1a3a5c;
            border-left: 4px solid #1a3a5c;
            padding-left: 12px;
            margin-bottom: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            border: 1px solid #d0d7e3;
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{ background: #1a3a5c; color: white; padding: 10px 14px; text-align: left; font-weight: 600; }}
        td {{ padding: 8px 14px; border-bottom: 1px solid #e8ecf1; }}
        tr:nth-child(even) {{ background: #f8f9fc; }}
        tr:last-child td {{ border-bottom: none; }}
        .conclusion-list, .news-list {{ list-style: none; padding: 0; }}
        .conclusion-list li, .news-list li {{
            padding: 8px 0 8px 20px;
            border-bottom: 1px solid #f0f2f5;
            font-size: 14px;
            line-height: 1.6;
            position: relative;
        }}
        .conclusion-list li::before {{ content: "▸"; position: absolute; left: 0; color: #1a3a5c; font-weight: 700; }}
        .news-list li::before {{ content: "◆"; position: absolute; left: 0; color: #1a3a5c; font-size: 10px; top: 11px; }}
        .news-list li:last-child {{ border-bottom: none; }}
        .action-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        .action-item {{
            background: #f5f7fa;
            border-radius: 8px;
            padding: 12px 16px;
            border-left: 3px solid #1a3a5c;
            font-size: 13px;
        }}
        .action-item .action-title {{ font-weight: 700; color: #1a3a5c; margin-bottom: 2px; }}
        .action-item .action-desc {{ color: #333; line-height: 1.5; font-size: 13px; }}
        .footer {{
            background: #f5f7fa;
            padding: 14px 40px;
            font-size: 12px;
            color: #999;
            text-align: center;
            border-top: 1px solid #e8ecf1;
        }}
        .up {{ color: #2e7d32; }}
        .down {{ color: #c62828; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="header-title">{title}</div>
        <div class="header-sub">
            <span>{report_date}</span>
            <span>内部参考 · 限时阅读</span>
        </div>
    </div>

    <div class="cards">{cards_html}</div>

    <div class="body-content">
        <div class="section"><div class="section-title">📊 数据速览</div>{table_html}</div>
        <div class="section"><div class="section-title">🎯 关键结论</div><ul class="conclusion-list">{conclusions_html}</ul></div>
        <div class="section"><div class="section-title">📰 要闻精选</div><ul class="news-list">{news_html}</ul></div>
        <div class="section"><div class="section-title">📋 竞品HR策略对比</div>{competitor_html}</div>
        <div class="section"><div class="section-title">📌 HR 行动建议</div><div class="action-grid">{action_html}</div></div>
    </div>

    <div class="footer">数据来源：公开权威渠道 · 仅供内部参考 · 生成时间：{report_date}</div>
</div>
</body>
</html>'''

    # ===== 保存并截图 =====
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.html',
        delete=False,
        encoding='utf-8'
    ) as f:
        f.write(html_content)
        temp_path = f.name

    print(f"  HTML 临时文件: {temp_path}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1140, "height": 1600})
            page.goto(f'file://{temp_path}')
            page.wait_for_timeout(2000)
            page.screenshot(path=output_path, full_page=True)
            browser.close()
        print(f"  ✅ 图片生成成功: {output_path}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    return output_path
