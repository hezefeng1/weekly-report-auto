from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

def markdown_to_image(markdown_text, output_path="report.png"):
    """使用 PIL 将文本渲染为 PNG 图片，自动适应内容"""

    print("=== 开始渲染图片（自适应宽度）===")

    # 字体加载（优先中文字体）
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    font = None
    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, 14)  # 字体从16改为14
                print(f"  ✅ 加载字体: {path}")
                break
            except:
                continue

    if font is None:
        print("  ⚠️ 使用默认字体")
        font = ImageFont.load_default()

    lines = markdown_text.split('\n')

    # 增加宽度到 1400px，避免右侧截断
    width = 1400
    padding = 30
    line_height = 24  # 字体变小，行高相应减小
    max_line_width = width - padding * 2

    initial_height = 6000
    img = Image.new('RGB', (width, initial_height), color='white')
    draw = ImageDraw.Draw(img)

    y = padding
    max_y = y

    for line in lines:
        if line.strip() == '':
            y += line_height
            continue

        # 判断是否需要换行：估算文本宽度
        # 使用 textbbox 或 textlength 估算
        try:
            line_width = draw.textlength(line, font=font)
        except:
            line_width = len(line) * 14  # 粗略估算

        if line_width > max_line_width:
            # 需要换行：按字符数拆分
            # 每行最多字符数（粗略估算）
            max_chars = int(max_line_width / 14)
            chunks = textwrap.wrap(line, width=max_chars)
            for chunk in chunks:
                draw.text((padding, y), chunk, fill='black', font=font)
                y += line_height
                max_y = y
                if y > initial_height - 100:
                    new_img = Image.new('RGB', (width, initial_height + 1000), color='white')
                    new_img.paste(img, (0, 0))
                    img = new_img
                    draw = ImageDraw.Draw(img)
                    initial_height += 1000
        else:
            draw.text((padding, y), line, fill='black', font=font)
            y += line_height
            max_y = y

        if y > initial_height - 100:
            new_img = Image.new('RGB', (width, initial_height + 1000), color='white')
            new_img.paste(img, (0, 0))
            img = new_img
            draw = ImageDraw.Draw(img)
            initial_height += 1000

    crop_height = max_y + padding
    if crop_height > img.height:
        crop_height = img.height
    img_cropped = img.crop((0, 0, width, crop_height))

    img_cropped.save(output_path)
    print(f"  ✅ 图片生成完成，尺寸: {width} x {crop_height}px")
    return output_path
