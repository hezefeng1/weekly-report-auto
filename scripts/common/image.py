from PIL import Image, ImageDraw, ImageFont
import os

def markdown_to_image(markdown_text, output_path="report.png"):
    """
    使用 PIL 直接将文本渲染为 PNG 图片
    完全绕过浏览器，不依赖编码解析
    """
    # 字体路径（GitHub Actions Ubuntu 环境下的中文字体）
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    
    font = None
    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, 16)
                break
            except:
                continue
    
    if font is None:
        font = ImageFont.load_default()
    
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
