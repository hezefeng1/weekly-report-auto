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

    # ===== 2. 提取关键结论（增加对"本期关键结论"的支持） =====
    conclusions = []
    in_summary = False
    for line in lines:
        if '本期摘要' in line or '本期核心摘要' in line or '本周关键结论' in line or '关键结论' in line or '本期关键结论' in line:
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

    # ===== 3. 提取核心数据速览表（优先）或行业薪酬趋势表（备用） =====
    table_data = []
    in_metric_table = False
    table_type = None  # 'core' 或 'salary'
    used_table_title = None

    for i, line in enumerate(lines):
        # 优先匹配核心数据速览
        if '核心数据速览' in line:
            in_metric_table = True
            table_type = 'core'
            used_table_title = '核心数据速览'
            continue
        # 备用：匹配行业薪酬趋势
        if '行业薪酬趋势' in line or '### 行业薪酬趋势' in line:
            in_metric_table = True
            table_type = 'salary'
            used_table_title = '行业薪酬趋势'
            continue
        
        if in_metric_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 3:
                header_text = ''.join(cells)
                # 跳过表头
                if '关键指标' in header_text and '本期数据' in header_text:
                    continue
                if '岗位类别' in header_text and '平均月薪' in header_text:
                    continue
                if '岗位类别' in header_text and '2026年' in header_text:
                    continue
                # 检查是否是数据行
                has_data = any(re.search(r'[\d,]+\.?\d*', c) for c in cells[:2])
                if has_data and len(cells) >= 3:
                    while len(cells) < 3:
                        cells.append('')
                    table_data.append(cells[:3])
        
        # 遇到下一个二级标题时结束
        if in_metric_table and line.startswith('##') and used_table_title not in line:
            in_metric_table = False
            table_type = None
            used_table_title = None
            continue
        if in_metric_table and line.startswith('###') and '行业薪酬' not in line and '核心数据' not in line:
            in_metric_table = False
            table_type = None
            used_table_title = None

    # ===== 4. 从表格数据提取数据卡片（按行号精准映射） =====
    card_values = {
        '招聘热度': '--',
        '薪酬变化': '--',
        '人才流动': '--',
        '政策动向': '暂无'
    }

    # 优先使用核心数据速览表格（按行号精准映射）
    if table_type == 'core' and len(table_data) >= 6:
        # 行1: 行业整体招聘热度 → 招聘热度
        if len(table_data[0]) >= 2 and table_data[0][1]:
            card_values['招聘热度'] = table_data[0][1]
        # 行4: 兽医/育种专家岗薪酬 → 薪酬变化
        if len(table_data[3]) >= 2 and table_data[3][1]:
            card_values['薪酬变化'] = table_data[3][1]
        # 行6: 行业主动离职率 → 人才流动
        if len(table_data[5]) >= 2 and table_data[5][1]:
            card_values['人才流动'] = table_data[5][1]
    else:
        # 备用：用关键词匹配
        for row in table_data:
            if len(row) >= 2:
                indicator = row[0]
                value = row[1] if row[1] else ''
                if any(kw in indicator for kw in ['招聘热度', '整体招聘']):
                    if value:
                        card_values['招聘热度'] = value
                if any(kw in indicator for kw in ['兽医', '育种专家']):
                    if value:
                        card_values['薪酬变化'] = value
                if any(kw in indicator for kw in ['离职率']):
                    if value:
                        card_values['人才流动'] = value

    # 提取政策动向（从3.3政策环境支持）
    in_policy_section = False
    policy_title = ""
    for line in lines:
        if '政策环境支持' in line or '### 3.3' in line:
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
            clean = re.sub(r'\[.*?\]\(.*?\)', '', clean)
            clean = re.sub(r'\*\*', '', clean)
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
        
        if in_news_section and len(news_items) >= 5:
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
                header_text = ''.join(cells)
                if '企业' in header_text and '招聘策略' in header_text:
                    continue
                if '招聘策略' in header_text and '人才培养' in header_text:
                    continue
                
                if len(cells) >= 5:
                    first_cell = cells[0]
                    first_cell_clean = first_cell.replace('**', '').strip()
                    if any(kw in first_cell_clean for kw in ['牧原', '温氏', '海大', '双胞胎', '正大']):
                        while len(cells) < 6:
                            cells.append('')
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
        if table_type == 'core':
            headers = ['指标', '本期数据', '趋势']
        else:
            headers = ['岗位类别', '平均月薪', '趋势']
        table_html = f'<table><thead><tr><th>{headers[0]}</th><th>{headers[1]}</th><th>{headers[2]}</th></tr></thead><tbody>'
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
