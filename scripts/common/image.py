from playwright.sync_api import sync_playwright
import markdown

def markdown_to_image(markdown_text, output_path="report.png"):
    """将 Markdown 渲染为 PNG 图片（完整版）"""
    
    # 先把 Markdown 转成 HTML
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'nl2br'])
    html_body = md.convert(markdown_text)
    
    # 完整的 HTML 模板（带中文支持）
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>周报</title>
        <style>
            body {{
                font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
                max-width: 1000px;
                margin: 30px auto;
                padding: 30px;
                background: #f5f7fa;
                color: #1a1a2e;
                line-height: 1.7;
            }}
            h1 {{
                font-size: 30px;
                border-bottom: 3px solid #1a3a5c;
                padding-bottom: 12px;
                color: #1a3a5c;
            }}
            h2 {{
                font-size: 24px;
                margin-top: 30px;
                background: #1a3a5c;
                color: white;
                padding: 10px 18px;
                border-radius: 6px;
            }}
            h3 {{
                font-size: 20px;
                margin-top: 24px;
                color: #1a3a5c;
                border-left: 4px solid #1a3a5c;
                padding-left: 12px;
            }}
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
                border: 1px solid #ddd;
            }}
            tr:nth-child(even) {{
                background: #f8f9fc;
            }}
            blockquote {{
                background: #eef2f7;
                border-left: 6px solid #1a3a5c;
                padding: 14px 22px;
                margin: 18px 0;
                border-radius: 0 8px 8px 0;
            }}
            hr {{
                border: 0;
                border-top: 2px solid #d0d7e3;
                margin: 30px 0;
            }}
            ul, ol {{
                padding-left: 24px;
            }}
            code {{
                background: #eef2f7;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 13px;
            }}
            pre {{
                background: #1a1a2e;
                color: #f0f0f0;
                padding: 16px 20px;
                border-radius: 6px;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
            p {{
                margin: 10px 0;
            }}
            a {{
                color: #1a5c9e;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .footer {{
                margin-top: 40px;
                font-size: 12px;
                color: #999;
                border-top: 1px solid #ddd;
                padding-top: 15px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html_body}
        <div class="footer">报告生成时间：2026年8月</div>
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
