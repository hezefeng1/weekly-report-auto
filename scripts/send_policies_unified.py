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

# ==================== 屏蔽词规则（完整版） ====================
SENSITIVE_RULES_RAW = """
发放,http
贴 补
卜帖
人力社,高温补贴
国家,高温补贴
最新卜帖
^(通 知\.)
(zip|exe|rar|
pdf|doc|docx)$
人力社
^(\d|\_|\.|\-)
*(zip|exe|rar)$
一业一查
部门联合双随机抽查工作计划
人力社,津贴
人力社,补助
人力社,补贴
人力社,居民补贴
人力社,综合补贴
人力社,个人补贴
人力社,补贴
居 民补 贴
综 合补 贴
京东商城,国家补贴
京东商城,平台补贴
工资补贴,扫描二维码
社保局工资补贴
人力社,工资补贴
薪资补贴,微信扫码
人力社,薪资补贴
人力社,社保补贴
人社部个人劳动补贴
国家财政部补贴
社保补贴,微信扫码
人社局,补贴
国家,补贴通知
补贴,申领
裁员名单

补贴,申领
就业困难,人员
失业,保险
脱贫,人口
残疾人,安置
一次性,扩岗,补助
岗前,培训,补贴
就业,见习,补贴
稳岗,返还,补贴
培训,补贴
吸纳,就业
招用,高校,毕业生
留用,率
扩岗,补助
工伤,保险
养老,保险
失业,金
低保,家庭
僵尸,企业
见习,基地
岗位,补贴
引才,奖励
返乡,就业
跨省,就业
""".strip().splitlines()

def load_sensitive_rules(lines):
    rules = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        keywords = [kw.strip() for kw in line.split(',') if kw.strip()]
        if keywords:
            rules.append(keywords)
    return rules

SENSITIVE_RULES = load_sensitive_rules(SENSITIVE_RULES_RAW)

def filter_sensitive(text):
    if not text:
        return text

    text_lower = text.lower()
    for keywords in SENSITIVE_RULES:
        if all(kw.lower() in text_lower for kw in keywords):
            for kw in keywords:
                text = text.replace(kw, "***")
                kw_no_space = kw.replace(" ", "")
                if kw_no_space != kw:
                    text = text.replace(kw_no_space, "***")

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

    md_lines = []
    md_lines.append(f"📋 2026年人社补贴政策追踪（{region_name}）\n")

    md_lines.append("| 省份 | 城市 | 政策名称 | 核心申请条件 | 补贴标准/金额 | 截止日期 |")
    md_lines.append("|------|------|----------|--------------|----------------|----------|")

    for policy in policies:
        province = filter_sensitive(policy.get("省份", ""))
        city = filter_sensitive(policy.get("城市", ""))
        title = filter_sensitive(policy.get("政策标题", ""))
        link = policy.get("政策链接", "")
        # 🔥 拼接 Markdown 链接
        if title and link:
            policy_name = f"[{title}]({link})"
        else:
            policy_name = title
        condition = filter_sensitive(policy.get("核心申请条件", ""))
        subsidy = filter_sensitive(policy.get("补贴标准", ""))
        deadline = filter_sensitive(policy.get("截止日期", "详见原文"))

        md_lines.append(f"| {province} | {city} | {policy_name} | {condition} | {subsidy} | {deadline} |")

    footer = filter_sensitive(f"\n📊 共 {len(policies)} 条政策")
    md_lines.append(footer)

    md_content = "\n".join(md_lines)

    send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "receive_id": receive_id,
        "msg_type": "post",
        "content": json.dumps({
            "zh_cn": {
                "title": "2026年人社补贴政策追踪报告",
                "content": [
                    [{"tag": "md", "text": md_content}]
                ]
            }
        })
    }

    resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
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
