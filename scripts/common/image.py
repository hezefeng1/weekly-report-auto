import os
import tempfile
import re
from playwright.sync_api import sync_playwright

def markdown_to_image(markdown_text, output_path="report.png"):
    """
    将人力资源周报 Markdown 内容渲染为 PNG 信息图
    严格按照周报结构解析，无硬编码假数据
    """
    print("=== 开始渲染图片 ===")

    lines = markdown_text.split('\n')
    
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

    # ===== 2. 提取关键结论 =====
    conclusions = []
    in_summary = False
    for line in lines:
        if '本期摘要' in line or '本期核心摘要' in line or '本周关键结论' in line or '关键结论' in line:
            in_summary = True
            continue
        if in_summary:
            if line.strip() == '':
                continue
            if line.startswith('##') or line.startswith('---'):
                break
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

    # ===== 3. 提取核心数据速览表 =====
    table_data = []
    in_metric_table = False

    for line in lines:
        if '核心数据速览' in line:
            in_metric_table = True
            continue
        
        if in_metric_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 3:
                header_text = ''.join(cells)
                if '关键指标' in header_text and '本期数据' in header_text:
                    continue
                has_data = any(re.search(r'[\d,]+\.?\d*', c) for c in cells[:2])
                if has_data and len(cells) >= 3:
                    while len(cells) < 3:
                        cells.append('')
                    table_data.append(cells[:3])
        
        if in_metric_table and line.startswith('##') and '核心数据' not in line:
            in_metric_table = False

    # ===== 4. 从指标表提取数据卡片 =====
    card_values = {
        '招聘热度': '--',
        '薪酬变化': '--',
        '人才流动': '--',
        '政策动向': '暂无'
    }
    
    for row in table_data:
        if len(row) >= 2:
            indicator = row[0]
            value = row[1] if row[1] else ''
            if any(kw in indicator for kw in ['招聘热度', '生猪养殖岗', '招聘']):
                if value:
                    card_values['招聘热度'] = value
            if any(kw in indicator for kw in ['薪酬', '兽医', '月薪']):
                if value:
                    card_values['薪酬变化'] = value
            if any(kw in indicator for kw in ['流动率', '离职', '技术岗']):
                if value:
                    card_values['人才流动'] = value
    
    # 提取政策动向
    in_policy_section = False
    policy_title = ""
    for line in lines:
        if '政策环境支持' in line or '政策' in line and '补贴' in line:
            in_policy_section = True
            continue
        if in_policy_section:
            if line.strip() == '':
                continue
            if line.startswith('###') or line.startswith('##'):
                break
            clean = line.strip()
            if clean.startswith('-') or clean.startswith('•'):
                clean = clean[1:].strip()
            if clean and len(clean) > 5 and len(clean) < 80:
                policy_title = clean[:20] + "..." if len(clean) > 20 else clean
                break
    
    if policy_title:
        card_values['政策动向'] = policy_title

    cards = [
        {"label": "招聘热度", "value": card_values['招聘热度']},
        {"label": "薪酬变化", "value": card_values['薪酬变化']},
        {"label": "人才流动", "value": card_values['人才流动']},
        {"label": "政策动向", "value": card_values['政策动向']},
    ]

    # ===== 5. 提取要闻 =====
    news_items = []
    in_news_section = False
    for line in lines:
        if '人力资源要闻' in line or '## 一、' in line:
            in_news_section = True
            continue
        if in_news_section:
            if line.startswith('##') and '要闻' not in line:
                break
            if line.startswith('---'):
                continue
            if '[' in line and '](' in line and '|' in line:
                title_match = re.search(r'\[([^\]]+)\]\([^\)]+\)', line)
                title_text = title_match.group(1) if title_match else ""
                source_match = re.search(r'【来源：([^】]+)】', line)
                source_text = source_match.group(1) if source_match else ""
                if title_text and len(title_text) > 5:
                    display_text = title_text
                    if source_text:
                        display_text += f"（{source_text}）"
                    if len(display_text) > 60:
                        display_text = display_text[:60] + "..."
                    news_items.append(display_text)
        
        if in_news_section and len(news_items) >= 5:
            break

    if not news_items:
        in_news_section = False
        for line in lines:
            if '人力资源要闻' in line:
                in_news_section = True
                continue
            if in_news_section:
                if line.startswith('##') and '要闻' not in line:
                    break
                clean = line.strip()
                if clean.startswith('-') or clean.startswith('•'):
                    clean = clean[1:].strip()
                    if clean and len(clean) > 10 and len(clean) < 100:
                        clean = re.sub(r'【来源.*?】', '', clean)
                        clean = re.sub(r'〖来源.*?〗', '', clean)
                        clean = clean.strip()
                        news_items.append(clean)
                    if len(news_items) >= 5:
                        break

    # ===== 6. 提取竞品对比表 =====
    competitor_data = []
    in_competitor_table = False

    for line in lines:
        if '竞品HR动态' in line or '## 二、行业竞品HR动态' in line:
            in_competitor_table = True
            continue
        
        if in_competitor_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 5:
                # 跳过表头
                header_text = ''.join(cells)
                if '企业' in header_text and '招聘策略' in header_text:
                    continue
                if '招聘策略' in header_text and '人才培养' in header_text:
                    continue
                
                # 检查是否是竞品数据行（支持带**加粗的格式）
                if len(cells) >= 5:
                    first_cell = cells[0]
                    first_cell_clean = first_cell.replace('**', '').strip()
                    if any(kw in first_cell_clean for kw in ['牧原', '温氏', '海大', '双胞胎', '正大']):
                        while len(cells) < 6:
                            cells.append('')
                        # 清理加粗标记
                        cells = [c.replace('**', '') for c in cells]
                        competitor_data.append(cells[:6])
        
        if in_competitor_table and line.startswith('##') and '竞品' not in line:
            in_competitor_table = False

    # ===== 7. 提取行动建议 =====
    action_items = []
    in_action_table = False
    action_skip = ['HR行动建议', '维度', '具体建议', '数据/案例支撑']
    
    for line in lines:
        if '行动建议' in line or '## 四、' in line:
            in_action_table = True
            continue
        if in_action_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 2:
                header_text = ''.join(cells)
                if any(kw in header_text for kw in action_skip):
                    continue
                if len(cells) >= 2:
                    first_cell = cells[0]
                    if first_cell and len(first_cell) > 2 and not re.match(r'^[\d]+$', first_cell):
                        action_items.append(cells[:3] if len(cells) >= 3 else cells[:2])
        if in_action_table and line.startswith('##') and '行动' not in line:
            break

    # ===== 生成 HTML 模板 =====
    cards_html = ''
    for card in cards:
        cards_html += f'''
        <div class="card">
            <div class="card-value">{card['value']}</div>
            <div class="card-label">{card['label']}</div>
        </div>
        '''

    table_html = ''
    if table_data:
        table_html = '<table><thead><tr><th>指标</th><th>本期数据</th><th>趋势</th></tr></thead><tbody>'
        for row in table_data[:10]:
            table_html += '<tr>'
            for cell in row:
                table_html += f'<td>{cell if cell else "--"}</td>'
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
                    <strong>{title_part}</strong><br>
                    {desc_part}
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
            padding: 16px 20px 14px 20px;
            text-align: center;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            border-left: 4px solid #1a3a5c;
        }}
        .card-value {{
            font-size: 28px;
            font-weight: 700;
            color: #1a3a5c;
            line-height: 1.2;
        }}
        .card-label {{
            font-size: 13px;
            color: #888;
            margin-top: 4px;
        }}
        .body-content {{
            padding: 20px 40px 30px 40px;
        }}
        .section {{
            margin-bottom: 24px;
        }}
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
        th {{
            background: #1a3a5c;
            color: white;
            padding: 10px 14px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 8px 14px;
            border-bottom: 1px solid #e8ecf1;
        }}
        tr:nth-child(even) {{
            background: #f8f9fc;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .conclusion-list, .news-list {{
            list-style: none;
            padding: 0;
        }}
        .conclusion-list li, .news-list li {{
            padding: 8px 0 8px 20px;
            border-bottom: 1px solid #f0f2f5;
            font-size: 14px;
            line-height: 1.6;
            position: relative;
        }}
        .conclusion-list li::before {{
            content: "▸";
            position: absolute;
            left: 0;
            color: #1a3a5c;
            font-weight: 700;
        }}
        .news-list li::before {{
            content: "◆";
            position: absolute;
            left: 0;
            color: #1a3a5c;
            font-size: 10px;
            top: 11px;
        }}
        .news-list li:last-child {{
            border-bottom: none;
        }}
        .action-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}
        .action-item {{
            background: #f5f7fa;
            border-radius: 8px;
            padding: 12px 16px;
            border-left: 3px solid #1a3a5c;
            font-size: 13px;
        }}
        .action-item strong {{
            color: #1a3a5c;
        }}
        .footer {{
            background: #f5f7fa;
            padding: 14px 40px;
            font-size: 12px;
            color: #999;
            text-align: center;
            border-top: 1px solid #e8ecf1;
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="header-title">{title}</div>
        <div class="header-sub">
            <span>{report_date if report_date else "2026年8月"}</span>
            <span>内部参考 · 限时阅读</span>
        </div>
    </div>

    <div class="cards">{cards_html}</div>

    <div class="body-content">
        <div class="section">
            <div class="section-title">📊 数据速览</div>
            {table_html}
        </div>

        <div class="section">
            <div class="section-title">🎯 关键结论</div>
            <ul class="conclusion-list">{conclusions_html}</ul>
        </div>

        <div class="section">
            <div class="section-title">📰 要闻精选</div>
            <ul class="news-list">{news_html}</ul>
        </div>

        <div class="section">
            <div class="section-title">📋 竞品HR策略对比</div>
            {competitor_html}
        </div>

        <div class="section">
            <div class="section-title">📌 HR 行动建议</div>
            <div class="action-grid">{action_html}</div>
        </div>
    </div>

    <div class="footer">数据来源：公开权威渠道 · 仅供内部参考 · 生成时间：{report_date if report_date else "2026年8月"}</div>
</div>
</body>
</html>'''

    # ===== 保存 HTML 为临时文件并截图 =====
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
