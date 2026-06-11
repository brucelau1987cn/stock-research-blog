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

# ---------- helper: pull a single A-share price via mx-data ----------
# usage: fetch_quote NAME CODE
# echoes "PRICE PCT" or "— —" on failure
# Sample output line: "| 2026-06-11 21:01 | 139.46 | -10% |"
fetch_quote() {
  local name="$1" code="$2"
  local out line
  if out=$(python3 ~/.hermes/skills/mx-data/scripts/mx_data.py "${name} ${code} 最新价 涨跌幅" 2>/dev/null); then
    # look for the data row "| date | price | pct% |"
    line=$(printf '%s\n' "$out" | grep -E '^\| [0-9]{4}-[0-9]{2}-[0-9]{2}' | tail -1)
    if [[ -n "$line" ]]; then
      # token 2 = price, token 3 = pct (strip %)
      local price pct
      price=$(printf '%s' "$line" | awk -F'|' '{gsub(/ /,"",$3); print $3}')
      pct=$(printf '%s' "$line" | awk -F'|' '{gsub(/[ %]/,"",$4); print $4}')
      if [[ -n "$price" && -n "$pct" ]]; then
        printf '%s %s\n' "$price" "$pct"
        return
      fi
    fi
  fi
  printf '— —\n'
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

log "fetching core A-share quotes..."
declare -A STOCKS=(
  ["沃格光电"]="603773"
  ["绿的谐波"]="688017"
  ["新易盛"]="300502"
  ["中际旭创"]="300308"
  ["天孚通信"]="300394"
  ["光库科技"]="300620"
  ["通富微电"]="002156"
  ["长电科技"]="600584"
)

STOCKS_JSON='['
first=1
for name in 沃格光电 绿的谐波 新易盛 中际旭创 天孚通信 光库科技 通富微电 长电科技; do
  code="${STOCKS[$name]}"
  read -r price pct < <(fetch_quote "$name" "$code")
  log "  $name($code) → $price / $pct%"
  if (( first )); then first=0; else STOCKS_JSON+=','; fi
  STOCKS_JSON+="{\"name\":\"$name\",\"code\":\"$code\",\"price\":\"$price\",\"pct\":\"$pct\"}"
done
STOCKS_JSON+=']'

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
