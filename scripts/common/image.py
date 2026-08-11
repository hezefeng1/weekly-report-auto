from playwright.sync_api import sync_playwright

def markdown_to_image(markdown_text, output_path="report.png"):
    """将 Markdown 渲染为 PNG 图片（直接显示原始文本）"""
    
    # 直接展示文本，不解析任何 Markdown 语法
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
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        pre {{
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            white-space: pre-wrap;
            word-wrap: break-word;
            padding: 10px;
            background: #f8f9fc;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.6;
        }}
    </style>
    </head>
    <body>
        <pre>{markdown_text}</pre>
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
