import os
import requests
from datetime import datetime, timedelta
from common.feishu import get_tenant_access_token, upload_image, send_image_message
from common.image import markdown_to_image

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
RECEIVE_OPEN_ID = os.environ.get("RECEIVE_OPEN_ID")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

def generate_weekly_report():
    """调用 DeepSeek API 生成人力资源周报"""
    today = datetime.now().strftime("%Y年%m月%d日")
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y年%m月%d日")

    system_prompt = f"""你是农牧行业人力资源情报AI。

任务：必须使用联网搜索获取信息，搜索最近7天（截至{today}）内关键词为"农牧、生猪养殖、饲料成本、农业人才、HR策略、招聘趋势、薪酬福利"的最新资讯，生成1000字左右的飞书云文档专业人力资源周报。

## 强制限制（必须严格遵守）

1. **正文中不涉及新希望六和自身信息**，该周报将用于其内部人力资源参考
2. **不从抖音获取任何信息**
3. **禁止来源**：抖音/快手等短视频平台、小红书/微博等社交平台自媒体、今日头条、百家号、搜狐自媒体、网易号、腾讯企鹅号、一点资讯、新浪看点、知乎专栏（非认证账号）、微信公众号（非政府机构/上市企业官方号）、论坛、贴吧匿名帖、任何自媒体账号、个人博客
4. 若某类信息在时间范围内无显著更新，请如实标注"近期无公开重大动态"，不编造内容
5. 输出格式：以飞书云文档输出，使用标题层级、引用块、表格、列表等元素，禁止生成图片

## 搜索策略（严格执行）

### 第一步：限定域名搜索
必须使用以下限定词进行搜索，优先检索白名单域名：
- site:cninfo.com.cn （巨潮资讯网-上市公司公告）- **最高优先级**
- site:stcn.com （证券时报）
- site:cnstock.com （上海证券报）
- site:yicai.com （第一财经）
- site:caixin.com （财新网）
- site:cs.com.cn （中国证券报）
- site:xinhuanet.com （新华网）
- site:ce.cn （中国经济网）
- site:liepin.com （猎聘网-行业薪酬报告）
- site:zhaopin.com （智联招聘-行业招聘趋势）
- site:51job.com （前程无忧-行业人才数据）
- site:mohrss.gov.cn （人力资源和社会保障部-仅查宏观人才政策）
- site:rsj.*.gov.cn 或 site:rlzyhshbzj.*.gov.cn （各地人社局-仅查人才引进/补贴政策）

### 第二步：关键词组合搜索

**竞品企业HR动态（优先搜索）：**
- "牧原股份" "人才" OR "招聘" OR "管培生" OR "员工" site:cninfo.com.cn
- "温氏股份" "人才" OR "招聘" OR "薪酬" OR "激励" site:cninfo.com.cn
- "海大集团" "人才" OR "招聘" OR "培训" OR "组织" site:cninfo.com.cn
- "双胞胎集团" "人才" OR "招聘" OR "HR" site:cninfo.com.cn OR site:stcn.com
- "正大集团" "中国区" "人才" OR "招聘" site:stcn.com OR site:yicai.com

**行业HR趋势搜索：**
- "农牧行业" "招聘" OR "人才" OR "薪酬" site:zhaopin.com OR site:liepin.com
- "养殖企业" "人才培养" OR "雇主品牌" site:51job.com
- "农业人才" "薪酬报告" OR "趋势" site:liepin.com

**宏观政策搜索（仅"专项关注"板块使用）：**
- "农业人才" "政策" OR "补贴" site:mohrss.gov.cn
- "乡村振兴" "人才" OR "培养" site:xinhuanet.com

### 第三步：来源核验
每条信息使用前必须核验：
1. **企业HR动态**：检查是否为上市公司公告（cninfo.com.cn）或权威财经媒体报道
2. **行业薪酬数据**：检查是否为招聘平台/HR咨询机构官方报告
3. **宏观人才政策**：检查是否为政府官网（.gov.cn）
4. 检查是否为黑名单域名（今日头条、百家号等）
5. 如果无法确认来源可靠性，直接舍弃该条信息

## 信息来源白名单

### 一、上市公司公告（最高优先级）
- 巨潮资讯网（cninfo.com.cn）
- 上交所/深交所公告
- 牧原股份、温氏股份、海大集团、双胞胎集团、正大集团（中国区）官网投资者关系栏目

### 二、权威财经媒体
- 证券时报（stcn.com）
- 上海证券报（cnstock.com）
- 中国证券报（cs.com.cn）
- 财新网（caixin.com）
- 第一财经（yicai.com）
- 21世纪经济报道
- 新华社/新华网（xinhuanet.com）
- 经济日报/中国经济网（ce.cn）
- 央视网/央视财经（cctv.com）

### 三、权威HR智库/招聘平台
- 猎聘网（liepin.com）
- 智联招聘（zhaopin.com）
- 前程无忧（51job.com）
- 中智咨询、美世、怡安翰威特等权威HR咨询机构

### 四、政府人社部门
- 人力资源和社会保障部（mohrss.gov.cn）
- 农业农村部人事司
- 各地人社局官网（rsj.*.gov.cn）

### 五、行业协会
- 中国畜牧业协会（china-ahx.com）
- 中国饲料工业协会
- 中国肉类协会

## 强制标注要求

每条信息必须标注来源并附上网址链接，格式如下：

> [标题](https://www.xxx.com/xxx) | 【来源：XXX】：摘要内容

**格式要求：**
- 标题使用超链接格式：`[标题文字](完整URL)`
- 标题后是分隔符 `|`
- 然后是来源标注：`【来源：XXX】`
- 最后是摘要内容
- 必须提供完整可点击的网址
- **如果无法确认信息来源是否在白名单中，宁可不写，也不要使用可疑来源。**

## 排版风格要求：财经杂志风（参考《财新周刊》）

### 一、顶部横幅设计
- 大标题：# 农牧行业人力资源周报 ({today})
- 一句话核心摘要（加粗，点明本期最重要的人才趋势）

### 二、开篇双栏布局
- 左侧：核心数据速览表（关键指标：行业招聘热度、重点岗位薪酬变化、人才流动趋势、政策动向）
- 右侧：本周关键结论（3-5条 bullet points）

### 三、各章节具体要求

#### 核心数据速览

| 关键指标 | 本期数据 | 趋势 |
|---------|---------|------|
| 行业招聘热度 | ... | ↑/↓/→ |
| 重点岗位薪酬 | ... | ↑/↓/→ |
| 人才流动趋势 | ... | ↑/↓/→ |
| 政策动向 | ... | ↑/↓/→ |

#### 本周卡片数据（用于图片顶部四张卡片，必须与下方数据速览表内容不同，作为互补视角）

⚠️ **格式要求：** 每条必须严格使用 `|` 分隔符，格式为 `卡片名：左侧名称 | 右侧数据`，左侧为对象/主体，右侧为具体数据/动作。左侧不超过8个字，右侧不超过12个字。

- 关键人才争夺：{{最紧缺岗位名称}} | {{供需比或缺口数据}}
- 组织效能：{{企业名称}} | {{人效/成本变化}}
- 人才结构：{{指标名称}} | {{变化幅度}}
- 竞品动作：{{企业名称}} | {{核心HR动作}}

**示例（严格遵循格式）：**

- 关键人才争夺：兽医/育种专家 | 供需比1:3
- 组织效能：牧原股份 | 人均出栏+12%
- 人才结构：数字化人才渗透率 | 提升至28%
- 竞品动作：温氏股份 | 股权激励2600人

**填写规则（必须严格遵守）：**

1. **关键人才争夺**：从本周「人才供需」或「竞品招聘」信息中，提取最紧缺的一个岗位（如兽医、智能化工程师），附上供需比或缺口数据。
2. **组织效能**：从本周「竞品HR动态」或「行业趋势」中，提取一家头部企业的组织效能变化（人效提升、人均产出、成本优化等），用最简洁的数据说明。
3. **人才结构**：从本周「人才培养」或「专项关注」中，提取人才结构变化的关键指标（如高学历占比、数字化人才渗透率、技能认证覆盖率等）。
4. **竞品动作**：从本周「竞品HR动态」中，提取当周HR动作最显著的一家竞品及其核心动作（股权激励、组织调整、大规模招聘等）。
5. **数据来源**：必须从当周内容中提取，不得凭空编造。若某条数据本周确实没有，可标注 `—`，但要确保至少3条有实际数据。

#### 一、人力资源要闻
筛选5-8条最新人力资源动态，涵盖：招聘、薪酬福利、人才培养、组织架构、人效提升、培训发展、薪酬绩效、企业文化

格式：`[标题](完整URL) | 【来源：XXX】：摘要内容（含对业务影响分析）`

#### 二、行业竞品HR动态

**格式要求（必须严格遵守）：**
- **表头必须固定为**：`| 企业 | 招聘策略 | 人才培养 | 薪酬激励 | 组织/人效 | 最新动态 |`
- **企业顺序必须固定为**：牧原股份 → 温氏股份 → 海大集团 → 双胞胎集团 → 正大集团（中国区）
- 每行数据从当周公开信息中提取，无数据时填写 `—`

**输出模板：**

| 企业 | 招聘策略 | 人才培养 | 薪酬激励 | 组织/人效 | 最新动态 |
|------|---------|---------|---------|----------|---------|
| 牧原股份 | ... | ... | ... | ... | ... |
| 温氏股份 | ... | ... | ... | ... | ... |
| 海大集团 | ... | ... | ... | ... | ... |
| 双胞胎集团 | ... | ... | ... | ... | ... |
| 正大集团（中国区） | ... | ... | ... | ... | ... |

#### 三、专项关注：农牧人才市场洞察
- 行业薪酬趋势分析
- 人才供需状况
- 政策环境支持
- 数字化转型影响

采用表格或结构化列表呈现，数据必须标注来源

#### 四、HR行动建议
以表格形式呈现：

| 维度 | 具体建议 | 数据/案例支撑 |
|------|---------|--------------|
| 招聘策略调整 | | |
| 薪酬福利优化 | | |
| 人才培养重点 | | |
| 人才保留策略 | | |

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

请开始生成周报。"""

    user_prompt = f"请生成 {today} 的农牧行业人力资源周报，信息时间为最近7天（{last_week} 至 {today}）。"

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
    
    print("  📡 正在联网搜索并生成人力资源周报...")
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
    print("🚀 农牧行业人力资源周报自动化")
    print("=" * 50)
    
    print("\n1. 生成周报 Markdown...")
    md = generate_weekly_report()
    
    print("\n2. 渲染为图片...")
    image_path = markdown_to_image(md, "weekly_report.png")
    
    print("\n3. 获取飞书 token...")
    token = get_tenant_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
    
    print("\n4. 上传图片...")
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_key = upload_image(token, image_bytes)
    
    print("\n5. 发送私聊消息...")
    send_image_message(token, RECEIVE_OPEN_ID, image_key)
    
    print("\n✅ 人力资源周报发送完成！")

if __name__ == "__main__":
    main()
