# 个股跟踪 cron 模板
# 适用：~/scripts/ 或 ~/.hermes/cron/ 创建 cron job
# 用法：复制本文件 → 替换 {{占位符}} → 用 hermes cron create 提交
# 配套文章模板：templates/stock-article-template.md
# 配套文章 file path：src/content/blog/YYYYMMDD-CODE-slug.md（URL = /CODE-slug/）

---

跟踪 {{NAME}} ({{CODE_PLAIN}}.{{EXCHANGE}}) 的盘中表现并按规则推送 + 同步到博客。

## 标的
- 名称：{{NAME}}
- 代码：{{CODE_PLAIN}}.{{EXCHANGE}}（{{板块：主板/科创/创业/科创板/创业板}}）
- 行业：{{行业 1}} + {{行业 2}} + {{行业 3}}
- 跟踪背景（必读）：站点已发布分析 `https://stock.peekabo.cc/{{CODE_PLAIN}}-{{SLUG}}/` —— 关键价位 {{关键位列表}}、止损 {{止损位}}、半年涨跌幅 {{X%}}、{{基本面锚点 1}}
- 短期操作框架：
  - {{建仓区间 1}} 区间分批建仓（试探仓 {{X%}} / 主仓 {{X%}} / 重仓 {{X%}}）
  - 跌破 {{止损位}} 全部清仓
  - 反弹 {{减仓区间 1}} / {{减仓区间 2}} / {{突破位}} 分批减仓
  - 短线（1–3 天）{{不追 / 可跟进}}，{{等放量阳线 + 站稳 X.X 才算右侧信号}}

## 触发节奏
- 盘前（每个交易日 09:25）：检查昨日收盘 + 今日集合竞价 + 隔夜美股 {{相关板块}}
- 盘中（每个交易日 11:00 / 14:00）：价格 + 量能 + 板块联动
- 盘后（每个交易日 15:30）：当日收盘 + 融资融券变化 + 公告/新闻

## 监控内容
1. **收盘价 / 涨跌幅**（iWencai 优先，mx-data 辅助）
2. **关键位测试**：是否触及 {{关键位列表}}
3. **量能变化**：今日成交量 vs 近 5 日均量 vs 近 20 日均量
4. **资金面**：融资净买入/净偿还、融券余量变化
5. **板块联动**：{{相关板块 1}} 指数、{{相关板块 2}} 板块（防止板块情绪拖累）
6. **公告 / 新闻**：mx-search {{NAME}} {{CODE_PLAIN}} 最近公告 新闻

## 触发推送的规则（避免噪音）
**只在以下任一条件满足时推送：**
- 价格突破 / 跌破任一关键位（{{所有关键位}}）
- 单日涨跌 > 3%
- 单日成交量 > 近 5 日均量 × 1.5 倍
- 出现新公告（mx-search 拉到 date == 今天）
- 融资净买入/偿还 > 500 万
- 板块联动：{{相关板块 1}} 指数或 {{相关板块 2}} 板块当日涨跌 > 4%

**其他情况静默**（不推送，节省 tokens）。但**每次运行均必须同步自动修改博客，保持内容信息最新。** 每次运行都把最新价/量能/筹码写到状态文件。

## 操作

### Step 1: 拉数据（**双源对账**——mx-data 是盘中价，iWencai 是收盘价）

**1a. mx-data（盘中价 / 实时）：**
```bash
python /root/skills/mx-data/mx-data/mx_data.py "{{NAME}} {{CODE_PLAIN}} 最新价 涨跌幅 成交量"
```

**1b. iWencai 收盘价 + 完整字段（**必须**，用于价格/振幅/成交额/换手率对账）：**
```bash
cd /root/skills/hithink-astock-selector && python scripts/cli.py --query "{{NAME}} {{CODE_PLAIN}} 收盘价 涨跌幅 成交量 振幅 换手率 成交额"
```

**1c. 资讯：**
```bash
python /root/skills/mx-search/mx-search/mx_search.py "{{NAME}} {{CODE_PLAIN}} 最新公告 新闻"
```

**1d. 对账规则：**
- 价差 < 0.2% → 接受 mx-data 盘中价
- 价差 0.2% ~ 0.5% → 用 iWencai 收盘价覆盖分析
- 价差 > 0.5% → 异常告警（异动 / 涨停 / 数据延迟）

