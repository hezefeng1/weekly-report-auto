from playwright.sync_api import sync_playwright

def markdown_to_image(markdown_text, output_path="report.png"):
    """将 Markdown 渲染为 PNG 图片（保留原始格式）"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8">
    <style>
        body {{
            font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif;
            max-width: 1000px;
            margin: 30px auto;
            padding: 30px;
            background: #f5f7fa;
            color: #1a1a2e;
            line-height: 1.7;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        h1 {{ font-size: 30px; border-bottom: 3px solid #1a3a5c; padding-bottom: 12px; color: #1a3a5c; }}
        h2 {{ font-size: 22px; margin-top: 30px; background: #1a3a5c; color: white; padding: 10px 18px; border-radius: 6px; }}
        h3 {{ font-size: 18px; margin-top: 24px; color: #1a3a5c; border-left: 4px solid #1a3a5c; padding-left: 12px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 14px;
        }}
        th {{
            background: #2c3e50;
            color: white;
            padding: 10px 14px;
            text-align: left;
        }}
        td {{
            padding: 8px 14px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:nth-child(even) {{ background: #f8f9fc; }}
        blockquote {{
            background: #eef2f7;
            border-left: 6px solid #1a3a5c;
            padding: 14px 22px;
            margin: 18px 0;
            border-radius: 0 8px 8px 0;
        }}
        hr {{ border: 0; border-top: 2px solid #d0d7e3; margin: 30px 0; }}
        a {{ color: #1a5c9e; text-decoration: none; }}
        ul, ol {{ padding-left: 24px; }}
        code {{ background: #eef2f7; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
        pre {{
            background: #1a1a2e;
            color: #f0f0f0;
            padding: 16px 20px;
            border-radius: 6px;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        .markdown-content {{
            white-space: pre-wrap;
            font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif;
        }}
    </style>
    </head>
    <body>
        <div class="markdown-content">
            {markdown_text}
        </div>
    </body>
    </html>
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1100, "height": 1600})
        page.set_content(html_content)
        page.wait_for_timeout(2000)
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    return output_path
