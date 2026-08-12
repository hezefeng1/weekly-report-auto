from PIL import Image, ImageDraw, ImageFont
import os

def markdown_to_image(markdown_text, output_path="report.png"):
    """
    使用 PIL 将文本渲染为 PNG 图片
    字体加载顺序：优先中文字体，最后才是英文
    """
    print("=== PIL 字体加载调试 ===")

    # 中文字体优先
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    font = None
    for path in font_paths:
        if os.path.exists(path):
            print(f"  ✅ 找到字体: {path}")
            try:
                font = ImageFont.truetype(path, 16)
                print(f"  🎯 成功加载: {path}")
                break
            except Exception as e:
                print(f"  ❌ 加载失败: {path} - {e}")
                continue
        else:
            print(f"  ❌ 字体不存在: {path}")

    if font is None:
        print("  ⚠️ 没有找到任何中文字体，使用默认字体")
        font = ImageFont.load_default()
    else:
        print(f"  ✅ 最终使用的字体: {font}")

    print("=== 字体检查结束 ===")

    # ===== 绘制图片 =====
    lines = markdown_text.split('\n')
    width = 1000
    line_height = 30
    padding = 30
    height = len(lines) * line_height + padding * 2 + 100

    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    y = padding
    for line in lines:
        if len(line) > 80:
            for i in range(0, len(line), 80):
                chunk = line[i:i+80]
                draw.text((padding, y), chunk, fill='black', font=font)
                y += line_height
        else:
            draw.text((padding, y), line, fill='black', font=font)
            y += line_height

        if y > height - padding:
            new_height = height + 500
            new_img = Image.new('RGB', (width, new_height), color='white')
            new_img.paste(img, (0, 0))
            img = new_img
            draw = ImageDraw.Draw(img)
            height = new_height

    img.save(output_path)
    return output_path
