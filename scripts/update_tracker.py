import json
import re
import os
from datetime import datetime

def update():
    # 1. Today's data
    ticker = "600438.SH"
    name = "通威股份"
    price = 11.96
    pct = -2.367347
    volume = 84241081.0
    amount = 1035293247.52
    turnover_rate = 1.871
    amplitude = 6.693878
    open_p = 12.24
    high_p = 12.77
    low_p = 11.95
    profit_ratio = 0.0
    trapped_ratio = 100.0
    avg_cost = 17.28
    
    # Capital flows
    main_net = -11222350.95
    big_net = 27108793.64
    mid_net = 21296714.56
    small_net = -48405508.20
    main_position_pct = -1.083978
    
    # Margin (T-1, i.e. 6/25)
    margin_net_buy = 2.2114 # in million
    margin_balance = 2.434 # in billion
    margin_note = "6月25日融资净买入221.14万元，两融余额24.39亿元，低于近一年20%分位数"
    
    # Calculate 5-day average volume
    # Past volumes (excluding today):
    # 6/25: 58,444,910
    # 6/24: 53,442,855
    # 6/23: 61,273,004
    # 6/22: 80,523,860
    # 6/18: 50,334,167
    avg_5d_vol = (58444910.0 + 53442855.0 + 61273004.0 + 80523860.0 + 50334167.0) / 5.0
    vol_ratio_5d = volume / avg_5d_vol # 84241081 / 60807759.2 = 1.385
    
    # Sector index (885531.TI)
    sector_pct = -1.7822
    
    # Check trigger rules
    triggers = []
    # 1. Price break key level:
    # 12.0 is the upper limit of the "进一步下沿" (11.0-12.0) and a psychological level
    if price < 12.0:
        triggers.append("rule1_price_key_level_close_cross: 收盘价 11.96 元跌破 12.0 元整数心理位及进一步下沿区间上限")
    # 2. Daily change > 3%
    if abs(pct) > 3.0:
        triggers.append(f"rule2_daily_move_gt_3pct: 单日跌幅 {pct:.2f}% > 3%")
    # 3. Volume > 1.5x
    if vol_ratio_5d > 1.5:
        triggers.append(f"rule3_volume_gt_1_5x: 今日成交量为 5 日均量 {vol_ratio_5d:.2f}x > 1.5x")
    # 4. Announcements - none today
    # 5. Margin net buy absolute > 5 million
    # (Since T-1 margin was 2.21m, it's not > 5m)
    # 6. Sector move > 4%
    if abs(sector_pct) > 4.0:
        triggers.append(f"rule6_sector_move_gt_4pct: 板块单日波动 {sector_pct:.2f}% > 4%")
    # 7. Chip trigger
    # profit_ratio has gone from 2.0% (6/25 close) to 0.0% (6/26 close)
    # is it continuous? Previous history close: 6/24 close was 1.1%, 6/25 close was 2.0%. So not continuous decline of multiple days.
    
    triggered = len(triggers) > 0
    trigger_summary = "、".join([t.split(": ")[1] for t in triggers]) if triggered else "盘后例行同步（筹码分布简报）"
    
    # State update
    state = {
        "as_of": "2026-06-26T15:28:00+08:00",
        "session": "afternoon_close",
        "ticker": ticker,
        "name": name,
        "price": price,
        "pct": pct,
        "volume": volume,
        "amount_raw": amount,
        "turnover_rate": turnover_rate,
        "amplitude": amplitude,
        "open": open_p,
        "high": high_p,
        "low": low_p,
        "chip_distribution": {
            "profit_ratio": profit_ratio,
            "trapped_ratio": trapped_ratio,
            "avg_cost": avg_cost,
            "as_of": "2026-06-26 15:28 BJT",
            "prev_profit_ratio": 2.0,
            "trend": "extreme_trapped_continuing",
            "chip_triggered": False,
            "chip_trigger_reason": ""
        },
        "main_net_wan": main_net / 10000.0,
        "big_net_wan": big_net / 10000.0,
        "mid_net_wan": mid_net / 10000.0,
        "small_net_wan": small_net / 10000.0,
        "main_position_pct": main_position_pct,
        "margin_net_buy_million": margin_net_buy,
        "margin_balance_billion": margin_balance,
        "margin_note": margin_note,
        "triggered": triggered,
        "reasons": triggers,
        "verdict": f"6/26 下午收盘 11.96 元（-2.37%），主力大单流入 +2710.88 万元，散户流出 -4840.55 万元，筹码获利盘 0.0%，套牢盘 100%，跌破 12.0 元整数支撑。"
    }
    
    # Write to twgf_tracker.json
    with open("/root/.hermes/state/twgf_tracker.json", "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print("Updated twgf_tracker.json")
    
    # Write to facts JSONL
    # Check if this fact already exists for today's afternoon run
    fact_entry = {
        "as_of": "2026-06-26T15:28:00+08:00",
        "ticker": ticker,
        "name": name,
        "price": price,
        "pct": pct,
        "volume": volume,
        "amount_raw": amount,
        "turnover_rate": turnover_rate,
        "amplitude": amplitude,
        "open": open_p,
        "high": high_p,
        "low": low_p,
        "triggered": triggered,
        "trigger_reasons": triggers,
        "chip_profit_ratio": profit_ratio,
        "chip_trapped_ratio": trapped_ratio,
        "chip_avg_cost": avg_cost,
        "chip_prev_profit_ratio": 2.0,
        "chip_trend": "extreme_trapped_continuing",
        "main_net": main_net,
        "big_net": big_net,
        "mid_net": mid_net,
        "small_net": small_net,
        "run_context": "下午盘后 (15:28 BJT 收盘)",
        "summary": state["verdict"],
        "sources": ["hithink-astock-selector", "hithink-market-query", "hithink-event-query", "mx-data", "mx-search"]
    }
    
    facts_file = "/root/.hermes/state/twgf_tracker_facts.jsonl"
    with open(facts_file, "a") as f:
        f.write(json.dumps(fact_entry, ensure_ascii=False) + "\n")
    print("Appended to facts JSONL")

update()
