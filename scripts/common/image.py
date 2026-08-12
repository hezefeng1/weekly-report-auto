from PIL import Image, ImageDraw, ImageFont
import os

def markdown_to_image(markdown_text, output_path="report.png"):
    """使用 PIL 将文本渲染为 PNG 图片，并打印字体加载状态"""
    
    print("=== PIL 字体加载调试 ===")
    
font_paths = [
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
    
    font = None
    loaded_path = None
    
    for path in font_paths:
        exists = os.path.exists(path)
        print(f"  检查: {path} -> {'✅ 存在' if exists else '❌ 不存在'}")
        if exists:
            try:
                font = ImageFont.truetype(path, 16)
                loaded_path = path
                print(f"  ✅ 成功加载字体: {path}")
                break
            except Exception as e:
                print(f"  ❌ 加载失败: {path} - {e}")
    
    if font is None:
        print("  ⚠️ 没有找到中文字体，使用默认字体（中文会显示为方块）")
        font = ImageFont.load_default()
    else:
        print(f"  🎯 最终使用的字体: {loaded_path}")
    
    print("=== 调试结束 ===")
    
    # ========== 以下是绘制代码 ==========
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
