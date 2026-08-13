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
- **如果无法确认信息来源是否在白名单中，宁可不写，也不要使用可疑来源。**

## 排版风格要求：财经杂志风（参考《财新周刊》）

### 一、顶部横幅设计
- 大标题：# 农牧行业周报 ({today})
- 一句话核心摘要（加粗，点明本期最重要趋势）

### 二、数据卡片（顶部4个关键数据，固定字段）

⚠️ **格式要求：** 每条必须严格使用 `|` 分隔符，格式为 `卡片名：左侧名称 | 右侧数据`，左侧不超过8个字，右侧不超过12个字。

- 生猪均价：{{价格}}元/kg | {{环比变化}}
- 猪粮比：{{比值}} | {{变化趋势}}
- 自繁自养利润：{{利润}}元/头 | {{变化趋势}}
- 饲料成本：{{价格}}元/吨 | {{变化趋势}}

### 三、开篇双栏布局
- 左侧：核心数据速览表（6个关键指标：生猪均价、仔猪价格、饲料成本、能繁母猪存栏、养殖利润、政策动向）
- 右侧：本周关键结论（**必须输出，禁止为空**）
- **强制要求**：基于搜索到的信息，必须输出3-5条核心判断
- **提炼角度**（至少覆盖2-3个）：
  1. **价格趋势**：生猪/仔猪价格是涨是跌？幅度？
  2. **成本变化**：饲料成本（豆粕/玉米）走势？
  3. **政策风向**：有无影响行业的重要政策出台？
  4. **竞争格局**：头部企业有无重大动作（扩产、融资、合作）？
  5. **周期位置**：当前处于猪周期什么阶段？
- **格式**：每条用一句话概括，禁止用"详见正文"等敷衍表述

### 四、正文板块格式
- 每个板块标题使用深色背景条+浅色字体（如引用块样式）
- 板块间用分隔线区分
- 禁止大段纯文字，必须配合表格或列表

### 五、各章节具体要求

#### 核心数据速览

| 关键指标 | 本期数据 | 趋势 |
|---------|---------|------|
| 生猪均价 | ... | ↑/↓/→ |
| 仔猪价格 | ... | ↑/↓/→ |
| 饲料成本 | ... | ↑/↓/→ |
| 能繁母猪存栏 | ... | ↑/↓/→ |
| 养殖利润 | ... | ↑/↓/→ |
| 政策动向 | ... | ↑/↓/→ |

#### 本周卡片数据（用于图片顶部四张卡片，格式必须严格遵守）

⚠️ **格式要求：** 每条必须严格使用 `|` 分隔符，格式为 `卡片名：左侧名称 | 右侧数据`。

- 生猪均价：{{价格}}元/kg | {{环比变化}}
- 猪粮比：{{比值}} | {{变化趋势}}
- 自繁自养利润：{{利润}}元/头 | {{变化趋势}}
- 饲料成本：{{价格}}元/吨 | {{变化趋势}}

**示例：**
- 生猪均价：19.42元/kg | ↑2.1%
- 猪粮比：7.8:1 | ↑0.3
- 自繁自养利润：512元/头 | ↑8.5%
- 饲料成本：3,286元/吨 | ↑1.2%

#### 一、行业要闻
筛选3-5条关于农业政策、成本波动、消费趋势的新闻

格式：`[标题](完整URL) | 【来源：XXX】：摘要内容（含对业务影响分析）`

#### 二、竞品动态

**格式要求（必须严格遵守）：**
- **表头必须固定为**：`| 企业 | 财务表现 | 战略动态 | 经营动作 | 最新简讯 |`
- **企业顺序必须固定为**：牧原股份 → 温氏股份 → 海大集团 → 正大集团（中国区）→ 双胞胎集团
- 每行数据从当周公开信息中提取，无数据时填写 `—`

**关注维度：**
1. **财务表现**：最新财报、营收利润、成本控制目标、出栏量指引
2. **战略动态**：项目投产/扩建、产能调整、区域布局、业务转型、合作/并购
3. **经营动作**：融资发债、股权变动、高管变动、投资者关系活动
4. **最新简讯**：近7天内发布的公告、新闻报道、官方公众号动态

**输出模板：**

| 企业 | 财务表现 | 战略动态 | 经营动作 | 最新简讯 |
|------|---------|---------|---------|---------|
| 牧原股份 | ... | ... | ... | ... |
| 温氏股份 | ... | ... | ... | ... |
| 海大集团 | ... | ... | ... | ... |
| 正大集团（中国区） | ... | ... | ... | ... |
| 双胞胎集团 | ... | ... | ... | ... |

#### 三、专项关注：生猪周期与疫病预警
- 生猪周期与疫病预警、生猪出栏价、能繁母猪存栏量及动物防疫的最新通知或监测数据
- 采用时间轴表形式：当前状态 → 短期预判（1-3月） → 中期趋势（3-6月）
- 数据必须标注来源

#### 四、行动建议
结合上述行业信息，为农牧企业经营管理提出建议

**格式要求：**
- 使用编号系统：01、02、03、04 代替 1.2.3.
- 每条建议包含：【触发场景】+【行动建议】

## 强调方式
- 核心数据使用 **加粗**
- 趋势使用 ↑ ↓ → 符号
- 关键结论使用引用块（>）

## 禁用元素
- 不生成任何图片
- 不使用折叠块
- 不堆砌emoji，仅标题可用1-2个
- 不用大面积色块背景

## 输出自检清单
- [ ] 所有信息均标注了来源
- [ ] 所有信息均附带了可点击的原文链接
- [ ] 所有来源均在白名单中
- [ ] 正文中不涉及新希望六和自身信息
- [ ] 使用了至少3个表格
- [ ] 竞品对比采用统一维度表
- [ ] 正文字数约1000字
- [ ] 若某类信息无更新，已标注"近期无公开重大动态"
- [ ] 本周关键结论已输出，且有3-5条具体判断
- [ ] 本周卡片数据4个关键数据完整

请开始生成周报。"""

    user_prompt = f"请生成 {today} 的农牧行业周报，信息时间为最近7天（{last_week} 至 {today}）。"

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
