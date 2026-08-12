from PIL import Image, ImageDraw, ImageFont
import os

def markdown_to_image(markdown_text, output_path="report.png"):
    """使用 PIL 将文本渲染为 PNG 图片，自动适应内容高度"""

    print("=== 开始渲染图片（自适应高度）===")

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
                font = ImageFont.truetype(path, 16)
                print(f"  ✅ 加载字体: {path}")
                break
            except:
                continue

    if font is None:
        print("  ⚠️ 使用默认字体")
        font = ImageFont.load_default()

    # 获取所有行
    lines = markdown_text.split('\n')

    # 先用一个很大的画布画完所有文字
    width = 1000
    padding = 30
    line_height = 28
    initial_height = 6000  # 足够大，保证装下所有内容

    img = Image.new('RGB', (width, initial_height), color='white')
    draw = ImageDraw.Draw(img)

    y = padding
    max_y = y

    for line in lines:
        # 处理空行
        if line.strip() == '':
            y += line_height
            continue

        # 换行处理（单行超过80字符拆分）
        if len(line) > 80:
            for i in range(0, len(line), 80):
                chunk = line[i:i+80]
                draw.text((padding, y), chunk, fill='black', font=font)
                y += line_height
                max_y = y
        else:
            draw.text((padding, y), line, fill='black', font=font)
            y += line_height
            max_y = y

        # 安全保护：如果超出画布，扩展高度
        if y > initial_height - 100:
            new_img = Image.new('RGB', (width, initial_height + 1000), color='white')
            new_img.paste(img, (0, 0))
            img = new_img
            draw = ImageDraw.Draw(img)
            initial_height += 1000

    # 裁剪到实际内容区域（留一点边距）
    crop_height = max_y + padding
    if crop_height > img.height:
        crop_height = img.height
    img_cropped = img.crop((0, 0, width, crop_height))

    img_cropped.save(output_path)
    print(f"  ✅ 图片生成完成，实际高度: {crop_height}px")
    return output_path