**写状态文件时必须包含两个源的最新价：**
```json
{
  "as_of": "{{ISO 8601 BJT}}",
  "ticker": "{{CODE_PLAIN}}.{{EXCHANGE}}",
  "name": "{{NAME}}",
  "mx_data": {"price": {{X.XX}}, "pct": {{X.XX}}, "volume": "—", "as_of": "盘中"},
  "iwencai": {"close": {{X.XX}}, "pct": {{X.XX}}, "volume": {{N}}, "amplitude": {{X.XX}}, "turnover_rate": {{X.XX}}, "amount": "{{X.XX}}亿", "as_of": "收盘"},
  "delta_pct": {{X.XX}},
  "verdict": "用 iWencai 收盘价（盘后），盘中价仅作盘中参考",
  "key_levels": {"stop": {{X.XX}}, "buy_low": {{X.XX}}, "buy_mid": {{X.XX}}, "buy_high": {{X.XX}}, "reduce_1": {{X.XX}}, "reduce_2": {{X.XX}}, "breakout": {{X.XX}}}
}
```

### Step 2: 判定是否触发推送
按监控规则过一遍。**无论是否命中，均必须同步自动修改博客文章并提交 Git（即执行 Step 3）。** 对于 Telegram 消息，若有任一规则命中，或在下午盘后（15:00 后）运行，则发送相应消息；否则（上午未命中且无触发规则）保持静默不发送 Telegram。

### Step 3: 同步到博客（每次运行均执行，顶部插入 H3 + 全文修订 + 5 交易日清理）

**3a. 编辑 `/root/projects/stock-research-blog/src/content/blog/{{FILE_ID}}.md`（注意 FILE_ID = YYYYMMDD-CODE_PLAIN-SLUG，URL = /CODE_PLAIN-SLUG/）：**

**【R1: URL 已稳定】** 站点 URL = `https://stock.peekabo.cc/{{CODE_PLAIN}}-{{SLUG}}/`（去日期前缀，patch 已生效）。文件 ID 仍为 {{FILE_ID}}，但 frontmatter + 内容是同一个文件，永远不要改文件名（避免外链失效）。

**【R2: 跟踪段始终在 H1 后顶部插入】** 不再"追加到文末"。把最新的跟踪段插在 `## 跟踪记录` H2 容器**内、已有跟踪段之上**（newest first）。
- 跟踪段统一使用 H3 格式：`### 跟踪 YYYY-MM-DD HH:MM BJT`（注意 H3 不是 H2，slug 自动生成）
- 同一日内多次更新时，更早的段落会下沉
- 区块结构按 templates/stock-article-template.md 中"### 跟踪"块填写
- 切忌把"跟踪记录"放到文末——它必须在 H1 标题之后、其它 H2 章节之前

**【R3 + R4: 快捷栏自动按日期分组 + 只显示近 5 个交易日】** 站点 `BlogPost.astro` 已实现 `stockTrackGroupsByDate` 逻辑：
- 同一日的多个 H3 跟踪段 → sidebar 自动合并为 1 个日期格
- 徽章显示当日跟踪段数量（>1 才显示）
- 点击跳转该日**时间最晚**的那条 H3（slug 已对应）
- **sidebar 硬约束：只显示近 5 个交易日的日期格**（`TRACK_DAYS_WINDOW = 5`）
- 你的责任是**只输出正确格式的 H3**，sidebar 自动接管

**【5 交易日保留：文章内的跟踪段清理】** 每次更新时检查跟踪段数量：
- 跟踪段按日期分组、保留近 5 个交易日的所有 H3 段
- 超出 5 个交易日的最老 H3 段（不是 5 段、是 5 个**交易日**），整段从文章中删除
- 删除前先备份：当次 commit message 必须包含 "archive" + 删除的 H3 段日期
- 5 个交易日窗口 = 当前 date - 5 自然日（按工作日）

**【R5: 全文修订（每次必改）】** 每次跟踪更新时，**除插入新跟踪段外，必须全文扫一遍其它 H2 章节，按以下规则修订**：

| 章节 | 必改触发条件 | 修订内容 |
|---|---|---|
| **结论先行** | **每次必改** | 同步当前 iWencai 收盘价 + mx-data 盘中价 + 涨跌幅 + 距关键位距离 + 止损位。触发原因若改变 1–3 天框架（突破 / 跌破 / 涨停 / 缩量）必须改写整个"短线 / 波段 / 减仓 / 止损"4 段 |
| **关键价位** | 关键位区间原则上不变 | {{所有关键位区间}} 固定。新增密集成交区 / 公司基本面变化（如回购价改变）时**补一行说明** |
| **近 1 个月行情** | **每月 1 日 / 每月 15 日 / 触发价差异动时** | 用最新 1 个月的 mx-data 重算涨跌幅 / 区间高低点。日常触发时只更新最新一行价 + 涨跌幅 |
| **近半年走势** | 6 个月数据每月才用一次 | 1 号节点重算；平时不动 |
| **三个买入理由** | mx-search 拉到 date == 今天的新公告影响某条 | 更新对应条目；不变的不动 |
| **三个风险** | 同上 | 同上 |
| **分批买入 / 减仓计划** | 评级改变时 | 更新"操作"列；价位档位不变 |
| **行业 / 基本面锚点** | 公告触发时 | 更新对应条目 |
| **风险点** | 固定条目原则不动 | 重大新风险时**追加**（不删） |

