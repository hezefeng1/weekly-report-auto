from playwright.sync_api import sync_playwright
import markdown

def markdown_to_image(markdown_text, output_path="report.png"):
    """将 Markdown 渲染为 PNG 图片"""
    # 将 Markdown 转换为 HTML
    md = markdown.Markdown(extensions=['tables', 'fenced_code'])
    html_body = md.convert(markdown_text)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8">
    <style>
        body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
               max-width: 1000px; margin: 30px auto; padding: 30px;
               background: #f5f7fa; color: #1a1a2e; line-height: 1.7; }}
        h1 {{ font-size: 30px; border-bottom: 3px solid #1a3a5c; padding-bottom: 12px; }}
        h2 {{ font-size: 22px; margin-top: 30px; background: #1a3a5c; color: white; padding: 10px 18px; border-radius: 6px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th {{ background: #2c3e50; color: white; padding: 10px 14px; }}
        td {{ padding: 8px 14px; border-bottom: 1px solid #e0e0e0; }}
        tr:nth-child(even) {{ background: #f8f9fc; }}
        blockquote {{ background: #eef2f7; border-left: 6px solid #1a3a5c; padding: 14px 22px; }}
        hr {{ border: 0; border-top: 2px solid #d0d7e3; margin: 30px 0; }}
    </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 1400})
        page.set_content(html_content)
        page.wait_for_timeout(1500)
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    return output_path
