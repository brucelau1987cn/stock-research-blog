#!/usr/bin/env bash
# market_pulse_refresh.sh
# 收盘后抓取核心 A 股标的 + 板块 ETF 涨幅 + 宏观背景，合并为
# src/data/market-pulse.json，供 stock-analysis.astro 在 build 时读取。
#
# 触发: cron 30 15 * * 1-5  (A 股工作日 15:30 BJT)
# 数据源:
#   1. mx-data (东方财富)  - 个股最新价/涨跌幅
#   2. hithink-etf-selector - 板块 ETF 涨幅前 5
#   3. hithink-macro-query  - CPI / PMI 同比
# 输出:
#   /root/projects/stock-research-blog/src/data/market-pulse.json
set -euo pipefail

REPO="/root/projects/stock-research-blog"
OUT="$REPO/src/data/market-pulse.json"
LOG="/root/.openclaw/workspace/mx_data/output/market_pulse_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG")"

# load env (Hermes auto-sources .bashrc but cron doesn't, so be explicit)
set +u
# Use bash's own parser (handles quotes correctly). Skip non-assignment lines.
if [[ -f /root/.hermes/.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source /root/.hermes/.env
  set +a
fi
set -u

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
log "=== market_pulse_refresh started ==="
log "OUT: $OUT"

# Serenity 主线赛道分组（sector key + 显示名 + 票列表）
# 7 组：CPO光模块 / TGV玻璃基板 / 人形机器人 / 封测ASIC / 电子特气+外延片 / 半导体材料 / 半导体设备
SECTORS_JSON='{
  "cpo": {"label": "🔦 CPO / 光模块", "stocks": [
    {"name": "新易盛",    "code": "300502"},
    {"name": "中际旭创",  "code": "300308"},
    {"name": "天孚通信",  "code": "300394"},
    {"name": "光库科技",  "code": "300620"}
  ]},
  "tgv": {"label": "🧊 TGV / 玻璃基板", "stocks": [
    {"name": "沃格光电",  "code": "603773"}
  ]},
  "robot": {"label": "🤖 人形机器人", "stocks": [
    {"name": "绿的谐波",  "code": "688017"}
  ]},
  "packaging": {"label": "🔧 ASIC 封测", "stocks": [
    {"name": "通富微电",  "code": "002156"},
    {"name": "长电科技",  "code": "600584"}
  ]},
  "gas_epi": {"label": "💨 电子特气 + 外延片", "stocks": [
    {"name": "雅克科技",  "code": "002409"},
    {"name": "昊华科技",  "code": "600378"},
    {"name": "中船特气",  "code": "688146"},
    {"name": "金宏气体",  "code": "688106"}
  ]},
  "mat": {"label": "🧪 半导体材料", "stocks": [
    {"name": "立昂微",    "code": "605358"},
    {"name": "三安光电",  "code": "600703"},
    {"name": "云南锗业",  "code": "002428"},
    {"name": "沪硅产业",  "code": "688126"}
  ]},
  "equip": {"label": "⚙️ 半导体设备", "stocks": [
    {"name": "北方华创",  "code": "002371"},
    {"name": "拓荆科技",  "code": "688072"}
  ]}
}'
export SECTORS_JSON  # fetch_all_quotes 的子 python 用

# ---------- helper: pull all Serenity core A-share prices via hithink-astock-selector ----------
# 改用 iWencai 的原因：mx-data 9 连击就触发 per-IP 限流，iWencai 不限流且字段更全
# 关键发现：把 "A股" 放最前 + 票名放后面，可以让 iWencai 1 次返回 18 只
# 17 字段: 收盘价 / 涨跌幅 / 振幅 / 换手率 / 成交额 / 成交量 / 最高最低 / 开盘
# usage: fetch_all_quotes
# echoes JSON array of {name, code, price, pct, sector, sector_label, amplitude, turnover, amount_yi}
fetch_all_quotes() {
  # 把 SECTORS_JSON 展平为 name 列表
  local names
  names=$(echo "$SECTORS_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); [print(s['name']) for k in d for s in d[k]['stocks']]")
  local query="A股 收盘价 涨跌幅 振幅 换手率 成交额 成交量 ${names}"

  local out
  if out=$(python3 ~/skills/hithink-astock-selector/scripts/cli.py --query "$query" --limit 20 2>/dev/null); then
    echo "$out" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if not d.get('success') or not d.get('datas'):
  sys.exit(1)
# 读 SECTORS_JSON（从 stdin 第 2 行以后是 SECTORS_JSON 内容，用环境变量传更稳）
import os
sectors = json.loads(os.environ['SECTORS_JSON'])
# 反查 name -> (sector, sector_label)
name_to_meta = {}
for k, v in sectors.items():
  for s in v['stocks']:
    name_to_meta[s['name']] = (k, v['label'], s['code'])
out = []
for r in d['datas']:
  short = r.get('股票简称', '')
  meta = name_to_meta.get(short)
  if not meta:
    # iWencai 多返回了我们不关心的票，跳过
    continue
  sec_key, sec_label, code = meta
  price = r.get('收盘价[20260612]') or r.get('最新价') or '—'
  pct = r.get('涨跌幅[20260612]') or r.get('最新涨跌幅')
  if pct is None or pct == '':
    pct = '—'
  else:
    pct = f'{float(pct):.4f}'
  out.append({
    'name': short, 'code': code, 'price': str(price), 'pct': pct,
    'sector': sec_key, 'sector_label': sec_label,
    'amplitude': r.get('振幅[20260612]'),
    'turnover': r.get('换手率[20260612]'),
    'amount_yi': round(float(r.get('成交额[20260612]') or 0) / 1e8, 2) if r.get('成交额[20260612]') else None,
  })
print(json.dumps(out, ensure_ascii=False))
"
    return
  fi
  echo '[]'
}

# ---------- helper: pull top-5 sector ETFs via hithink-etf-selector ----------
fetch_top_etfs() {
  local query="$1" count="$2"
  python3 ~/skills/hithink-etf-selector/scripts/cli.py \
    --query "$query" --limit "$count" 2>/dev/null \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
if not d.get("success"):
    print("[]")
    sys.exit(0)
out = []
for row in d.get("datas", []):
    out.append({
        "code": row.get("基金代码", ""),
        "name": row.get("基金简称", "") or row.get("基金扩位简称", ""),
        "price": row.get("最新收盘价", ""),
        "pct": row.get("最新涨跌幅"),
    })
print(json.dumps(out, ensure_ascii=False))
'
}

# ---------- helper: pull one macro indicator ----------
fetch_macro() {
  local query="$1"
  python3 ~/skills/hithink-macro-query/scripts/cli.py \
    --query "$query" --limit 1 2>/dev/null \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
if not d.get("success"):
    print({"value": None, "date": None, "unit": ""})
    sys.exit(0)
rows = d.get("datas", [])
if not rows:
    print({"value": None, "date": None, "unit": ""})
    sys.exit(0)
r = rows[0]
print(json.dumps({
    "value": r.get("指标值"),
    "date": r.get("时间"),
    "unit": r.get("单位", ""),
    "name": r.get("指标") or r.get("macro_name", ""),
}, ensure_ascii=False))
'
}

log "fetching core A-share quotes via iWencai (1 call for 18 stocks)..."
# 把 SECTORS_JSON 暴露到 fetch_all_quotes 的子 python 进程
export SECTORS_JSON
STOCKS_JSON=$(fetch_all_quotes)
if [[ "$STOCKS_JSON" == "[]" || -z "$STOCKS_JSON" ]]; then
  log "ERROR: fetch_all_quotes returned empty array, aborting"
  exit 1
fi
N_STOCKS=$(echo "$STOCKS_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
log "  → $N_STOCKS stocks fetched"

log "fetching sector ETF top gainers..."
ETF_UP_JSON=$(fetch_top_etfs "今日场内ETF涨幅前5" 5)
log "  → $(echo "$ETF_UP_JSON" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)),"rows")')"

log "fetching sector ETF top losers..."
ETF_DN_JSON=$(fetch_top_etfs "今日场内ETF跌幅前5" 5)
log "  → $(echo "$ETF_DN_JSON" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)),"rows")')"

log "fetching macro: latest CPI YoY..."
CPI_JSON=$(fetch_macro "最近一期CPI同比")
log "  → $CPI_JSON"

log "fetching macro: latest PMI..."
PMI_JSON=$(fetch_macro "最近一期制造业PMI")
log "  → $PMI_JSON"

log "writing $OUT"
python3 - <<PY > "$OUT"
import json
data = {
  "as_of": "$(date '+%Y-%m-%d %H:%M:%S %Z')",
  "trading_day": "$(date '+%Y-%m-%d')",
  "stocks": json.loads('''$STOCKS_JSON'''),
  "etf_top": json.loads('''$ETF_UP_JSON'''),
  "etf_bottom": json.loads('''$ETF_DN_JSON'''),
  "macro": {
    "cpi_yoy": json.loads('''$CPI_JSON'''),
    "pmi": json.loads('''$PMI_JSON'''),
  },
}
print(json.dumps(data, ensure_ascii=False, indent=2))
PY

log "=== refresh complete ==="
log "snapshot:"
cat "$OUT" | head -40
echo

# 守门：如果超过 30% 的票数据是 '—'，不 commit（避免限流期间刷出空数据覆盖上次真值）
TOTAL=$(python3 -c "import json; d=json.load(open('$OUT')); print(len(d.get('stocks',[])))" 2>/dev/null || echo 0)
EMPTY=$(python3 -c "import json; d=json.load(open('$OUT')); print(sum(1 for s in d.get('stocks',[]) if s.get('price')=='—'))" 2>/dev/null || echo 0)
if [[ "$TOTAL" -gt 0 ]]; then
  EMPTY_PCT=$((EMPTY * 100 / TOTAL))
  log "data quality: $EMPTY/$TOTAL stocks missing ($EMPTY_PCT%)"
  if [[ "$EMPTY_PCT" -ge 30 ]]; then
    log "ABORT: too many missing data points (≥30%), skip commit to avoid overwriting good snapshot"
    exit 0
  fi
fi

log "now committing + pushing..."
cd "$REPO"
git add src/data/market-pulse.json
if git diff --cached --quiet; then
  log "no change in market-pulse.json, skip commit"
  exit 0
fi
git commit -m "chore(pulse): refresh market-pulse snapshot $(date '+%Y-%m-%d %H:%M')" >/dev/null
git push >/dev/null 2>&1 || log "WARN: git push failed (non-fatal)"
log "done."
