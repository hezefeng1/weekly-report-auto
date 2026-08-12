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

    # 提取数据速览表格
    table_data = []
    in_table = False
    table_headers = []
    for i, line in enumerate(lines):
        if '|' in line and '---' not in line and not in_table:
            # 表头行
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                table_headers = cells
                in_table = True
                continue
        if in_table and '|' in line and '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                table_data.append(cells)
        if in_table and line.strip() == '':
            in_table = False

    # 提取关键结论（数据卡片用）
    key_numbers = []
    for line in lines:
        if '元/kg' in line or '元/吨' in line or '岗位' in line:
            nums = re.findall(r'[\d,]+\.?\d*', line)
            if nums and len(nums) > 0:
                key_numbers.append(nums[0])
    
    # 取前4个作为数据卡片
    card_data = []
    card_labels = ["生猪均价", "玉米现货", "豆粕现货", "新增岗位"]
    if len(key_numbers) >= 4:
        for i in range(4):
            card_data.append({"label": card_labels[i], "value": key_numbers[i] if i < len(key_numbers) else "--"})
    else:
        card_data = [
            {"label": "生猪均价", "value": "--"},
            {"label": "玉米现货", "value": "--"},
            {"label": "豆粕现货", "value": "--"},
            {"label": "新增岗位", "value": "--"},
        ]

    # 提取关键结论段落
    conclusions = []
    for i, line in enumerate(lines):
        if '关键结论' in line or '核心发现' in line:
            for j in range(i+1, min(i+20, len(lines))):
                if lines[j].strip() and not lines[j].startswith('#'):
                    conclusions.append(lines[j].strip())
                    if len(conclusions) >= 5:
                        break

    # 提取要闻列表
    news_items = []
    news_pattern = r'\*\*(\d+\.\s*.*?)\*\*'
    for line in lines:
        if '##' in line and ('要闻' in line or '新闻' in line):
            continue
        if line.strip().startswith('**') and any(c.isdigit() for c in line[:10]):
            clean = line.replace('**', '').strip()
            if clean and len(clean) > 10:
                news_items.append(clean)

    # 如果没提取到，用一些示例
    if not news_items:
        for line in lines:
            if '来源' in line or '链接' in line:
                continue
            if line.strip().startswith('-') or line.strip().startswith('•'):
                clean = line.replace('-', '').replace('•', '').strip()
                if clean and len(clean) > 15:
                    news_items.append(clean)

    # ===== 2. 生成 HTML 模板 =====
    # 数据卡片 HTML
    cards_html = ''
    for card in card_data:
        cards_html += f'''
        <div class="card">
            <div class="card-value">{card['value']}</div>
            <div class="card-label">{card['label']}</div>
        </div>
        '''

    # 表格 HTML
    table_html = ''
    if table_headers and table_data:
        table_html += '<table><thead><tr>'
        for h in table_headers:
            table_html += f'<th>{h}</th>'
        table_html += '</tr></thead><tbody>'
        for row in table_data[:10]:
            table_html += '<tr>'
            for cell in row:
                table_html += f'<td>{cell}</td>'
            table_html += '</tr>'
        table_html += '</tbody></table>'
    else:
        table_html = '<p style="color:#999;text-align:center;">暂无表格数据</p>'

    # 关键结论 HTML
    conclusions_html = ''
    for c in conclusions[:5]:
        conclusions_html += f'<li>{c}</li>'

    # 要闻 HTML
    news_html = ''
    for item in news_items[:8]:
        news_html += f'<li>{item}</li>'

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
        /* ===== 顶部标题栏 ===== */
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
        /* ===== 数据卡片区 ===== */
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
        /* ===== 内容主体 ===== */
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
        /* ===== 表格 ===== */
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
        /* ===== 列表 ===== */
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
        /* ===== 行动建议 ===== */
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
        /* ===== 页脚 ===== */
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
    <!-- 顶部标题栏 -->
    <div class="header">
        <div class="header-title">{title}</div>
        <div class="header-sub">
            <span>{report_date if report_date else "2026年8月"}</span>
            <span>内部参考 · 限时阅读</span>
        </div>
    </div>

    <!-- 数据卡片 -->
    <div class="cards">{cards_html}</div>

    <!-- 主体内容 -->
    <div class="body-content">
        <!-- 表格 -->
        <div class="section">
            <div class="section-title">📊 数据速览</div>
            {table_html}
        </div>

        <!-- 关键结论 -->
        <div class="section">
            <div class="section-title">🎯 关键结论</div>
            <ul class="conclusion-list">{conclusions_html}</ul>
        </div>

        <!-- 要闻 -->
        <div class="section">
            <div class="section-title">📰 要闻精选</div>
            <ul class="news-list">{news_html}</ul>
        </div>

        <!-- 行动建议 -->
        <div class="section">
            <div class="section-title">📌 HR 行动建议</div>
            <div class="action-grid">
                <div class="action-item"><strong>招聘策略</strong><br>提前布局秋招，锁定复合型人才</div>
                <div class="action-item"><strong>薪酬优化</strong><br>对标行业数据，动态调整激励方案</div>
                <div class="action-item"><strong>人才培养</strong><br>强化产教融合，建设人才梯队</div>
                <div class="action-item"><strong>人才保留</strong><br>关注核心人才，提升组织温度</div>
            </div>
        </div>
    </div>

    <!-- 页脚 -->
    <div class="footer">数据来源：公开权威渠道 · 仅供内部参考 · 生成时间：2026年8月</div>
</div>
</body>
</html>'''

    # ===== 3. 保存 HTML 为临时文件 =====
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.html',
        delete=False,
        encoding='utf-8'
    ) as f:
        f.write(html_content)
        temp_path = f.name

    print(f"  HTML 临时文件: {temp_path}")

    # ===== 4. 用 Playwright 加载并截图 =====
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
