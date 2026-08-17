#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人社补贴政策追踪 - 测试版
分阶段发送，定位飞书 230001 错误根因
"""
import os
import sys
import requests
import json
import time
from common.feishu import get_tenant_access_token

REQUIRED_ENV = ["FEISHU_APP_ID", "FEISHU_APP_SECRET", "RECEIVE_OPEN_ID_POLICY"]
missing = [e for e in REQUIRED_ENV if not os.environ.get(e)]
if missing:
    print(f"❌ 缺少环境变量: {', '.join(missing)}")
    sys.exit(1)

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")

def send_post(content_2d, title="测试消息"):
    """发送富文本消息，返回 (成功, 响应内容)"""
    post_content = {"post": {"zh_cn": {"title": title, "content": content_2d}}}
    payload = {
        "receive_id": RECEIVE_OPEN_ID_POLICY,
        "msg_type": "post",
        "content": json.dumps(post_content, ensure_ascii=False)
    }

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    return resp.status_code == 200, resp.text

def main():
    print("=" * 60)
    print("📋 飞书消息发送测试 - 分阶段定位")
    print("=" * 60)

    # ========== 阶段1：纯文本测试 ==========
    print("\n【阶段1】发送纯文本 'Hello, 测试消息'...")
    ok, resp = send_post([
        [{"tag": "text", "text": "Hello, 测试消息"}]
    ], "阶段1测试")
    print(f"  结果: {'✅ 成功' if ok else '❌ 失败'}")
    print(f"  响应: {resp}")
    if not ok:
        print("  ⚠️ 最基础的测试就失败了，说明问题在 token 或接收人配置")
        return

    # ========== 阶段2：标题 + 1条政策（仅城市和名称，无URL） ==========
    print("\n【阶段2】发送标题 + 1条政策（仅城市 + 名称）...")
    ok, resp = send_post([
        [{"tag": "text", "text": "📋 政策测试"}],
        [{"tag": "text", "text": "─────────────────────"}],
        [{"tag": "text", "text": "📍 成都市  📄 稳岗扩岗专项补贴"}]
    ], "阶段2测试")
    print(f"  结果: {'✅ 成功' if ok else '❌ 失败'}")
    print(f"  响应: {resp}")
    if not ok:
        print("  ⚠️ 问题在标题或分隔线格式")
        return

    # ========== 阶段3：标题 + 1条政策（城市 + 名称 + 纯文本URL） ==========
    print("\n【阶段3】发送城市 + 名称 + 纯文本 URL...")
    ok, resp = send_post([
        [{"tag": "text", "text": "📋 政策测试"}],
        [{"tag": "text", "text": "─────────────────────"}],
        [{"tag": "text", "text": "📍 成都市  📄 稳岗扩岗专项补贴  🔗 https://cdhrss.chengdu.gov.cn/2026wggx"}]
    ], "阶段3测试")
    print(f"  结果: {'✅ 成功' if ok else '❌ 失败'}")
    print(f"  响应: {resp}")
    if not ok:
        print("  ⚠️ 问题在纯文本 URL")
        return

    # ========== 阶段4：阶段3 + 截止日期 ==========
    print("\n【阶段4】阶段3 + 截止日期...")
    ok, resp = send_post([
        [{"tag": "text", "text": "📋 政策测试"}],
        [{"tag": "text", "text": "─────────────────────"}],
        [{"tag": "text", "text": "📍 成都市  ⏰ 2026-07-01至2026-09-30  📄 稳岗扩岗专项补贴  🔗 https://cdhrss.chengdu.gov.cn/2026wggx"}]
    ], "阶段4测试")
    print(f"  结果: {'✅ 成功' if ok else '❌ 失败'}")
    print(f"  响应: {resp}")
    if not ok:
        print("  ⚠️ 问题在截止日期（包含连字符 -）")
        return

    # ========== 阶段5：真实完整数据（含条件和补贴） ==========
    print("\n【阶段5】发送真实完整数据（含条件和补贴）...")
    ok, resp = send_post([
        [{"tag": "text", "text": "📋 政策测试"}],
        [{"tag": "text", "text": "─────────────────────"}],
        [{"tag": "text", "text": "📍 成都市  ⏰ 2026-07-01至2026-09-30  📄 稳岗扩岗专项补贴  📌 企业2026年1-6月社保参保人数不低于2025年同期，且未裁员或裁员率≤5.5%  💰 按2026年6月参保人数×500元/人，最高50万元  🔗 https://cdhrss.chengdu.gov.cn/2026wggx"}]
    ], "阶段5测试")
    print(f"  结果: {'✅ 成功' if ok else '❌ 失败'}")
    print(f"  响应: {resp}")
    if not ok:
        print("  ⚠️ 问题在条件或补贴字段（含 ≤、×、% 等特殊字符）")
        return

    # ========== 结论 ==========
    print("\n" + "=" * 60)
    if ok:
        print("✅ 所有阶段全部成功！说明代码没问题，之前失败是因为具体数据触发了飞书限制。")
        print("   现在可以逐步排查真实数据中的特殊字符。")
    else:
        print("❌ 某个阶段失败了，根据上面的输出定位具体是哪个阶段。")
        print("   重点关注：连字符(-)、百分号(%)、小于等于(≤)、乘号(×)等特殊字符。")
    print("=" * 60)

if __name__ == "__main__":
    main()
