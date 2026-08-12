def markdown_to_image(markdown_text, output_path="report.png"):
    """
    使用 PIL 直接将文本渲染为 PNG 图片
    """
    print("=== 开始检查中文字体路径 ===")
    
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
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
    
    # ===== 后面是绘制代码 =====
