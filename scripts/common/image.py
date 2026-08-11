from playwright.sync_api import sync_playwright
import re

def markdown_to_image(markdown_text, output_path="report.png"):
    """将 Markdown 渲染为 PNG 图片（自动修复表格格式）"""
    
    # 修复表格：检测并修复列数不对齐的表格
    lines = markdown_text.split('\n')
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 如果当前行是表格分隔行（包含 |---）
        if '|---' in line or '| ---' in line:
            # 统计表头的列数（上一行）
            if i > 0 and '|' in lines[i-1]:
                header_cells = lines[i-1].count('|') - 1
                # 重新生成正确的分隔行
                fixed_line = '|' + '|'.join(['---'] * header_cells) + '|'
                fixed_lines.append(fixed_line)
                i += 1
                continue
        fixed_lines.append(line)
        i += 1
    
    cleaned_text = '\n'.join(fixed_lines)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8">
    <style>
        body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
               max-width: 1000px; margin: 30px auto; padding: 30px;
               background: #f5f7fa; color: #1a1a2e; line-height: 1.7;
               white-space: pre-wrap; word-wrap: break-word; }}
        h1 {{ font-size: 28px; border-bottom: 3px solid #1a3a5c; padding-bottom: 10px; }}
        h2 {{ font-size: 22px; margin-top: 25px; background: #1a3a5c; color: white; padding: 8px 16px; border-radius: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }}
        th {{ background: #2c3e50; color: white; padding: 8px 12px; text-align: left; }}
        td {{ padding: 6px 12px; border: 1px solid #ddd; }}
        tr:nth-child(even) {{ background: #f8f9fc; }}
        blockquote {{ background: #eef2f7; border-left: 5px solid #1a3a5c; padding: 10px 18px; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; white-space: pre-wrap; }}
    </style>
    </head>
    <body>
        {cleaned_text}
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
