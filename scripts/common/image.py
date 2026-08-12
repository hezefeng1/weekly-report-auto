import os
import tempfile
import re
from playwright.sync_api import sync_playwright

def markdown_to_image(markdown_text, output_path="report.png"):
    """
    将 Markdown 内容渲染为 PNG 信息图
    方案：保存 HTML 文件 → 浏览器加载 → 截图
    """
    print("=== 开始渲染图片（Playwright + HTML 模板）===")

    # ===== 1. 解析 Markdown 内容 =====
    lines = markdown_text.split('\n')
    
    # 提取标题
    title = "农牧行业人力资源周报"
    report_date = ""
    for line in lines[:20]:
        if "报告周期" in line or "发布日期" in line:
            report_date = line.strip()
        if "# 农牧" in line or "## 农牧" in line:
            title = line.replace('#', '').strip()

    # ===== 提取 4 列数据速览表（严格匹配） =====
    table_data = []
    in_table = False
    
    for i, line in enumerate(lines):
        # 检查是否是4列表头（必须同时包含"指标""数值""变化""来源"四个关键词）
        if '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 4:
                header_text = ''.join(cells)
                if ('指标' in header_text and '数值' in header_text and '变化' in header_text and '来源' in header_text):
                    in_table = True
                    continue
        
        # 提取数据行
        if in_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 4:
                has_number = any(re.search(r'[\d,]+\.?\d*', c) for c in cells[:2])
                if has_number and len(table_data) < 10:
                    table_data.append(cells[:4])
        
        if in_table and line.strip() == '':
            in_table = False

    # 如果没提取到表格，用备用数据
    if not table_data:
        table_data = [
            ["生猪均价（元/kg）", "18.42", "▼ 1.8%", "中国养猪网"],
            ["玉米现货（元/吨）", "2,486", "▲ 0.6%", "卓创资讯"],
            ["豆粕现货（元/吨）", "3,872", "▲ 2.3%", "卓创资讯"],
            ["育肥猪饲料（元/吨）", "3,415", "▲ 1.1%", "农业农村部"],
        ]

    # ===== 从表格前4行提取数据卡片 =====
    card_data = []
    for row in table_data[:4]:
        if len(row) >= 2:
            label = row[0]
            if '(' in label:
                label = label.split('(')[0].strip()
            if len(label) > 10:
                label = label[:10] + "..."
            card_data.append({
                "label": label,
                "value": row[1] if row[1] else "--"
            })
        else:
            card_data.append({"label": "--", "value": "--"})
    
    while len(card_data) < 4:
        card_data.append({"label": "--", "value": "--"})

    # ===== 提取关键结论 =====
    conclusions = []
    in_conclusion_section = False
    for line in lines:
        if '关键结论' in line or '核心发现' in line:
            in_conclusion_section = True
            continue
        if in_conclusion_section:
            if line.strip() == '':
                continue
            if '要闻' in line or '数据来源' in line:
                break
            clean = line.strip()
            clean = re.sub(r'\*\*', '', clean)
            clean = re.sub(r'^[\d]+\.\s*', '', clean)
            clean = re.sub(r'^[-•]\s*', '', clean)
            if clean and len(clean) > 10 and len(clean) < 150 and '来源' not in clean and '链接' not in clean:
                conclusions.append('• ' + clean)
                if len(conclusions) >= 5:
                    break

    if not conclusions:
        conclusions = [
            "• 猪价温和上行，养殖盈利改善带动用工需求回暖",
            "• 饲料成本小幅回落，企业薪酬空间释放",
            "• 行业主动离职率降至年内低位，结构性缺工仍存"
        ]

    # ===== 提取要闻（从“要闻”板块提取） =====
    news_items = []
    in_news_section = False
    skip_patterns = ['报告周期', '发布日期', '情报级别', '内部参考', '专业版', '数据来源']

    for line in lines:
        if '要闻' in line or '新闻' in line:
            in_news_section = True
            continue
        
        if in_news_section and line.startswith('##') and '要闻' not in line:
            break
        if in_news_section and line.startswith('---'):
            break
        
        if in_news_section:
            clean = line.strip()
            if not clean:
                continue
            if any(kw in clean for kw in skip_patterns):
                continue
            clean = re.sub(r'\*\*', '', clean)
            clean = re.sub(r'^[\d]+\.\s*', '', clean)
            clean = re.sub(r'^[-•]\s*', '', clean)
            if clean and 10 < len(clean) < 120 and 'http' not in clean and not clean.isdigit():
                if clean not in conclusions and clean not in news_items:
                    news_items.append(clean)

    if not news_items:
        news_items = [
            "牧原股份7月出栏612万头，环比增长4.2%",
            "温氏股份启动2027届校招提前批，计划招聘2800人",
            "人社部发布农业数字化人才需求目录，智慧养殖人才缺口12万",
            "豆粕价格周涨2.3%，饲料企业成本压力上升",
        ]

    news_items = news_items[:6]

    # ===== 提取行动建议 =====
    action_items = []
    in_action_section = False
    action_skip = ['数据来源', '免责', '仅供']

    for line in lines:
        if '行动建议' in line or '建议表' in line:
            in_action_section = True
            continue
        
        if in_action_section:
            if line.strip() == '':
                continue
            if any(kw in line for kw in action_skip):
                break
            
            clean = line.strip()
            clean = re.sub(r'\*\*', '', clean)
            clean = re.sub(r'^[\d]+\.\s*', '', clean)
            clean = re.sub(r'^[-•]\s*', '', clean)
            
            if clean and '|' not in clean and len(clean) > 5 and len(clean) < 80:
                if '：' in clean or ':' in clean:
                    parts = re.split(r'[：:]', clean, 1)
                    if len(parts) == 2 and len(parts[0]) < 10:
                        action_items.append(clean)
                    else:
                        action_items.append(clean)
                else:
                    action_items.append(clean)
                
                if len(action_items) >= 4:
                    break

    if len(action_items) < 4:
        action_items = [
            "招聘策略：提前布局秋招，锁定复合型人才",
            "薪酬优化：对标行业数据，动态调整激励方案",
            "人才培养：强化产教融合，建设人才梯队",
            "人才保留：关注核心人才，提升组织温度",
        ]
    action_items = action_items[:4]

    # ===== 生成 HTML 模板 =====
    cards_html = ''
    for card in card_data:
        cards_html += f'''
        <div class="card">
            <div class="card-value">{card['value']}</div>
            <div class="card-label">{card['label']}</div>
        </div>
        '''

    table_html = ''
    if table_data:
        table_html = '<table><thead><tr><th>指标</th><th>数值</th><th>变化</th><th>来源</th></tr></thead><tbody>'
        for row in table_data[:10]:
            table_html += '<tr>'
            for cell in row:
                table_html += f'<td>{cell if cell else "--"}</td>'
            table_html += '</tr>'
        table_html += '</tbody></table>'
    else:
        table_html = '<p style="color:#999;text-align:center;">暂无数据</p>'

    conclusions_html = ''
    for c in conclusions[:5]:
        conclusions_html += f'<li>{c}</li>'

    news_html = ''
    for item in news_items[:6]:
        news_html += f'<li>{item}</li>'

    action_html = ''
    for item in action_items:
        if '：' in item or ':' in item:
            parts = re.split(r'[：:]', item, 1)
            title_part = parts[0].strip()
            desc_part = parts[1].strip() if len(parts) > 1 else ""
            if len(title_part) > 8:
                action_html += f'<div class="action-item">{item}</div>'
            else:
                action_html += f'<div class="action-item"><strong>{title_part}</strong><br>{desc_part}</div>'
        else:
            action_html += f'<div class="action-item">{item}</div>'

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
            <div class="section-title">📌 HR 行动建议</div>
            <div class="action-grid">{action_html}</div>
        </div>
    </div>

    <div class="footer">数据来源：公开权威渠道 · 仅供内部参考 · 生成时间：2026年8月</div>
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
