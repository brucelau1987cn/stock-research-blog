# A股股票研究笔记

Bruce 的 A 股股票中短线研究博客，记录股票观察队列、盘中修正、关键价位、持仓动作和复盘修正。

## 本地开发

```bash
npm install
npm run dev
```

## 构建

```bash
npm run build
```

Cloudflare Pages 构建配置：

- Build command: `npm run build`
- Build output directory: `dist`
- Node.js version: `22.12.0` 或更高

正式域名：<https://stock.peekabo.cc>

## 维护与迁移

- Agent 自动维护规则：[`AGENTS.md`](./AGENTS.md)
- 新服务器迁移、定时任务恢复与安全备份：[`docs/MIGRATION.md`](./docs/MIGRATION.md)
- 刷新 Hermes 自动化备份：`python3 scripts/export_hermes_stock_ops.py`
- 刷新脱敏股票长期知识：`python3 scripts/export_stock_knowledge.py`
