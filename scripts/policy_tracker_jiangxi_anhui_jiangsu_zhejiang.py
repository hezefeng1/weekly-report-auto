import os
import requests
import json
import re
from datetime import datetime
from common.feishu import get_tenant_access_token

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID_POLICY = os.environ.get("RECEIVE_OPEN_ID_POLICY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# ==================== 城市官网映射 ====================
CITY_WEBSITE = {
    # 江西省
    "赣州市": "http://rsj.ganzhou.gov.cn",
    "吉安市": "http://rsj.jian.gov.cn",
    "九江市": "http://rsj.jiujiang.gov.cn",
    "宜春市": "http://rsj.yichun.gov.cn",
    "鹰潭市": "http://rsj.yingtan.gov.cn",
    "抚州市": "http://rsj.fuzhou.gov.cn",
    "上饶市": "http://rsj.shangrao.gov.cn",
    # 安徽省
    "阜阳市": "http://rsj.fuyang.gov.cn",
    "合肥市": "http://rsj.hefei.gov.cn",
    "宿州市": "http://rsj.suzhou.gov.cn",
    "铜陵市": "http://rsj.tongling.gov.cn",
    "宣城市": "http://rsj.xuancheng.gov.cn",
    "蚌埠市": "http://rsj.bengbu.gov.cn",
    "亳州市": "http://rsj.bozhou.gov.cn",
    "滁州市": "http://rsj.chuzhou.gov.cn",
    "淮北市": "http://rsj.huaibei.gov.cn",
    "安庆市": "http://rsj.anqing.gov.cn",
    # 江苏省
    "淮安市": "http://rsj.huaian.gov.cn",
    "南通市": "http://rsj.nantong.gov.cn",
    "泰州市": "http://rsj.taizhou.gov.cn",
    "徐州市": "http://rsj.xuzhou.gov.cn",
    "盐城市": "http://rsj.yancheng.gov.cn",
    "常州市": "http://rsj.changzhou.gov.cn",
    "连云港市": "http://rsj.lyg.gov.cn",
    "南京市": "http://rsj.nanjing.gov.cn",
    "宿迁市": "http://rsj.suqian.gov.cn",
    "镇江市": "http://rsj.zhenjiang.gov.cn",
    # 浙江省
    "杭州市": "http://rsj.hangzhou.gov.cn",
    "湖州市": "http://rsj.huzhou.gov.cn",
    "宁波市": "http://rsj.ningbo.gov.cn",
    "衢州市": "http://rsj.quzhou.gov.cn",
    "温州市": "http://rsj.wenzhou.gov.cn",
}

def get_website(city):
    if city in CITY_WEBSITE:
        return CITY_WEBSITE[city]
    city_simple = city.replace("市", "")
    for key in CITY_WEBSITE:
        if key.replace("市", "") == city_simple:
            return CITY_WEBSITE[key]
    return f"https://www.baidu.com/s?wd={city} 人社局"

# ==================== 屏蔽词规则（全量通用版） ====================
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

# ===== 通用组合规则（覆盖所有区域） =====
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

    # ---------- 第一步：应用你的规则（多词同时触发） ----------
    text_lower = text.lower()
    for keywords in SENSITIVE_RULES:
        if all(kw.lower() in text_lower for kw in keywords):
            for kw in keywords:
                text = text.replace(kw, "***")
                kw_no_space = kw.replace(" ", "")
                if kw_no_space != kw:
                    text = text.replace(kw_no_space, "***")

    # ---------- 第二步：近义词替换 ----------
    replacements = {
        # ========== 核心敏感词 ==========
        "补贴": "补助",
        "稳岗": "稳工",
        "返还": "退回",
        "社保": "保险",
        "失业": "待业",
        "就业": "用工",
        "培训": "培养",
        "吸纳": "接收",
        "安置": "安排",
        "奖励": "鼓励",
        "见习": "实习",
        "扩岗": "增岗",
        "招工": "招聘",
        "用工": "用人",
        "招聘": "招募",

        # ========== 人群类 ==========
        "残疾人": "残障人士",
        "脱贫": "解困",
        "脱贫人口": "困难群体",
        "建档立卡": "登记在册",
        "高校毕业生": "应届生",
        "登记失业": "登记待业",
        "就业困难": "用工困难",
        "就业困难人员": "用工困难群体",
        "失业人员": "待业人员",
        "失业青年": "待业青年",
        "离校未就业": "毕业未用工",
        "低保": "困难",
        "低保家庭": "困难家庭",

        # ========== 文件/政策类 ==========
        "通知": "公告",
        "通告": "公告",
        "关于印发": "关于发布",
        "实施细则": "操作办法",
        "申领": "申请",
        "申报": "申请",
        "发放": "拨付",
        "拨付": "支付",

        # ========== 机构类 ==========
        "人社局": "人社部门",
        "就业局": "就业部门",
        "社保局": "保险部门",
        "财政局": "财政部门",

        # ========== 企业/人员类 ==========
        "裁员": "减员",
        "裁员率": "减员率",
        "失业保险": "待业保险",
        "社会保险": "综合保险",
        "保险费": "保费",
        "缴费": "缴纳",
        "参保": "参保",
        "参保企业": "参保单位",
        "中小微企业": "中小企业",
        "大型企业": "大型单位",
        "企业": "单位",
        "员工": "人员",
        "职工": "人员",
        "工资": "薪酬",
        "薪酬": "待遇",
        "待遇": "福利",
        "僵尸": "异常",
        "僵尸企业": "异常单位",

        # ========== 保险/金类 ==========
        "工伤": "职业伤害",
        "养老": "退休",
        "养老保险": "退休保险",
        "失业金": "待业金",

        # ========== 补贴类型 ==========
        "津贴": "补贴",
        "补助": "支持",
        "居民补贴": "居民支持",
        "综合补贴": "综合支持",
        "个人补贴": "个人支持",
        "工资补贴": "薪酬支持",
        "薪资补贴": "薪酬支持",
        "社保补贴": "保险支持",
        "高温补贴": "高温支持",

        # ========== 见习/实习类 ==========
        "见习基地": "实习基地",
        "留用": "留任",
        "留用率": "留任率",

        # ========== 通用组合词替换 ==========
        "一次性扩岗补助": "一次性增岗支持",
        "岗前培训补贴": "岗前培养支持",
        "就业见习补贴": "用工实习支持",
        "稳岗返还补贴": "稳工退回支持",
        "招用高校毕业生": "招聘应届生",
        "吸纳就业": "接收用工",
        "培训补贴": "培养支持",

        # ========== 其他 ==========
        "扫码": "扫码",
        "微信": "微信",
        "支付宝": "支付宝",
        "银行": "银行",
        "账号": "账号",
        "密码": "密码",
        "验证码": "验证码",
        "银行卡": "银行卡",
    }
    # 按长度降序替换，避免短词干扰长词
    for old, new in sorted(replacements.items(), key=lambda x: -len(x[0])):
        text = text.replace(old, new)

    # ---------- 第三步：附加清理 ----------
    text = re.sub(r'\d{5,}', '****', text)
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '***@***.***', text)
    extra = ['社保卡', '身份证', '工资卡', '扫码', '微信', '支付宝', '银行', '账号', '密码', '验证码', '银行卡']
    for kw in extra:
        if kw in text:
            text = text.replace(kw, '***')

    return text
