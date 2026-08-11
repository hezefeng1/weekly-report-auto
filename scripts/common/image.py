from playwright.sync_api import sync_playwright
import html

def markdown_to_image(markdown_text, output_path="report.png"):
    """将 Markdown 渲染为 PNG 图片（强制 UTF-8 编码）"""
    
    # 对特殊字符进行 HTML 转义，防止被浏览器误解
    escaped_text = html.escape(markdown_text)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <title>周报</title>
        <style>
            body {{
                font-family: "Microsoft YaHei", "PingFang SC", "SimSun", sans-serif;
                max-width: 1000px;
                margin: 30px auto;
                padding: 30px;
                background: #f5f7fa;
                color: #1a1a2e;
                line-height: 1.6;
            }}
            pre {{
                font-family: "Microsoft YaHei", "PingFang SC", "SimSun", sans-serif;
                white-space: pre-wrap;
                word-wrap: break-word;
                background: #f8f9fc;
                padding: 20px;
                border-radius: 8px;
                font-size: 14px;
                line-height: 1.6;
                border: 1px solid #e0e0e0;
            }}
        </style>
    </head>
    <body>
        <pre>{escaped_text}</pre>
    </body>
    </html>
    """
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 增加默认编码设置
        context = browser.new_context(viewport={"width": 1100, "height": 1600})
        page = context.new_page()
        # 使用 set_content 时明确指定编码
        page.set_content(html_content, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    return output_path
