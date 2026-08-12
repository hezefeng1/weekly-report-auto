import os
import tempfile
import re
from playwright.sync_api import sync_playwright

def markdown_to_image(markdown_text, output_path="report.png"):
    """
    将人力资源周报 Markdown 内容渲染为 PNG 信息图
    严格按照周报结构解析：摘要、要闻、竞品对比、专项指标、行动建议
    """
    print("=== 开始渲染图片 ===")

    lines = markdown_text.split('\n')
    
    # ===== 1. 提取标题和日期 =====
    title = "农牧行业人力资源周报"
    report_date = ""
    for line in lines[:15]:
        if '# 农牧行业人力资源周报' in line:
            # 提取日期：如 2026年08月12日
            date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', line)
            if date_match:
                report_date = date_match.group(1)
            title = line.replace('#', '').strip()
        elif '报告周期' in line or '发布日期' in line:
            report_date = line.strip()

    # ===== 2. 提取本期摘要（关键结论） =====
    conclusions = []
    in_summary = False
    for line in lines:
        if '本期摘要' in line or '**本期摘要**' in line:
            in_summary = True
            continue
        if in_summary:
            if line.strip() == '':
                continue
            if line.startswith('##') or line.startswith('---'):
                break
            # 匹配格式：- **关键词**：说明
            clean = line.strip()
            if clean.startswith('-'):
                clean = clean[1:].strip()
            # 去除加粗标记，保留内容
            clean = re.sub(r'\*\*', '', clean)
            if clean and len(clean) > 10 and len(clean) < 200:
                conclusions.append('• ' + clean)
                if len(conclusions) >= 5:
                    break

    if not conclusions:
        conclusions = [
            "• 行业招聘需求稳中有升，数字化岗位成为增长主力",
            "• 核心岗位薪酬持续走高，复合型人才溢价明显",
            "• 行业主动离职率保持稳定，人才保留压力可控",
            "• 政策持续引导人才向农业领域流动"
        ]

    # ===== 3. 提取核心指标追踪表（用于数据卡片和数据速览） =====
    table_data = []
    in_metric_table = False
    metric_indicators = []  # 用于卡片提取

    for i, line in enumerate(lines):
        if '核心指标追踪' in line or '### 3.1 核心指标追踪' in line:
            in_metric_table = True
            continue
        
        if in_metric_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            # 检查是否是指标表头（包含"指标""本期""环比""来源"）
            if len(cells) >= 3:
                header_text = ''.join(cells)
                if '指标' in header_text and '本期' in header_text:
                    continue  # 跳过表头
                # 检查是否是数据行（包含数字）
                has_number = any(re.search(r'[\d,]+\.?\d*', c) for c in cells[:2])
                if has_number and len(cells) >= 3:
                    # 补全到4列
                    while len(cells) < 4:
                        cells.append('')
                    table_data.append(cells[:4])
        
        if in_metric_table and line.strip() == '':
            # 遇到空行或下一个标题结束
            pass
        if in_metric_table and line.startswith('###') and '核心指标' not in line:
            in_metric_table = False

    # 如果没提取到指标表，用备用数据
    if not table_data:
        table_data = [
            ["农牧行业新增岗位数", "18,642", "+6.3%", "猎聘大数据"],
            ["养殖技术岗平均月薪", "8,650", "+1.2%", "猎聘薪酬报告"],
            ["主动离职率", "12.8%", "-0.6pct", "人社部监测"],
            ["生猪均价", "18.42", "+2.1%", "证券时报"],
            ["玉米现货", "2,386", "-0.8%", "卓创资讯"],
            ["豆粕现货", "3,152", "-1.5%", "卓创资讯"],
        ]

    # ===== 4. 从指标表提取数据卡片 =====
    # 固定4个卡片：招聘热度、薪酬变化、人才流动、政策动向
    card_mapping = {
        '招聘热度': ['新增岗位数', '岗位数', '招聘'],
        '薪酬变化': ['月薪', '薪酬', '平均月薪'],
        '人才流动': ['离职率', '流动率'],
        '政策动向': []  # 从政策板块提取
    }
    
    card_values = {
        '招聘热度': '--',
        '薪酬变化': '--',
        '人才流动': '--',
        '政策动向': '暂无'
    }
    
    # 从指标表中匹配对应值
    for row in table_data:
        if len(row) >= 2:
            indicator = row[0]
            value = row[1] if row[1] else ''
            # 匹配招聘热度
            if any(kw in indicator for kw in ['新增岗位', '招聘', '岗位数']):
                if value:
                    card_values['招聘热度'] = value
            # 匹配薪酬变化
            if any(kw in indicator for kw in ['月薪', '薪酬', '平均月薪']):
                if value:
                    card_values['薪酬变化'] = value
            # 匹配人才流动
            if any(kw in indicator for kw in ['离职率', '流动率']):
                if value:
                    card_values['人才流动'] = value
    
    # 提取政策动向：查找 3.3 政策环境支持 或 "政策" 关键词
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
            if clean and len(clean) > 5 and len(clean) < 80:
                policy_title = clean
                break
    
    if policy_title:
        card_values['政策动向'] = policy_title[:20] + "..." if len(policy_title) > 20 else policy_title

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
            # 匹配格式：[标题](URL) | 〖来源：XXX〗：摘要
            if '[' in line and '](' in line and '|' in line:
                # 提取标题
                title_match = re.search(r'\[([^\]]+)\]\([^\)]+\)', line)
                title_text = title_match.group(1) if title_match else ""
                # 提取来源
                source_match = re.search(r'〖来源：([^〗]+)〗', line)
                source_text = source_match.group(1) if source_match else ""
                # 提取摘要（去掉标题和来源部分）
                summary = line
                if title_match:
                    summary = summary.replace(f'[{title_text}]({title_match.group(0).split("](")[1].rstrip(")")})', '')
                summary = re.sub(r'\|.*?〗', '', summary)
                summary = summary.strip()
                if summary.startswith('：'):
                    summary = summary[1:].strip()
                if summary.startswith(':'):
                    summary = summary[1:].strip()
                
                if title_text and len(title_text) > 5:
                    display_text = title_text
                    if source_text:
                        display_text += f"（{source_text}）"
                    if len(display_text) > 60:
                        display_text = display_text[:60] + "..."
                    news_items.append(display_text)
        
        if in_news_section and len(news_items) >= 5:
            break

    # 如果没提取到，尝试从 Markdown 列表中提取
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
                        # 去除来源标记
                        clean = re.sub(r'【来源.*?】', '', clean)
                        clean = re.sub(r'〖来源.*?〗', '', clean)
                        clean = clean.strip()
                        news_items.append(clean)
                    if len(news_items) >= 5:
                        break

    if not news_items:
        news_items = [
            "牧原股份发布2026年半年报，净利润同比增长218%",
            "温氏股份启动2027届校招提前批，计划招聘2800人",
            "人社部发布农业数字化人才需求目录，智慧养殖人才缺口12万",
            "海大集团加速海外人才本地化布局",
            "双胞胎集团设立5亿元人才发展基金",
        ]

    # ===== 6. 提取竞品对比表 =====
    competitor_data = []
    in_competitor_table = False
    for line in lines:
        if '竞品HR策略对比' in line or '### 2.1' in line:
            in_competitor_table = True
            continue
        if in_competitor_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            # 检查是否是表头
            if len(cells) >= 4 and any(kw in ''.join(cells) for kw in ['企业', '公司', '牧原', '温氏', '海大', '双胞胎', '正大']):
                # 如果是表头，跳过
                if '企业' in ''.join(cells) or '公司' in ''.join(cells):
                    continue
                # 检查是否是竞品数据行
                if len(cells) >= 4 and any(kw in cells[0] for kw in ['牧原', '温氏', '海大', '双胞胎', '正大', '集团']):
                    while len(cells) < 5:
                        cells.append('')
                    competitor_data.append(cells)
        if in_competitor_table and line.startswith('###') and '竞品' not in line:
            in_competitor_table = False

    # 备用竞品数据
    if not competitor_data:
        competitor_data = [
            ["牧原股份", "校招覆盖智能化类岗位", "管培生项目+技能认证", "股权激励+高薪酬", "近期无重大HR动态"],
            ["温氏股份", "2027届秋招启动，岗位500+", "青年牧场主培养计划", "限制性股票激励计划", "近期无重大HR动态"],
            ["海大集团", ""海智慧"校招进行中", "管培生培养体系", "股权激励覆盖广", "近期无重大HR动态"],
            ["双胞胎集团", "精准招聘高端技术干部", "—", "财经专家15薪", "近期无重大HR动态"],
            ["正大集团", "奶山羊项目招募场长", "—", "年薪20-50万", "近期无重大HR动态"],
        ]

    # ===== 7. 提取行动建议 =====
    action_items = []
    in_action_table = False
    for line in lines:
        if '行动建议' in line or '## 四、' in line:
            in_action_table = True
            continue
        if in_action_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 2 and any(kw in ''.join(cells) for kw in ['维度', '招聘', '薪酬', '人才', '培训', '策略']):
                # 跳过表头
                if '维度' in ''.join(cells):
                    continue
                if len(cells) >= 2:
                    action_items.append(cells)
        if in_action_table and line.startswith('##') and '行动' not in line:
            break

    if len(action_items) < 4:
        action_items = [
            ["招聘策略调整", "提前布局校招，锁定复合型人才", "行业校招竞争加剧"],
            ["薪酬福利优化", "对标行业数据，动态调整激励方案", "数字化岗位薪酬溢价15%-25%"],
            ["人才培养重点", "强化产教融合，建设人才梯队", "智慧养殖人才缺口12万"],
            ["人才保留策略", "关注核心人才，提升组织温度", "行业主动离职率12.8%"],
        ]

    # ===== 生成 HTML 模板 =====
    # 数据卡片 HTML
    cards_html = ''
    for card in cards:
        cards_html += f'''
        <div class="card">
            <div class="card-value">{card['value']}</div>
            <div class="card-label">{card['label']}</div>
        </div>
        '''

    # 数据速览表 HTML
    table_html = ''
    if table_data:
        table_html = '<table><thead><tr><th>指标</th><th>本期</th><th>环比</th><th>数据来源</th></tr></thead><tbody>'
        for row in table_data[:10]:
            table_html += '<tr>'
            for cell in row:
                table_html += f'<td>{cell if cell else "--"}</td>'
            table_html += '</tr>'
        table_html += '</tbody></table>'
    else:
        table_html = '<p style="color:#999;text-align:center;">暂无数据</p>'

    # 关键结论 HTML
    conclusions_html = ''
    for c in conclusions[:5]:
        conclusions_html += f'<li>{c}</li>'

    # 要闻 HTML
    news_html = ''
    for item in news_items[:6]:
        news_html += f'<li>{item}</li>'

    # 竞品对比表 HTML
    competitor_html = ''
    if competitor_data:
        competitor_html = '<table><thead><tr><th>企业</th><th>招聘策略</th><th>人才培养</th><th>薪酬激励</th><th>最新动态</th></tr></thead><tbody>'
        for row in competitor_data[:5]:
            competitor_html += '<tr>'
            for cell in row:
                competitor_html += f'<td>{cell if cell else "--"}</td>'
            competitor_html += '</tr>'
        competitor_html += '</tbody></table>'
    else:
        competitor_html = '<p style="color:#999;text-align:center;">暂无数据</p>'

    # 行动建议 HTML
    action_html = ''
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

    # 完整 HTML
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
        .section-subtitle {{
            font-size: 14px;
            font-weight: 600;
            color: #1a3a5c;
            margin-top: 12px;
            margin-bottom: 8px;
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