# ==================================================


def generate_policy_report():
    today = datetime.now().strftime("%Y年%m月%d日")

    system_prompt = """你是人社政策情报分析AI。

任务：搜索2026年1月1日之后新发布的企业补贴政策，覆盖江西省、安徽省、江苏省、浙江省，输出表格格式政策追踪报告。

## 强制限制

### 绝对禁止
- 禁止生成任何中间文件
- 禁止在最终文档中添加总结、建议等额外文字
- 禁止输出官网首页链接（必须输出政策原文链接）
- 禁止链接带追踪参数
- 禁止使用短链接
- 链接必须指向政策原文页面

### 明确排除的文件类型
- 标题包含"公示"的所有文件
- 任何涉及资金分配、补贴发放名单的公示文件
- "灵活就业社保补贴"相关文件
- "创业担保贷款"相关文件

### 明确排除的链接类型
- 官网首页
- 栏目页
- 列表页
- 转发/转载页面

## 城市清单

**江西省**：赣州市、吉安市、九江市、宜春市、鹰潭市、抚州市、上饶市

**安徽省**：阜阳市、合肥市、宿州市、铜陵市、宣城市、蚌埠市、亳州市、滁州市、淮北市、安庆市

**江苏省**：淮安市、南通市、泰州市、徐州市、盐城市、常州市、连云港市、南京市、宿迁市、镇江市

**浙江省**：杭州市、湖州市、宁波市、衢州市、温州市

## 搜索要求

### 政策范围
- 部门来源：人社局、就业局相关政策
- 补贴类型（针对企业的奖补）：
  - 稳岗补贴/稳岗返还补贴
  - 就业补贴、培训补贴
  - 残疾人安置补贴
  - 扩岗补贴、吸纳就业补贴
  - 招工/用工/招聘补贴
  - 见习补贴/见习基地
  - 岗位补贴、引才奖励
  - 返乡就业补助、跨省就业补助

### 时间范围
- 发布日期：2026年1月1日之后
- 截止日期必须晚于当前日期

## 核心信息要素

| 字段 | 要求 |
|------|------|
| 省份 | 政策发布省份 |
| 城市 | 适用城市（多个用顿号分隔） |
| 政策名称 | 完整政策标题（作为链接文字） |
| 核心申请条件 | 企业适用条件 |
| 补贴标准/金额 | 具体金额或比例 |
| 开放申请及截止日期 | 格式：YYYY-MM-DD |
| 政策原文链接 | 可点击的官方政策原文URL |

## 搜索关键词组合

对每个城市使用以下关键词搜索（site:.gov.cn）：
稳岗补贴、稳岗返还、就业补贴、培训补贴、扩岗补贴、吸纳就业补贴、招工补贴、见习补贴、引才奖励、返乡就业补贴、残疾人安置补贴

## 输出格式

### 格式要求
- 只生成一个 Markdown 表格
- 表格表头：省份 | 城市 | 政策名称 | 核心申请条件 | 补贴标准/金额 | 开放申请及截止日期 | 政策原文链接
- 政策名称列：使用 `[政策名称](政策原文URL)` 格式

### 数据处理规则
- 省级政策覆盖多个城市：城市列用顿号分隔
- 市级政策：城市列填写具体城市名称
- 同一城市多个政策：每个政策单独一行
- 无新政策的城市：不输出该城市

## 输出前自检清单

- [ ] 日期合规：开放申请日期 ≥ 2026-01-01
- [ ] 日期有效：截止日期 > 当前日期
- [ ] 链接原文合规：URL含 /art/、/zhengce/、/policy/ 等路径
- [ ] 来源合规：仅gov.cn官方域名
- [ ] 无公示文件
- [ ] 格式极简：仅表格，无多余文字

请开始生成报告。"""

    user_prompt = f"请生成2026年人社补贴政策追踪报告（江西安徽江苏浙江），政策发布日期为2026年1月1日之后，截止当前日期（{today}）仍未过期的政策。严格按照固定格式输出。"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "stream": False
    }

    print("  📡 正在联网搜索江西安徽江苏浙江人社补贴政策...")
    resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=300)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    print(f"  ✅ 生成完成，共 {len(content)} 字符")
    return content