**简化规则：**
- **结论先行 = 每次必改**（其他 H2 章节的最权威摘要）
- **近 1 个月行情 = 数据有变就改**
- **关键价位档位永不动**（这是操作锚点，变了读者会乱）

**3b. 更新 frontmatter：**
- 同步 `updatedDate: YYYY-MM-DDTHH:MM:00+08:00`（必须 BJT +08:00 时区）
- `pubDate` 不动（首发时间保留）
- `description` = "最新结论：<一句话重写当前框架>"（保持 80–120 字内）

**3c. build + 提交：**
```bash
cd /root/projects/stock-research-blog && npm run build
git add src/content/blog/{{FILE_ID}}.md
git commit -m "[{{SLUG}}-tracker] YYYY-MM-DD HH:MM 触发原因简述 + 全文修订 (结论先行+近1月+...) [+ archive <删除了的日期>]"（若非触发运行，则 `触发原因简述` 填写 `定时同步` 或 `盘后同步`）
git push origin main
```

### Step 4: 落盘 fact_store
每次触发推送时，调用 fact_store action="add" 存一条：
- category: "project"
- content: "{{NAME}} {{CODE_PLAIN}} 跟踪 YYYY-MM-DD HH:MM BJT：iWencai 收盘价 X 元（±X%），mx-data 盘中价 X 元（价差 X%）；成交量 X 万股，振幅 X%，成交额 X 亿，换手率 X%；触发 <原因>。当前距关键位 {{所有关键位}} 分别 X%。本次修订章节：<列出本次全文修订改过的 H2 章节>。"
- tags: "{{SLUG}},{{CODE_PLAIN}},tracker,YYYY-MM-DD,dual-source,full-revision"

⚠️ 已知 fact_store hrr_vector 编码告警"inhomogeneous shape"是误报，写入仍成功。看到此错不要重试，避免重复存。

### Step 5: 推送格式（命中时）
```
📊 {{NAME}} {{CODE_PLAIN}} 跟踪

⏰ YYYY-MM-DD HH:MM BJT
💰 收盘价（iWencai）：X.XX 元（±X.XX%）
📊 盘口价（mx-data）：X.XX 元
📈 量能：X 万股（vs 5日均量 ±X%）
💵 成交额：X.XX 亿 · 换手率：X.XX%

🚨 触发：<具体原因>

🔑 关键位状态：
- {{止损位}} 止损位：距 X%
- {{建仓下沿}} 建仓下沿：距 X%
- {{建仓上沿}} 建仓上沿：距 X%
- {{减仓一档}} 减仓一档：距 X%
- {{减仓二档}} 减仓二档：距 X%
- {{突破位}} 突破位：距 X%

📌 下一步：<具体动作 / 观察点>

📝 本次修订章节：<列出本次改过的 H2 章节，未改则写"无">

🔗 详情：https://stock.peekabo.cc/{{CODE_PLAIN}}-{{SLUG}}/
```

## 注意事项
- **关键位状态**要算清楚"距 X%"，不能含糊
- 量能对比必须用近 5 日均量（不是 20 日），更敏感
- 推文要短、有信号感；不堆数据
- **未触发推送时不要发送任何消息给用户**（watchdog pattern：静默 + 仅落盘）
- 静默运行也要把 state 写全，便于下次推理
- 跟踪期间站点已经发布，无需重复首发
- 跟踪段永远在 H1 后顶部插入（H3 ### 跟踪 ...），不再追加到文末
- 每次同步必须全文扫一遍其它 H2 章节，按 R5 规则修订
- URL 固定 https://stock.peekabo.cc/{{CODE_PLAIN}}-{{SLUG}}/（去日期前缀，patch 已生效）

## 一次性配置（脚本启动时执行一次）
```bash
mkdir -p /root/.hermes/state
echo '{"created":"'$(date -Iseconds)'","ticker":"{{CODE_PLAIN}}.{{EXCHANGE}}","name":"{{NAME}}","current_price_iwencai":{{X.XX}},"current_price_mxdata":{{X.XX}},"as_of":"{{ISO 8601 BJT}}","key_levels":{"stop":{{X.XX}},"buy_low":{{X.XX}},"buy_mid":{{X.XX}},"buy_high":{{X.XX}},"reduce_1":{{X.XX}},"reduce_2":{{X.XX}},"breakout":{{X.XX}}}}' > /root/.hermes/state/{{SLUG}}_tracker.json
```
