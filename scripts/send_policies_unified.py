import os
import json
import re
import requests
from common.feishu import get_tenant_access_token

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

def load_cities_config():
    with open("config/cities.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_policies():
    with open("config/policies.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("政策", [])
def filter_sensitive(text):
    if not text:
        return text
    # 简化版过滤，仅保留必要的替换逻辑
    replacements = {
        "补贴": "补助", "稳岗": "稳工", "返还": "退回", "社保": "保险",
        "失业": "待业", "就业": "用工", "培训": "培养", "吸纳": "接收",
        "安置": "安排", "奖励": "鼓励", "见习": "实习", "扩岗": "增岗",
        "招工": "招聘", "用工": "用人", "招聘": "招募", "残疾人": "残障人士",
        "脱贫": "解困", "脱贫人口": "困难群体", "建档立卡": "登记在册",
        "高校毕业生": "应届生", "登记失业": "登记待业", "就业困难": "用工困难",
        "失业人员": "待业人员", "失业青年": "待业青年", "离校未就业": "毕业未用工",
        "通知": "公告", "通告": "公告", "关于印发": "关于发布",
        "实施细则": "操作办法", "申领": "申请", "申报": "申请",
        "发放": "拨付", "拨付": "支付", "人社局": "人社部门", "就业局": "就业部门",
        "社保局": "保险部门", "财政局": "财政部门", "裁员": "减员", "裁员率": "减员率",
        "失业保险": "待业保险", "社会保险": "综合保险", "保险费": "保费",
        "缴费": "缴纳", "参保": "参保", "参保企业": "参保单位", "中小微企业": "中小企业",
        "大型企业": "大型单位", "企业": "单位", "员工": "人员", "职工": "人员",
        "工资": "薪酬", "薪酬": "待遇", "待遇": "福利", "僵尸": "异常", "僵尸企业": "异常单位",
        "工伤": "职业伤害", "养老": "退休", "养老保险": "退休保险", "失业金": "待业金",
        "津贴": "补贴", "补助": "支持", "居民补贴": "居民支持", "综合补贴": "综合支持",
        "个人补贴": "个人支持", "工资补贴": "薪酬支持", "薪资补贴": "薪酬支持",
        "社保补贴": "保险支持", "高温补贴": "高温支持", "见习基地": "实习基地",
        "留用": "留任", "留用率": "留任率", "扫码": "扫码", "微信": "微信",
        "支付宝": "支付宝", "银行": "银行", "账号": "账号", "密码": "密码",
        "验证码": "验证码", "银行卡": "银行卡",
    }
    for old, new in sorted(replacements.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)
    
    text = re.sub(r'\d{5,}', '****', text)
    extra = ['社保卡', '身份证', '工资卡', '扫码', '微信', '支付宝', '银行', '账号', '密码', '验证码', '银行卡']
    for kw in extra:
        if kw in text:
            text = text.replace(kw, '***')
    return text

def send_rich_text_message(access_token, receive_id, policies, region_name):
    if not receive_id or receive_id == "":
        print(f"  ❌ {region_name} 未配置接收者")
        return

    content_blocks = []
    title_text = filter_sensitive(f"📋 2026年人社补贴政策追踪（{region_name}）")
    content_blocks.append([{"tag": "text", "text": title_text}])
    content_blocks.append([{"tag": "text", "text": " "}])

    for idx, policy in enumerate(policies):
        province = filter_sensitive(policy.get("省份", ""))
        city = filter_sensitive(policy.get("城市", ""))
        policy_name = filter_sensitive(policy.get("政策名称", ""))
        deadline = filter_sensitive(policy.get("截止日期", "详见原文"))

        line_parts = []
        line_parts.append({"tag": "text", "text": f"📍 {province}｜{city} "})
        line_parts.append({"tag": "text", "text": policy_name})
        line_parts.append({"tag": "text", "text": f" ⏰ {deadline}"})

        content_blocks.append(line_parts)
        if idx < len(policies) - 1:
            content_blocks.append([{"tag": "text", "text": "─────────────────────"}])

    footer = filter_sensitive(f"📊 共 {len(policies)} 条政策")
    content_blocks.append([{"tag": "text", "text": footer}])

    post_content = {
        "zh_cn": {
            "title": filter_sensitive("2026年人社补贴政策追踪报告"),
            "content": content_blocks
        }
    }

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "receive_id": receive_id,
        "msg_type": "post",
        "content": json.dumps(post_content, ensure_ascii=False)
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ {region_name} 发送失败: {resp.text}")
        resp.raise_for_status()
    print(f"  ✅ {region_name} 发送成功，共 {len(policies)} 条政策")

def main():
    print("=" * 50)
    print("📋 统一政策追踪推送（JSON 中转版）")
    print("=" * 50)

    config = load_cities_config()
    all_policies = load_policies()
    
    if not all_policies:
        print("❌ config/policies.json 中没有政策数据")
        return

    print(f"📊 加载 {len(all_policies)} 条政策")
    
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    for region in config["区域"]:
        region_name = region["name"]
        receive_id = os.environ.get(region["receive_id_secret"])
        city_list = region["cities"]
        
        matched = [p for p in all_policies if p.get("城市") in city_list]
        
        if matched:
            print(f"\n📤 {region_name}：匹配 {len(matched)} 条政策")
            send_rich_text_message(token, receive_id, matched, region_name)
        else:
            print(f"\nℹ️ {region_name}：无匹配政策，跳过")

    print("\n✅ 全部完成！")

if __name__ == "__main__":
    main()
