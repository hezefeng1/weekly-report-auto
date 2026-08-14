import os
import tempfile
import re
from playwright.sync_api import sync_playwright

def markdown_to_image(markdown_text, output_path="report.png"):
    """
    通用 Markdown 渲染为 PNG 图片
    自动识别周报类型（人力资源 / 农牧市场），适配不同的卡片和表格结构
    """
    print("=== 开始渲染图片 ===")

    raw_lines = markdown_text.split('\n')
    
    # ===== 预处理：去除行首 > 符号 =====
    lines = []
    for line in raw_lines:
        cleaned = re.sub(r'^>\s*', '', line)
        lines.append(cleaned)
    
    # ===== 1. 提取标题和日期 =====
    title = "农牧行业周报"
    report_date = ""
    report_type = 'hr'
    
    for line in lines[:15]:
        if '人力资源' in line and '周报' in line:
            title = "农牧行业人力资源周报"
            report_type = 'hr'
        elif '农牧行业周报' in line and '人力资源' not in line:
            title = "农牧行业周报"
            report_type = 'agri'
        
        date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', line)
        if date_match:
            report_date = date_match.group(1)
    
    if not report_date:
        import datetime
        report_date = datetime.datetime.now().strftime("%Y年%m月%d日")

    # ===== 2. 提取核心数据速览表 =====
    table_data = []
    in_table = False
    table_end_markers = ['人力资源要闻', '行业要闻', '竞品动态', '行动建议', '专项关注']
    
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
                if '关键指标' in header_text or ('指标' in header_text and '本期数据' in header_text):
                    is_header = True
                    for kw in ['本期数据', '本周数据', '本期']:
                        if kw in header_text:
                            is_header = True
                            break
                    if is_header:
                        continue
                has_data = any(re.search(r'[\d,]+\.?\d*', c) for c in cells[:2])
                if has_data and len(cells) >= 3:
                    while len(cells) < 3:
                        cells.append('')
                    cells = [re.sub(r'\*\*', '', c) for c in cells]
                    table_data.append(cells[:3])

    # ===== 3. 提取竞品对比表 =====
    competitor_data = []
    in_competitor = False

    if report_type == 'agri':
        competitor_headers = ['企业', '财务表现', '战略动态', '经营动作', '最新简讯']
        company_names = ['牧原股份', '温氏股份', '海大集团', '正大集团', '双胞胎集团']
    else:
        competitor_headers = ['企业', '招聘策略', '人才培养', '薪酬激励', '组织/人效', '最新动态']
        company_names = ['牧原股份', '温氏股份', '海大集团', '双胞胎集团', '正大集团']

    for line in lines:
        if '竞品动态' in line or '竞品HR动态' in line or '行业竞品HR动态' in line:
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
                if '企业' in header_text:
                    continue
                first_cell = cells[0].replace('**', '').strip()
                if any(kw in first_cell for kw in company_names):
                    target_len = len(competitor_headers)
                    while len(cells) < target_len:
                        cells.append('—')
                    cells = [c.replace('**', '') for c in cells]
                    if len(cells) > 0:
                        last_idx = len(cells) - 1
                        if '[' in cells[last_idx] and '](' in cells[last_idx]:
                            match = re.search(r'\[([^\]]+)\]\([^\)]+\)', cells[last_idx])
                            if match:
                                cells[last_idx] = match.group(1)
                    competitor_data.append(cells[:target_len])

    # ===== 4. 提取要闻 =====
    news_items = []
    in_news = False
    news_keywords = ['人力资源要闻', '行业要闻']
    for line in lines:
        if any(kw in line for kw in news_keywords):
            in_news = True
            continue
        if in_news:
            if line.startswith('##') and '要闻' not in line and '人力资源' not in line and '行业' not in line:
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

    # ===== 5. 提取关键结论（增强兼容性） =====
    conclusions = []
    in_conclusion_section = False
    conclusion_markers = ['本周关键结论', '关键结论', '本期关键结论', '核心判断']
    
    for line in lines:
        if any(marker in line for marker in conclusion_markers):
            in_conclusion_section = True
            continue
        
        if in_conclusion_section:
            if line.startswith('##') and '结论' not in line and '关键' not in line:
                in_conclusion_section = False
                continue
            if line.startswith('###'):
                in_conclusion_section = False
                continue
            
            clean = line.strip()
            if not clean:
                continue
            
            # 格式1：> - 内容（标准格式）
            if clean.startswith('> - '):
                content = clean[4:].strip()
                content = re.sub(r'\*\*', '', content)
                if content and len(content) > 5:
                    conclusions.append('• ' + content)
                continue
            
            # 格式2：> 内容（没有短横线）
            if clean.startswith('> '):
                content = clean[2:].strip()
                content = re.sub(r'\*\*', '', content)
                if content:
                    if '①' in content or '②' in content or '③' in content or '④' in content or '⑤' in content:
                        parts = re.split(r'[①②③④⑤]', content)
                        for part in parts:
                            part = part.strip()
                            if part and len(part) > 5:
                                conclusions.append('• ' + part)
                    else:
                        conclusions.append('• ' + content)
                continue
            
            # 格式3：- 内容（普通列表，带短横线）
            if clean.startswith('- '):
                content = clean[2:].strip()
                content = re.sub(r'\*\*', '', content)
                if content and len(content) > 5:
                    conclusions.append('• ' + content)
                continue
            
            # 格式4：**关键词**：内容（老格式，兜底）
            if clean.startswith('**') and '**' in clean[2:]:
                content = re.sub(r'\*\*', '', clean)
                content = re.sub(r'^[：:]\s*', '', content)
                if content and len(content) > 5:
                    conclusions.append('• ' + content)
                continue
            
            # 格式5：普通文本（兜底）
            if len(clean) > 10 and not clean.startswith('|') and '【来源' not in clean and '```' not in clean:
                conclusions.append('• ' + clean[:150])

    # ===== 6. 提取行动建议（表格格式，清理加粗符号） =====
    action_items = []
    in_action_section = False
    
    for line in lines:
        if '行动建议' in line:
            in_action_section = True
            continue
        
        if not in_action_section:
            continue
        
        if line.startswith('##') and '行动' not in line and '建议' not in line:
            in_action_section = False
            break
        
        clean = line.strip()
        if not clean:
            continue
        
        if '|' in clean and '---' not in clean:
            cells = [c.strip() for c in clean.split('|') if c.strip()]
            if len(cells) >= 3:
                header_text = ''.join(cells)
                if any(kw in header_text for kw in ['序号', '触发场景', '行动建议', '维度', '具体建议', '数据/案例支撑']):
                    continue
                if len(cells) >= 3:
                    # 清理所有单元格中的 ** 标记
                    cleaned_cells = [re.sub(r'\*\*', '', c) for c in cells]
                    action_items.append(cleaned_cells[:3] if len(cleaned_cells) >= 3 else cleaned_cells[:2])

    # ===== 7. 提取卡片数据 =====
    card_data = []
    in_card_section = False
    
    for line in lines:
        if '##' in line and '卡片' in line:
            in_card_section = True
            continue
        
        if in_card_section:
            if line.startswith('##') and '卡片' not in line:
                in_card_section = False
                continue
            
            if line.startswith('- ') and ' | ' in line:
                content = line[2:].strip()
                if '：' in content:
                    name = content.split('：')[0].strip()
                    rest = content.split('：')[1].strip() if len(content.split('：')) > 1 else ""
                    if ' | ' in rest:
                        value = rest.split(' | ')[0].strip()
                        change = rest.split(' | ')[1].strip() if len(rest.split(' | ')) > 1 else ""
                        value = value.strip('*')
                        change = change.strip('*')
                        card_data.append({
                            'name': name,
                            'value': value,
                            'change': change
                        })
                    else:
                        rest = rest.strip('*')
                        card_data.append({
                            'name': name,
                            'value': rest,
                            'change': ""
                        })

    # ===== 8. 卡片渲染 =====
    cards_html = ''
    if card_data and len(card_data) >= 4:
        for card in card_data[:4]:
            cards_html += f'''
            <div class="card">
                <div class="card-name">{card['name']}</div>
                <div class="card-value">{card['value']}</div>
                <div class="card-change">{card['change']}</div>
            </div>
            '''
    else:
        for i in range(4):
            cards_html += f'''
            <div class="card">
                <div class="card-name">--</div>
                <div class="card-value">--</div>
                <div class="card-change">--</div>
            </div>
            '''

    # ===== 9. 生成表格 =====
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

    # ===== 10. 生成结论 =====
    conclusions_html = ''
    if conclusions:
        for c in conclusions[:5]:
            conclusions_html += f'<li>{c}</li>'
    else:
        conclusions_html = '<li>暂无关键结论</li>'

    # ===== 11. 生成要闻 =====
    news_html = ''
    if news_items:
        for item in news_items[:6]:
            news_html += f'<li>{item}</li>'
    else:
        news_html = '<li>暂无要闻</li>'

    # ===== 12. 生成竞品表格 =====
    competitor_html = ''
    if competitor_data:
        competitor_html = f'<table><thead><tr>'
        for h in competitor_headers:
            competitor_html += f'<th>{h}</th>'
        competitor_html += '</tr></thead><tbody>'
        for row in competitor_data[:5]:
            competitor_html += '<tr>'
            for cell in row:
                competitor_html += f'<td>{cell if cell else "--"}</td>'
            competitor_html += '</tr>'
        competitor_html += '</tbody></table>'
    else:
        competitor_html = '<p style="color:#999;text-align:center;">暂无竞品数据</p>'

    # ===== 13. 生成行动建议HTML（清理加粗符号） =====
    action_html = ''
    if action_items:
        for item in action_items[:4]:
            if isinstance(item, list) and len(item) >= 2:
                title_part = re.sub(r'\*\*', '', item[0])
                desc_part = re.sub(r'\*\*', '', item[1]) if len(item) > 1 else ""
                action_html += f'''
                <div class="action-item">
                    <div class="action-title">{title_part}</div>
                    <div class="action-desc">{desc_part}</div>
                </div>
                '''
            elif isinstance(item, str):
                item = re.sub(r'\*\*', '', item)
                action_html += f'''
                <div class="action-item">
                    <div class="action-title">{item[:20]}</div>
                    <div class="action-desc">{item[20:] if len(item) > 20 else ""}</div>
                </div>
                '''
    else:
        action_html = '<div class="action-item">暂无行动建议</div>'

    # ===== 14. 完整HTML模板 =====
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
        .card-name {{
            font-size: 14px;
            font-weight: 600;
            color: #888;
            margin-bottom: 4px;
        }}
        .card-value {{
            font-size: 22px;
            font-weight: 700;
            color: #1a3a5c;
            line-height: 1.2;
            max-width: 100%;
            text-align: center;
        }}
        .card-change {{
            font-size: 15px;
            font-weight: 500;
            color: #555;
            margin-top: 2px;
        }}
        .card-value .up {{ color: #2e7d32; }}
        .card-value .down {{ color: #c62828; }}
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
        <div class="section"><div class="section-title">📋 竞品动态对比</div>{competitor_html}</div>
        <div class="section"><div class="section-title">📌 行动建议</div><div class="action-grid">{action_html}</div></div>
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
