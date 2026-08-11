import os
import tempfile
from playwright.sync_api import sync_playwright

def markdown_to_image(markdown_text, output_path="report.png"):
    """
    将 Markdown 文本渲染为 PNG 图片
    通过保存 HTML 文件再加载，确保 UTF-8 编码正确识别
    """
    # 把 Markdown 转成 HTML 格式
    lines = markdown_text.split('\n')
    html_lines = []
    for line in lines:
        if line.startswith('# '):
            html_lines.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('### '):
            html_lines.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('- '):
            html_lines.append(f'<li>{line[2:]}</li>')
        elif line.strip() == '':
            html_lines.append('<br>')
        else:
            html_lines.append(f'<p>{line}</p>')
    
    html_body = '\n'.join(html_lines)
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>农牧周报</title>
    <style>
        body {{
            font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
            max-width: 1000px;
            margin: 30px auto;
            padding: 30px;
            background: #ffffff;
            color: #1a1a2e;
            line-height: 1.8;
        }}
        h1 {{ font-size: 28px; border-bottom: 3px solid #1a3a5c; padding-bottom: 10px; color: #1a3a5c; }}
        h2 {{ font-size: 22px; margin-top: 25px; background: #1a3a5c; color: #ffffff; padding: 8px 16px; border-radius: 4px; }}
        h3 {{ font-size: 18px; margin-top: 20px; color: #1a3a5c; border-left: 4px solid #1a3a5c; padding-left: 12px; }}
        p {{ margin: 6px 0; word-wrap: break-word; }}
        li {{ margin-left: 20px; }}
        .container {{ background: #f8f9fc; padding: 20px; border-radius: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }}
        th {{ background: #2c3e50; color: white; padding: 8px 12px; text-align: left; }}
        td {{ padding: 6px 12px; border: 1px solid #ddd; }}
        tr:nth-child(even) {{ background: #f8f9fc; }}
        blockquote {{ background: #eef2f7; border-left: 5px solid #1a3a5c; padding: 10px 18px; }}
    </style>
</head>
<body>
    <div class="container">
        {html_body}
    </div>
</body>
</html>"""
    
    # 保存 HTML 到临时文件（UTF-8 编码）
    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.html', 
        delete=False, 
        encoding='utf-8'
    ) as f:
        f.write(html_content)
        temp_html_path = f.name
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1100, "height": 1600})
            # 用文件 URL 加载，让浏览器通过文件头识别编码
            page.goto(f'file://{temp_html_path}')
            page.wait_for_timeout(2000)
            page.screenshot(path=output_path, full_page=True)
            browser.close()
    finally:
        # 清理临时文件
        if os.path.exists(temp_html_path):
            os.unlink(temp_html_path)
    
    return output_path