def parse_markdown_table_to_list(markdown_text):
    lines = markdown_text.strip().split('\n')
    if len(lines) < 2:
        return None, None
    data_lines = [line for line in lines if '---' not in line]
    if len(data_lines) < 2:
        return None, None
    header_line = data_lines[0]
    headers = [h.strip() for h in header_line.split('|') if h.strip()]
    rows = []
    for line in data_lines[1:]:
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if cells:
            rows.append(cells)
    return headers, rows


def extract_link(text):
    match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', text)
    if match:
        return match.group(1), match.group(2)
    return text, None


def send_rich_text_message(access_token, receive_id, rows, region="江西安徽江苏浙江"):
    if not receive_id or receive_id == "":
        print("  ❌ RECEIVE_OPEN_ID_POLICY 未配置")
        return

    md_lines = []
    md_lines.append(f"📋 2026年人社补贴政策追踪（{region}）\n")

    md_lines.append("| 省份 | 城市 | 政策名称 | 核心申请条件 | 补贴标准/金额 | 截止日期 |")
    md_lines.append("|------|------|----------|--------------|----------------|----------|")

    policy_count = 0
    max_policies = len(rows)
    for row in rows:
        if policy_count >= max_policies:
            break
        if len(row) < 7:
            continue
        province = row[0]
        city = row[1]
        policy_name_raw = row[2]
        condition = row[3] if len(row) > 3 else ""
        subsidy = row[4] if len(row) > 4 else ""
        deadline = row[5] if len(row) > 5 else "详见原文"

        province = filter_sensitive(province)
        city = filter_sensitive(city)
        condition = filter_sensitive(condition)
        subsidy = filter_sensitive(subsidy)
        deadline = filter_sensitive(deadline)

        display_name, _ = extract_link(policy_name_raw)
        if not display_name:
            display_name = policy_name_raw
        display_name = filter_sensitive(display_name)

        website = get_website(city)
        policy_cell = f"[{display_name}]({website})"

        md_lines.append(f"| {province} | {city} | {policy_cell} | {condition} | {subsidy} | {deadline} |")
        policy_count += 1

    total_count = len(rows)
    if total_count > max_policies:
        md_lines.append(f"\n📊 共找到 {total_count} 条政策，当前展示前 {max_policies} 条")
    else:
        md_lines.append(f"\n📊 共找到 {total_count} 条政策")

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

    msg_size = len(json.dumps(payload, ensure_ascii=False))
    print(f"  📊 消息体积：{msg_size} 字节")

    resp = requests.post(send_url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ 发送失败: {resp.text}")
        resp.raise_for_status()

    print(f"  ✅ 富文本消息发送成功，共 {policy_count} 条政策")


def main():
    print("=" * 50)
    print("📋 人社补贴政策追踪（江西安徽江苏浙江）")
    print("=" * 50)

    print("\n1. 生成政策追踪报告...")
    md_content = generate_policy_report()
    print("=== DeepSeek 返回的完整 Markdown 内容 ===")
    print(md_content)
    print("=== 内容结束 ===")

    print("\n2. 解析 Markdown 表格...")
    headers, rows = parse_markdown_table_to_list(md_content)
    if not headers or not rows:
        print("  ❌ 未能解析出表格数据")
        return

    print(f"  ✅ 解析成功，表头: {len(headers)} 列，数据: {len(rows)} 行")

    print("\n3. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)

    print("\n4. 发送富文本消息...")
    send_rich_text_message(token, RECEIVE_OPEN_ID_POLICY, rows, "江西安徽江苏浙江")

    print("\n✅ 政策追踪报告发送完成！")


if __name__ == "__main__":
    main()
