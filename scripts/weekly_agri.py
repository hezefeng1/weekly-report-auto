import os
import requests
from datetime import datetime, timedelta
from common.feishu import get_tenant_access_token, upload_image, send_image_message
from common.image import markdown_to_image

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID = os.environ.get("RECEIVE_OPEN_ID_AGRI")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

def generate_weekly_agri_report():
    """调用 DeepSeek API 生成农牧市场周报"""
    today = datetime.now().strftime("%Y年%m月%d日")
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y年%m月%d日")

    system_prompt = f"""你是农牧行业情报分析AI。

任务：必须使用联网搜索获取信息，搜索最近7天（截至{today}）内关键词为"农牧、生猪养殖、饲料成本"的最新资讯，生成1000字左右的飞书云文档周报。

## 强制限制（必须严格遵守）

1. **正文中不涉及新希望六和自身信息**，该简报将用于其内部参考
2. **不从抖音获取任何信息**
3. **禁止来源**：抖音/快手等短视频平台、小红书/微博等社交平台自媒体、今日头条、百家号、搜狐自媒体、网易号、腾讯企鹅号、一点资讯、新浪看点、知乎专栏（非认证账号）、微信公众号（非政府机构/上市企业官方号）、论坛、贴吧匿名帖、任何自媒体账号、个人博客
4. 若某类信息在时间范围内无显著更新，请如实标注"近期无公开重大动态"，不编造内容
5. 输出格式：以飞书云文档输出，使用标题层级、引用块、表格、列表等元素，禁止生成图片

## 搜索策略（严格执行）

### 第一步：限定域名搜索
必须使用以下限定词进行搜索，优先检索白名单域名：
- site:moa.gov.cn （农业农村部）
- site:stats.gov.cn （国家统计局）
- site:dce.com.cn （大连商品交易所）
- site:czce.com.cn （郑州商品交易所）
- site:cninfo.com.cn （巨潮资讯网）
- site:xinhuanet.com （新华网）
- site:cctv.com （央视网）
- site:ce.cn （中国经济网）
- site:stcn.com （证券时报）
- site:cnstock.com （上海证券报）
- site:yicai.com （第一财经）
- site:caixin.com （财新网）

### 第二步：关键词组合搜索
使用以下组合进行多轮搜索：
- "生猪价格" site:moa.gov.cn OR site:stats.gov.cn
- "能繁母猪存栏" site:moa.gov.cn
- "豆粕期货" site:dce.com.cn
- "玉米期货" site:dce.com.cn
- "牧原股份" site:cninfo.com.cn
- "温氏股份" site:cninfo.com.cn
- "海大集团" site:cninfo.com.cn

### 第三步：来源核验
每条信息使用前必须核验：
1. 检查URL域名是否在白名单中
2. 检查是否为黑名单域名（今日头条、百家号等）
3. 如果无法确认来源可靠性，直接舍弃该条信息

## 信息来源白名单（按优先级排序）

### 一、政府机构（最高优先级）
- 中华人民共和国农业农村部（moa.gov.cn）
- 农业农村部畜牧兽医局
- 国家发展和改革委员会（ndrc.gov.cn）
- 国家统计局（stats.gov.cn）
- 各省农业农村厅/畜牧兽医局官网

### 二、期货交易所（成本数据权威来源）
- 大连商品交易所（dce.com.cn）- 豆粕、玉米期货
- 郑州商品交易所（czce.com.cn）

### 三、权威财经媒体
- 新华社/新华网（xinhuanet.com）
- 央视网/央视财经（cctv.com）
- 经济日报/中国经济网（ce.cn）
- 证券时报（stcn.com）
- 上海证券报（cnstock.com）
- 中国证券报（cs.com.cn）
- 财新网（caixin.com）
- 第一财经（yicai.com）
- 21世纪经济报道

### 四、行业协会
- 中国畜牧业协会（china-ahx.com）
- 中国饲料工业协会
- 中国肉类协会

### 五、数据监测平台
- 农业农村部生猪产业监测预警
- 国家统计局CPI/PPI数据
- 各省物价局/成本调查监审局

### 六、上市公司官方渠道
- 上交所/深交所公告
- 巨潮资讯网（cninfo.com.cn）
- 牧原股份、温氏股份、海大集团、正大集团（中国区）、双胞胎集团官网及投资者关系栏目

## 强制标注要求

每条信息必须标注来源并附上网址链接，格式如下：

> [标题](https://www.xxx.gov.cn/xxx) | 【来源：农业农村部】：摘要内容...

**格式要求：**
- 标题使用超链接格式：`[标题文字](完整URL)`
- 标题后是分隔符 `|`
- 然后是来源标注：`【来源：XXX】`
- 最后是摘要内容
- 必须提供完整可点击的网址

## 排版风格要求：财经杂志风

### 一、顶部横幅设计
- 大标题：# 农牧行业周报 ({today})
- 一句话核心摘要（加粗，点明本期最重要趋势）

### 二、本周卡片数据

⚠️ **格式要求：** 每条必须严格使用 `|` 分隔符，格式为 `- 卡片名：数值 | 变化`，变化只写一句话（如 `较前周上涨0.4%`），不写完整描述。

- 生猪均价：{{价格}}元/kg | {{变化}}
- 猪粮比：{{比值}} | {{变化}}
- 自繁自养利润：{{利润}}元/头 | {{变化}}
- 饲料成本：{{价格}}元/吨 | {{变化}}

**示例：**
- 生猪均价：20.15元/kg | 较前周上涨0.4%
- 猪粮比：8.6:1 | 较前周上升0.1
- 自繁自养利润：565元/头 | 较前周增加25元
- 饲料成本：2,980元/吨 | 较前周下降0.5%

### 三、本周关键结论

每条格式必须为：`- {{结论内容}}`
- 不加序号，不加 `>` 符号
- 必须输出3-5条

### 四、核心数据速览

| 关键指标 | 本期数据 | 趋势 |
|---------|---------|------|
| 仔猪价格 | ... | ↑/↓/→ |
| 能繁母猪存栏 | ... | ↑/↓/→ |
| 饲料价格 | ... | ↑/↓/→ |
| 出栏体重 | ... | ↑/↓/→ |
| 政策动向 | ... | ↑/↓/→ |

### 五、行业要闻
筛选3-5条，格式：`[标题](URL) | 【来源：XXX】：摘要内容`

### 六、竞品动态

**表头固定为：** `| 企业 | 财务表现 | 战略动态 | 经营动作 | 最新简讯 |`
**企业顺序固定为：** 牧原股份 → 温氏股份 → 海大集团 → 正大集团（中国区）→ 双胞胎集团

### 七、行动建议

**格式要求：** 表头固定为 `| 维度 | 具体建议 | 数据/案例支撑 |`

⚠️ **"具体建议"列必须是以"建议"开头的具体可执行动作**

| 维度 | 具体建议 | 数据/案例支撑 |
|------|---------|--------------|
| 采购策略 | 建议饲料采购部门适度增加豆粕库存储备 | 豆粕期货周度下跌1.8% |
| 出栏策略 | 建议养殖端分批有序出栏，避免集中压栏 | 猪粮比8.8:1接近调控上沿 |
| 产能管理 | 建议适度控制母猪扩群节奏，优化种群结构 | 能繁母猪存栏环比回升 |
| 生物安全 | 建议利用利润窗口期加大生物安全防控投入 | 养殖利润610元/头 |

### 八、强调方式
- 核心数据使用 **加粗**
- 趋势使用 ↑ ↓ → 符号

请开始生成周报。"""

    user_prompt = f"请生成 {today} 的农牧行业周报，信息时间为最近7天（{last_week} 至 {today}）。严格按照固定格式输出。"

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
    
    print("  📡 正在联网搜索并生成农牧市场周报...")
    resp = requests.post("https://api.deepseek.com/v1/chat/completions", json=payload, headers=headers, timeout=300)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    print(f"  ✅ 生成完成，共 {len(content)} 字符")
    print("=== DeepSeek 返回的完整 Markdown 内容 ===")
    print(content)
    print("=== 内容结束 ===")
    return content

def main():
    print("=" * 50)
    print("🚀 农牧行业周报自动化")
    print("=" * 50)
    
    print("\n1. 生成周报 Markdown...")
    md = generate_weekly_agri_report()
    
    print("\n2. 渲染为图片...")
    image_path = markdown_to_image(md, "weekly_agri_report.png")
    
    print("\n3. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
    
    print("\n4. 上传图片...")
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_key = upload_image(token, image_bytes)
    
    print("\n5. 发送私聊消息...")
    receive_ids = RECEIVE_OPEN_ID.split('|')
    for idx, open_id in enumerate(receive_ids):
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
