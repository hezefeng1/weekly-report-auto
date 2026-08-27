import os
import json
from datetime import datetime
from common.feishu import get_tenant_access_token, upload_image, send_image_message
from common.image import markdown_to_image

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_AGRI = os.environ.get("RECEIVE_OPEN_ID_AGRI")


def load_weekly_data():
    with open("data/weekly_agri.json", "r", encoding="utf-8") as f:
        return json.load(f)


def build_markdown_from_json(data):
    today = data.get("日期", datetime.now().strftime("%Y年%m月%d日"))
    md_lines = []

    # 标题
    md_lines.append(f"# 农牧行业周报（{today}）")
    md_lines.append("")

    # 摘要
    md_lines.append(f"**{data.get('摘要', '')}**")
    md_lines.append("")

    # 本周卡片数据
    md_lines.append("## 本周卡片数据")
    core = data.get("核心数据", {})
    for key, value in core.items():
        md_lines.append(f"- **{key}**：{value.get('数值', '—')} ｜ {value.get('变化', '')}")
    md_lines.append("")

    # 核心结论
    md_lines.append("## 本周关键结论")
    for c in data.get("核心结论", []):
        md_lines.append(f"- {c}")
    md_lines.append("")

    # 核心数据速览
    md_lines.append("## 核心数据速览")
    md_lines.append("| 关键指标 | 本期数据 | 趋势 |")
    md_lines.append("|---------|---------|------|")
    for key, value in data.get("核心数据速览", {}).items():
        md_lines.append(f"| {key} | {value.get('数值', '—')} | {value.get('趋势', '→')} |")
    md_lines.append("")

    # 行业要闻
    md_lines.append("## 行业要闻")
    for item in data.get("行业要闻", []):
        title = item.get("标题", "")
        link = item.get("链接", "")
        source = item.get("来源", "")
        summary = item.get("摘要", "")
        if link:
            md_lines.append(f"- [{title}]({link}) ｜ 【来源：{source}】{summary}")
        else:
            md_lines.append(f"- {title} ｜ 【来源：{source}】{summary}")
    md_lines.append("")

    # 竞品动态
    md_lines.append("## 竞品动态")
    md_lines.append("| 企业 | 财务表现 | 战略动态 | 经营动作 | 最新动态 |")
    md_lines.append("|------|---------|---------|---------|---------|")
    for item in data.get("竞品动态", []):
        md_lines.append(
            f"| {item.get('企业', '—')} | "
            f"{item.get('财务表现', '—')} | "
            f"{item.get('战略动态', '—')} | "
            f"{item.get('经营动作', '—')} | "
            f"{item.get('最新动态', '—')} |"
        )
    md_lines.append("")

    # 行动建议
    md_lines.append("## 行动建议")
    md_lines.append("| 维度 | 具体建议 | 数据/案例支撑 |")
    md_lines.append("|------|---------|--------------|")
    for item in data.get("行动建议", []):
        md_lines.append(
            f"| {item.get('维度', '—')} | "
            f"{item.get('具体建议', '—')} | "
            f"{item.get('数据/案例支撑', '—')} |"
        )

    return "\n".join(md_lines)


def main():
    print("=" * 50)
    print("🚀 农牧行业周报自动化（JSON 中转版）")
    print("=" * 50)

    print("\n1. 加载周报数据...")
    data = load_weekly_data()
    print(f"   ✅ 加载成功，周报日期: {data.get('日期', '未知')}")
    print(f"   📊 核心数据: {len(data.get('核心数据', {}))} 条")
    print(f"   📰 行业要闻: {len(data.get('行业要闻', []))} 条")
    print(f"   🏢 竞品动态: {len(data.get('竞品动态', []))} 条")
    print(f"   💡 行动建议: {len(data.get('行动建议', []))} 条")

    print("\n2. 渲染 Markdown...")
    md_content = build_markdown_from_json(data)
    print(f"   ✅ 渲染完成，共 {len(md_content)} 字符")

    print("\n3. 渲染为图片...")
    image_path = markdown_to_image(md_content, "weekly_agri_report.png")
    print(f"   ✅ 图片已生成: {image_path}")

    print("\n4. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    print("\n5. 上传图片...")
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_key = upload_image(token, image_bytes)
    print(f"   ✅ 图片上传成功")

    print("\n6. 发送飞书消息...")
    receive_ids = RECEIVE_OPEN_ID_AGRI.split('|')
    for open_id in receive_ids:
        open_id = open_id.strip()
        if open_id:
            try:
                send_image_message(token, open_id, image_key)
                print(f"   ✅ 已发送给 {open_id}")
            except Exception as e:
                print(f"   ❌ 发送给 {open_id} 失败: {e}")

    print("\n✅ 农牧行业周报发送完成！")


if __name__ == "__main__":
    main()
