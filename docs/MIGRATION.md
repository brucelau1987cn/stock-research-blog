# Stock 网站迁移与 Agent 接手手册

本仓库是 `https://stock.peekabo.cc` 的代码、文章和自动化定义的唯一 GitHub 备份入口。新服务器或新 Agent 应先阅读 `AGENTS.md`，再执行本手册。

## 1. 已纳入版本库

- Astro 网站源码、文章、测试与构建脚本
- `ops/hermes/stock-cron-jobs.json`：14 个 Hermes 定时任务的脱敏、可移植快照
- `ops/hermes/scripts/`：任务依赖的 5 个自建辅助脚本（含 tracker state 原子 JSON 写入器）
- `knowledge/memory/stock-knowledge.jsonl`：长期记忆中股票相关事实的脱敏导出
- `knowledge/memory/manifest.json`：导出数量、脱敏规则和标签概览
- `templates/`：文章和 cron prompt 模板

不会进入 GitHub：API Key、Telegram/GitHub 凭据、Hermes 运行日志、输出、会话数据库、tracker 实时 state。它们必须在新服务器单独恢复或重新生成。

## 2. 新服务器准备

建议目录保持为：

```bash
mkdir -p ~/projects
git clone https://github.com/brucelau1987cn/stock-research-blog.git ~/projects/stock-research-blog
cd ~/projects/stock-research-blog
```

安装：

- Node.js `>=22.12.0` 与 npm
- Python 3.11+
- Git
- Hermes Agent（最新版）
- 项目任务用到的金融技能：iWencai hithink 系列、mx-data、news-search、xurl

然后：

```bash
npm ci
npm run validate:decisions
npm test
npm run build
```

## 3. 凭据与环境变量

**不要把值写入仓库或发到聊天。** 在新服务器 SSH 终端中配置 Hermes `~/.hermes/.env` / `hermes auth`：

- Hermes 默认模型提供商凭据
- GitHub push 凭据（推荐 SSH key 或 Git credential helper；远端 URL 不得嵌 token）
- Telegram bot / gateway 凭据
- iWencai 双 Key（由 `iwencai_runner.py` 轮询）
- 妙想 mx-data / mx-search / mx-xuangu Key
- X/Twitter xurl 认证（Serenity 任务使用）

具体变量名以各技能的 `required_environment_variables` 和新服务器的 Hermes 文档为准，不在文档中记录值。

## 4. 恢复辅助脚本

```bash
mkdir -p ~/.hermes/scripts
cp ops/hermes/scripts/*.py ~/.hermes/scripts/
chmod 700 ~/.hermes/scripts/*.py
```

`serenity_persist.py` 需要原服务器的 Serenity 缓存/游标才能无缝增量延续；若不迁移 state，它会按脚本自身逻辑重新建立游标。迁移前应另做加密的私有 state 备份。

## 5. 恢复定时任务

`ops/hermes/stock-cron-jobs.json` 是**声明式备份，不可直接覆盖** `~/.hermes/cron/jobs.json`。原因：Hermes 会维护运行状态、来源聊天、下次执行时间等内部字段。

恢复原则：

1. 用 `hermes cron create`、`/cron` 或 cronjob 工具逐项创建。
2. 将 `${STOCK_SITE_DIR}` 替换为新服务器仓库绝对路径，将 `${HOME}` 替换为新用户 HOME。
3. 所有任务 `model/provider/base_url` 保持 `null`，跟随 Hermes 默认模型。
4. 重新绑定 delivery：`origin` 类任务需绑定新的 Telegram 对话；`local` 类任务只保存本地输出。
5. 创建后执行 `hermes cron list --all` 核对名称、时区、schedule、workdir、skills 和 toolsets。
6. 先暂停写入型任务，逐个手动试跑；确认构建、push、线上部署均正常后再恢复全部任务。

当前任务概览：

| 类别 | 任务 |
|---|---|
| Serenity | 工作日 09:10 BJT 抓取并更新月度专栏 |
| A 股市场 | 工作日 17:30 BJT 刷新 market-pulse |
| A 股个股 | 7 只股票工作日每日两次跟踪，时间错峰 |
| NU | 盘前 21:00、盘中 23:30、盘后次日 06:00 BJT |
| 美股周检 | 周六 10:00 BJT |
| FFAI | 周二至周六 06:00 BJT 盘后复盘 |

精确 prompt 和 schedule 以导出的 JSON 为准。

## 6. 恢复脱敏股票知识

`knowledge/memory/stock-knowledge.jsonl` 是可移植的历史股票事实，不包含原数据库 fact_id、URL、社交账号、邮箱、手机号或凭据。新 Agent 可以逐行导入 holographic memory：

```bash
python3 - <<'PY'
import json, subprocess
from pathlib import Path
for line in Path('knowledge/memory/stock-knowledge.jsonl').read_text().splitlines():
    row = json.loads(line)
    subprocess.run([
        'recall', 'add', row['content'], row['category'], ','.join(row['tags'])
    ], check=True)
PY
```

导入前先确认 `hermes memory status` 显示 holographic 可用。重复导入可能产生重复事实；应以 `source_id` 建立自己的导入日志，或只执行一次。原始数据库里的 HRR 向量和实体关系不会直接迁移，导入后由新 memory provider 重新建立。

重新导出最新知识：

```bash
python3 scripts/export_stock_knowledge.py
```

## 7. 运行状态（不进 Git）

如需无缝接续，在停旧服务器后、启新服务器前，通过加密通道备份：

- `~/.hermes/state/*_tracker.json`
- `~/.hermes/state/*_tracker_facts.jsonl`
- Serenity 脚本使用的缓存和 since_id 文件
- Hermes holographic memory 数据库（如新 Agent 也要继承长期事实）
- 必要的 Hermes profile / gateway 配置

不要上传这些文件到公开或普通 GitHub 仓库，因为可能包含用户 ID、历史内容或认证上下文。

## 8. 切换服务器顺序

1. 暂停旧服务器所有写入型 cron，防止双写。
2. 确认旧仓库工作区 clean，并把最后提交推到 GitHub。
3. 导出最新 cron 快照：`python3 scripts/export_hermes_stock_ops.py`，提交并推送。
4. 通过加密通道迁移凭据与必要 state。
5. 新服务器完成 clone、依赖安装、三项验证。
6. 恢复 cron，但先保持暂停。
7. 手动试跑一个只读任务、一个 A 股写入任务、一个美股写入任务。
8. 检查 GitHub 新提交与线上 `https://stock.peekabo.cc`。
9. 新服务器逐项 resume；确认旧服务器 scheduler/gateway 已停止。

## 9. Agent 工作规则

- 修改结构化文章必须遵守 `AGENTS.md` 的 decision contract。
- 修改前 `git pull --ff-only`，工作区不干净时不得覆盖其他 Agent 的工作。
- 写入后必须运行：`npm run validate:decisions && npm test && npm run build`。
- push 后需检查 GitHub 远端；涉及页面变化时还要核验线上域名。
- 禁止把最新文章编辑时间冒充行情时间。
- 禁止在输出、commit、remote URL 或文档中写入明文凭据。

## 10. 更新备份

定时任务有增删改后运行：

```bash
python3 scripts/export_hermes_stock_ops.py
python3 scripts/export_stock_knowledge.py
git add ops/hermes knowledge/memory scripts/export_hermes_stock_ops.py scripts/export_stock_knowledge.py docs/MIGRATION.md
git commit -m "chore: refresh Hermes stock automation backup"
git push origin main
```

导出器会去除聊天 ID、运行时字段和模型锁定，并对常见 token / secret 形态做阻断检查。
