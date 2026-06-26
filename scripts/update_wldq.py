import json
import re
import os
from datetime import datetime

def main():
    md_path = "/root/projects/stock-research-blog/src/content/blog/20260612-600580-wldq.md"
    state_path = "/root/.hermes/state/wldq_tracker.json"
    facts_path = "/root/.hermes/state/wldq_tracker_facts.jsonl"
    
    # 6/26 close data
    price = 31.89
    pct = -4.976162
    volume = 44548985.0
    amount = 1444669316.93
    turnover_rate = 2.86
    amplitude = 4.856973
    open_p = 33.49
    high_p = 33.49
    low_p = 31.86
    profit_ratio = 0.0
    trapped_ratio = 100.0
    avg_cost = 39.12
    
    # Capital
    dde_big = -101520043.06
    mid_net = -146994285.73
    small_net = 248514328.79
    main_net = -2381869.95
    main_change_pct = -0.164873
    
    # Margin (6/25 T-1)
    margin_balance = 2465280544.0
    margin_net_buy = -35498200.0
    short_margin_balance = 12328700.0
    
    # Volumes for 5-day average (excluding 6/26)
    # 6/25: 53,393,976
    # 6/24: 30,954,805
    # 6/23: 43,183,559
    # 6/22: 48,861,884
    # 6/18: 54,544,616
    avg_5d_vol = (53393976.0 + 30954805.0 + 43183559.0 + 48861884.0 + 54544616.0) / 5.0
    ratio_to_5d_avg = volume / avg_5d_vol # 44548985 / 46187768 = 0.9645
    
    # Key levels
    stop_level = 28.00
    buy_low = 30.50
    buy_mid = 33.50
    buy_high = 36.50
    reduce_1 = 40.60
    reduce_2 = 45.70
    breakout = 50.80
    
    # Distances to key levels (relative to current price)
    dist_stop = (price - stop_level) / stop_level * 100 # +13.89%
    dist_buy_low = (price - buy_low) / buy_low * 100 # +4.56%
    dist_buy_mid = (buy_mid - price) / price * 100 # +5.05%
    
    # Triggers check
    triggers = []
    # R1: price breaks key levels
    # Since 31.89 is below 33.50, and yesterday was 33.56 (above 33.50), it crossed 33.50.
    triggers.append("R1: 价格跌破 33.5 元中位支撑线 (收盘报 31.89 元，距 -5.05%)")
    # R2: Daily change absolute > 3%
    if abs(pct) > 3.0:
        triggers.append(f"R2: 单日收盘大跌 {pct:.2f}%，涨跌幅绝对值 > 3% 阈值 (收盘报 31.89 元)")
    # R3: Volume > 1.5x of 5d avg
    if ratio_to_5d_avg > 1.5:
        triggers.append(f"R3: 今日成交量为 5 日均量 {ratio_to_5d_avg:.2f}x > 1.5x")
    # R5: Margin absolute > 5 million
    if abs(margin_net_buy) > 5000000.0:
        triggers.append(f"R5: T-1 (6/25) 融资净偿还 {-margin_net_buy/10000.0:.2f} 万元，绝对值 > 500 万元")
    # R7: Chip trigger (profit ratio decline to <1% and consecutive drop)
    # 6/24: 2.3% -> 6/25: 0.3% -> 6/26: 0.0%
    triggers.append("R7 筹码触发: 获利盘连续下跌且低于 1% (6/24 2.3% -> 6/25 0.3% -> 6/26 0.0%)，极端套牢比例达 100.0%")
    
    triggered = True
    
    # Read original MD
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
        
    # 1. Update Frontmatter
    md_content = re.sub(
        r"title: '.*?'",
        f"title: '600580 卧龙电驱：06/26 收盘 31.89 元 (-4.98%) 支撑破位'",
        md_content
    )
    md_content = re.sub(
        r"updatedDate: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00",
        "updatedDate: 2026-06-26T15:38:00+08:00",
        md_content
    )
    new_desc = "最新结论：6/26 收盘跌至 31.89 元（-4.98%）失守 33.5 元支撑，新低探至 31.86 元。收盘获利盘降至 0.0% 触发 R7 筹码警报，T-1 融资大额净流出 3549.82 万元（R5）形成资金共振。评级下调为“空仓等待”，暂缓任何左侧加仓，关注 30.50 元下沿防守。"
    md_content = re.sub(
        r"description: '.*?'",
        f"description: '{new_desc}'",
        md_content
    )
    
    # 2. Update Tracking Records
    tracking_block = f"""### 跟踪 2026-06-26 15:38 BJT

**触发原因：** **R1 跌破中位支撑线**（收盘跌至 31.89 元，正式跌破 33.50 元中位支撑线）；**R2 单日涨跌幅 |−4.98%| > 3% 阈值**（昨收 33.56 元，今日收盘 31.89 元，跌幅 4.98%）；**R5 融资净买入绝对值 > 500 万元**（T-1 6/25 披露融资净偿还 3549.82 万元）；**R7 筹码正式触发**（获利盘 6/24 收盘 2.3% → 6/25 0.3% → 6/26 收盘 0.0%，形成连续两期下跌且低于 1% 极端红线）。多重利空共振，中位防守确认失守，评级维持“空仓等待”。

**📊 盘面数据快照：**
- **收盘价 / 盘中最新价**：**31.89 元**（-4.98%，iWencai 口径）
- **资金与动能**：量比 **0.96x**，换手率 **2.86%**，主力大单净流入 **-1.02 亿元**（散户净买入 2.49 亿元）
- **收盘/盘中获利盘**：**0.00%**（获利盘 6/24 2.3% → 6/25 0.3% → 6/26 收盘 0.0%，连续三日下跌，套牢盘 100.0%，筹码全数套牢，结构极度冰冻）

**🛡 当前对峙边界：**
- 🔼 **直属攻击线**（上方阻力）：**33.50 元**（距 +5.05%，原中位支撑线转化为第一阻力位）
- 🔽 **直属防守线**（下方支撑）：**30.50 元**（距 +4.56%，建仓下沿支撑）
- 🚨 **风控/止损底线**：**28.00 元**（距 +13.89%，说明风控状态）

**🎯 条件执行计划 (If-Then Plan)：**
- **IF 向上**：若日内大幅放量（量比 > 1.5x）重新站稳 33.50 元攻击线 → 考虑维持“右侧观望”评级并观察资金流入持续度；否则不主动加仓。
- **IF 向下**：若收盘实质性跌破 30.50 元防守线 → 离场观望，防范向 28.00 元风控底线寻底的风险。"""
    
    # Locate tracking records
    pattern_track = r"(## 跟踪记录\s*\n\s*> 跟踪段按时间倒序排列（最新在上）。右侧快捷栏按日期分组、当日多个跟踪段自动合并为一格，徽章显示数量，点击跳到当日最新一条。\s*\n\s*)(### 跟踪 .*?)(?=\n\n## 结论先行)"
    
    md_content = re.sub(
        pattern_track,
        f"\\1{tracking_block}",
        md_content,
        flags=re.DOTALL
    )
    
    # 3. Update 结论先行
    new_conclusion = """卧龙电驱**6/26 收盘触发 R1（跌破 33.5 元中位支撑线）、R2（单日跌幅 4.98% > 3%）以及 R7（筹码连续下跌且获利盘 0.0% 低于 1% 红线）共振，同时 T-1（6/25）融资净偿还 3549.82 万元触发 R5 融资大额流出**。最新收盘价报 31.89 元，较昨日下跌 1.67 元（-4.98%），盘中最低触及 31.86 元。**多信号利空共振确认**：33.5 元中位支撑线确认告破，筹码获利盘缩水至 0.0% 的历史冰点，套牢盘高达 100.0%，融资杠杆资金持续流出（T-1 融资净偿还 3549.82 万元，融资余额降至 24.65 亿元），主力大单流出达 1.02 亿元，小单接盘（2.49 亿元）特征明显。**评级维持“空仓等待”**，严禁任何形式的左侧买入或抄底。

- 短线（1–3 天）：**支撑失效，向下寻求 30.50 元下沿防守**。6/22 以来连续 5 根阴线累计跌幅达 **-14.0%**；6/26 最低 31.86 元，半年新低重置为 31.86 元。全天成交量 4455 万股，量比 0.96x 呈现温和缩量破位阴跌，主力大单净流出 1.02 亿元，散户小单涌入 2.49 亿元接盘，融资盘持续大额偿还，绝对不可左侧抄底。
- 波段（2–6 周）：33.50 元中位线由支撑转化为直属攻击压力线。31.89 元距 30.50 元防守线仅 +4.56%，距 28.00 元止损位 +13.89%。由于 33.50 元已失守，评级下调为“空仓等待”，等待在 30.50 元或更低防守位止跌企稳的明确资金转正信号。
- 减仓节奏：40.6 / 45.7 / 50.8 三档关键位距离已被大幅拉开（-27.31% / -43.31% / -59.30%），当前无任何减仓触发。
- 止损：跌破 28.00 元清仓底线不变。
- 筹码触发：获利盘 0.0% 续刷极端，且形成连续下跌（6/24 2.3% → 6/25 0.3% → 6/26 0.0%），符合严格规则 7 筹码触发条件，弱势结构达极端。"""
    
    md_content = re.sub(
        r"(## 结论先行\s*\n\s*)(.*?)(?=\n\n## 关键价位)",
        f"\\1{new_conclusion}",
        md_content,
        flags=re.DOTALL
    )
    
    # 4. Update 关键价位
    new_levels_note = f"""> **2026-06-26 15:38 盘后收盘更新（本次修订）：** 31.89 元收盘（-4.98%，昨收 33.56 跌 1.67 元）触发 R1（跌破 33.5 元中位支撑线）与 R2（单日跌幅 > 3%）；T-1 6/25 融资数据披露，融资净偿还 **3549.82 万元**（绝对值 > 500 万）触发 R5；6/26 收盘获利盘降至 **0.0%** 且实现 6/24(2.3%) -> 6/25(0.3%) -> 6/26(0.0%) 的连续下跌，严格触发 R7 筹码规则。**关键位档位不变，33.50 由支撑转阻力位，下行防御直指 30.50 元。**"""
    
    md_content = re.sub(
        r"(> \*\*2026-06-26 11:38 盘中更新（本次修订）：\*\* .*?)(?=\n\n\| 性质 \| 价位区间 \|)",
        f"{new_levels_note}",
        md_content,
        flags=re.DOTALL
    )
    
    # Update new low in the table
    md_content = re.sub(
        r"\| 半年新低 \| 32\.01 \| 2026-06-26 盘中最低（原 33\.31 已被跌穿） \|",
        r"| 半年新低 | 31.86 | 2026-06-26 最低（原 33.31/32.01 已被跌穿） |",
        md_content
    )
    
    # 5. Update 近1个月行情
    new_one_month = """- **6/26 收盘 15:38 BJT 31.89 元（-4.98%）**，**正式跌破 33.5 中位支撑线并触发 R1、R2、R5、R7 共振**；现价距 30.50 建仓下沿仅 +4.56%，距 28.00 止损位 +13.89%
- **下行破位，连收 5 阴续创半年新低**：6/22 跌 3.40% → 6/23 跌 2.87% → 6/24 跌 0.20% → 6/25 跌 3.40% → 6/26 跌 4.98%，5 连阴累计跌幅达 **-14.0%**；6/26 最低 31.86 元正式跌破 6/25 新低 33.31，半年新低重置为 31.86 元
- 6/26 全天成交量 **4455 万股**（近 5 日均量 **4619 万股**，量比约 **0.96x**，未触发 1.5x 放量，阴跌不言底）
- 6/26 全天成交额 **14.45 亿**，换手率 **2.86%**，振幅 **4.86%**
- 6/26 主力大单净流出 **-1.02 亿元**（主力增仓占比 -0.16%），中单净买入 -1.47 亿元，小单净买入 **+2.49 亿元**（主力及中单继续派发，小单被动承接）
- **T-1 6/25 融资数据披露**：融资净买入 **-3549.82 万元**（大额净偿还，绝对值 35.498 百万 > 500 万，触发 R5）；融资余额降至 **24.65 亿元**（低于近一年 40% 分位），融券余额降至 **1232.87 万元**（低于近一年 10% 分位），说明杠杆资金撤离态度坚决
- **筹码获利盘 0.0% 续创极端（触发 R7）**：获利盘 6/24 2.3% → 6/25 0.3% → 6/26 0.0%，连续下跌且跌破 1% 极端红线，套牢盘 100.0% 创历史极值
- 6/26 资讯与专利：公司于 6/26 获得实用新型专利授权“一种一体化关节模组及机器人”（专利号 CN202521426400.9），但在基本面破位下该技术主题未起催化作用"""

    md_content = re.sub(
        r"(## 近1个月行情\s*\n\s*)(.*?)(?=\n\n## 近半年走势（背景）)",
        f"\\1{new_one_month}",
        md_content,
        flags=re.DOTALL
    )
    
    # 6. Update 近半年走势（背景）
    md_content = re.sub(
        r"- 区间涨跌幅 \*\*-22\.98%\*\*（2025-12-12 → 2026-06-26，跌势呈加速状态）",
        "- 区间涨跌幅 **-23.82%**（2025-12-12 → 2026-06-26，跌势呈加速状态）",
        md_content
    )
    md_content = re.sub(
        r"半年高 51\.15 / 半年低 \*\*32\.01——6/26 盘中重置\*\*",
        "半年高 51.15 / 半年低 **31.86——6/26 收盘重置**",
        md_content
    )
    md_content = re.sub(
        r"盘中新低 32\.01 元",
        "收盘新低 31.89 元，盘中新低 31.86 元",
        md_content
    )
    
    # 7. Update 三个风险
    md_content = re.sub(
        r"6/26 跌破 33.50 元中位支撑线，5 连阴累计跌幅 -13.0%",
        "6/26 跌破 33.50 元中位支撑线，5 连阴累计跌幅 -14.0%",
        md_content
    )
    md_content = re.sub(
        r"获利盘仅 0\.1%",
        "获利盘仅 0.0%",
        md_content
    )
    
    # 8. Update 分批买入 / 减仓计划
    new_rating = """**当前评级：空仓等待（正式下调）**。6/26 收盘 31.89 元（-4.98%）正式跌破 33.5 元中位线，触发 R1 与 R2；T-1 (6/25) 融资净偿还 3549.82 万触发 R5 融资大额流出；筹码最新获利盘仅 0.0% 续创极低，套牢盘 100.0% 且形成连续下跌，正式触发 R7 筹码警报。多信号共振均呈弱势极点，原观望带下移，评级由“右侧观望”正式下调为“空仓等待”。后续需等待现价重新站稳 33.50 元阻力位 + 融资扭转为大额净买入 + 筹码获利盘回升至 5% 以上，方可考虑解除空仓状态。"""
    md_content = re.sub(
        r"(\*\*当前评级：空仓等待（正式下调）\*\*.*?)(?=\n\n## 行业 / 基本面锚点)",
        f"{new_rating}",
        md_content,
        flags=re.DOTALL
    )
    
    # 9. Update 行业 / 基本面锚点
    md_content = re.sub(
        r"- \*\*6/26 盘中 11:38 触发 R1（跌破 33\.5 支撑线）、R2（单日跌幅 3\.93% > 3% 阈值）、R7（获利盘 0\.1% 连续下跌且 <1%）\*\*\. 现价 32\.24 元距 30\.50 元仅 \+5\.70%，半年新低重置为 32\.01 元\. 主力大单净流出 5043\.01 万元，小单净流入 1\.49 亿元",
        "- **6/26 收盘触发 R1（跌破 33.5 支撑线）、R2（单日跌幅 4.98% > 3% 阈值）、R7（获利盘 0.0% 连续下跌且 <1%）**。现价 31.89 元距 30.50 元仅 +4.56%，半年新低重置为 31.86 元。主力大单净流出 1.02 亿元，小单净流入 2.49 亿元",
        md_content
    )
    
    # 10. Update 风险点
    new_risks = """- 支撑失效破位重挫：6/26 收盘 31.89 元正式跌破 33.5 元中位支撑线。6/22 以来录得 5 连阴累计跌幅达 -14.0%，半年新低屡次重置（最新 31.86 元），均线呈空头排列，下行寻底风险急剧上升
- 主力持续撤退：6/26 主力大单净流出 1.02 亿元，中单流出，小单涌入接盘 2.49 亿元。散户接盘为主力撤退典型格局
- 融资杠杆资金反向流出：6/25 融资大额净偿还 3549.82 万元（触发 R5 融资流出警报），连续偿还说明杠杆资金做多信心崩塌
- 极端的冰冻筹码结构：最新获利盘仅 0.0% 刷新历史极低点，套牢盘 100.0% 处于全盘套牢状态，市场几乎丧失所有上行动能，严格触发 R7 筹码警报
- 主题催化失效：6/26 虽获得一体化机器人关节模组实用新型专利授权，但在股价单边阴跌破位的悲观情绪中未起到任何提振效果"""
    
    md_content = re.sub(
        r"(## 风险点\s*\n\s*)(.*?)$",
        f"\\1{new_risks}\n",
        md_content,
        flags=re.DOTALL
    )
    
    # Write back to MD file
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print("Updated markdown file successfully.")
    
    # State update
    state = {
        "as_of": "2026-06-26T15:38:00+08:00",
        "ticker": "600580.SH",
        "name": "卧龙电驱",
        "triggered": triggered,
        "trigger_reasons": triggers,
        "session": "afternoon_close",
        "iwencai": {
            "close": price,
            "pct": pct,
            "volume": volume,
            "amount": amount,
            "turnover_rate": turnover_rate,
            "amplitude": amplitude,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "as_of": f"2026-06-26 15:38 BJT (iWencai 收盘价[20260626]={price}, 最新获利={profit_ratio}%)"
        },
        "iwencai_market": {
            "main_net": main_net,
            "big_net": dde_big,
            "mid_net": mid_net,
            "small_net": small_net,
            "main_change_pct": main_change_pct,
            "margin_balance": margin_balance,
            "margin_net_buy": margin_net_buy,
            "short_margin_balance": short_margin_balance,
            "margin_source": "mx-search 6/26 披露 T-1 (6/25) 融资买入1.58亿/偿还1.94亿/净偿还3549.82万/融资余额24.65亿/融券余量36.74万股/融券余额1232.87万",
            "margin_as_of": "T-1/2026-06-25 (mx-search 6/26 披露)",
            "t_minus1_margin_net_buy_note": "T-1 (2026-06-25) 实际融资净买入 -3549.82 万元 (融资净偿还 3549.82 万元)，绝对值超过 500 万流动性阈值，触发规则 5。"
        },
        "iwencai_event": {
            "today_exchange_or_company_announcement": False,
            "summary": "mx-search 6/26 命中：① 6/26 专利授权：公司新获得一项实用新型专利授权“一种一体化关节模组及机器人”（专利号 CN202521426400.9）；② 6/26 两融：6/25 融资净偿还 3549.82 万，余额 24.65 亿，融券余额 1232.87 万；③ 机构持仓：截至 3/31，香港中央结算加仓 1546.86 万股，稀土 ETF 增仓，中证 500ETF 减仓。"
        },
        "mx_data": {
            "price": price,
            "pct": pct,
            "as_of": "2026-06-26 15:38 BJT",
            "support": buy_low,
            "resistance": buy_mid,
            "unavailable": False
        },
        "volume_check": {
            "today_volume": volume,
            "five_day_avg_volume": avg_5d_vol,
            "ratio_to_5d_avg": ratio_to_5d_avg,
            "triggered": ratio_to_5d_avg > 1.5,
            "note": f"6/26 全天成交 {volume/10000.0:.2f} 万股 vs 近 5 日均量 {avg_5d_vol/10000.0:.2f} 万股，全天量比 {ratio_to_5d_avg:.2f}x，未触发 1.5x 阈值。"
        },
        "key_levels": {
            "scaled": {
                "stop": stop_level,
                "buy_low": buy_low,
                "buy_mid": buy_mid,
                "buy_high": buy_high,
                "reduce_1": reduce_1,
                "reduce_2": reduce_2,
                "breakout": breakout
            },
            "original": {
                "stop": 13.8,
                "buy_low": 15.0,
                "buy_mid": 16.5,
                "buy_high": 18.0,
                "reduce_1": 20.0,
                "reduce_2": 22.5,
                "breakout": 25.0
            }
        },
        "distance_to_key_levels_pct": {
            "stop_28.0": round(dist_stop, 2),
            "buy_low_30.5": round(dist_buy_low, 2),
            "buy_mid_33.5": round(dist_buy_mid, 2),
            "buy_high_36.5": round((price - buy_high) / price * 100, 2),
            "reduce_1_40.6": round((price - reduce_1) / price * 100, 2),
            "reduce_2_45.7": round((price - reduce_2) / price * 100, 2),
            "breakout_50.8": round((price - breakout) / price * 100, 2)
        },
        "trigger_check": {
            "price_key_level_cross": True,
            "abs_daily_pct_gt_3": True,
            "volume_gt_1p5x_5d_avg": ratio_to_5d_avg > 1.5,
            "new_exchange_or_company_announcement": False,
            "margin_net_abs_gt_5m": True,
            "margin_net_value_wan": -3549.82,
            "margin_unavailable_reason": "T-1 6/25 实际净买入 -3549.82 万元 (融资净偿还 3549.82 万元)，绝对值超过 500 万阈值，触发规则 5。",
            "sector_abs_pct_gt_4": None,
            "chip_strict_trigger": True,
            "chip_severe_warning": True,
            "notes": f"6/26 收盘价 {price} 元 ({pct:.2f}%)。31.89 元正式跌破 33.5 元中位支撑线 (R1 触发)；单日跌幅 {abs(pct):.2f}% > 3% 阈值 (R2 触发)；T-1 (6/25) 融资净偿还 3549.82 万元 > 500 万元 (R5 触发)；筹码获利盘 6/24 2.3% -> 6/25 0.3% -> 6/26 收盘 0.0% 连续下跌且 <1% (R7 触发)。四个规则共振触发，中位防守失效，评级维持“空仓等待”。"
        },
        "chip_distribution": {
            "profit_ratio": profit_ratio,
            "trapped_ratio": trapped_ratio,
            "avg_cost": avg_cost,
            "as_of": f"2026-06-26 15:38 BJT (iWencai 收盘获利[20260626]={profit_ratio}%, 套牢盘={trapped_ratio}%, 平均成本={avg_cost} 元)",
            "prev_profit_ratio": 0.3,
            "prev_prev_profit_ratio": 2.3,
            "prev_as_of": "2026-06-25 收盘",
            "prev_prev_as_of": "2026-06-24 收盘",
            "trend": "down_consecutive_two_steps",
            "delta_pct_points_step1": -2.0,
            "delta_pct_points_step2": -0.3,
            "chip_triggered": True,
            "chip_severe_warning": True,
            "chip_trigger_reason": f"获利盘 6/24 收盘 2.3% → 6/25 收盘 0.3% → 6/26 收盘 0.0%，形成连续两期下跌，且获利盘低于 1% 极端红线，严格触发规则 7 筹码触发。套牢盘升至 100.0% 历史极端，市场呈冰冻态势，33.5 支撑失效，评级必须下调为“空仓等待”。"
        },
        "data_quality": {
            "iwencai_quote": "ok",
            "iwencai_market": "ok",
            "iwencai_event": "ok",
            "mx_data": "ok",
            "mx_search": "ok",
            "sector": "partial"
        },
        "blog_updated": True,
        "url": "https://stock.peekabo.cc/600580-wldq/"
    }
    
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print("Updated state JSON successfully.")
    
    # Facts append
    fact_entry = {
        "as_of": "2026-06-26T15:38:00+08:00",
        "ticker": "600580.SH",
        "name": "卧龙电驱",
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
        "chip_prev_profit_ratio": 0.3,
        "chip_trend": "down_consecutive_two_steps",
        "main_net": main_net,
        "big_net": dde_big,
        "mid_net": mid_net,
        "small_net": small_net,
        "run_context": "下午盘后 (15:38 BJT 收盘)",
        "summary": "6/26 收盘跌至 31.89 元（-4.98%）失守 33.5 元支撑，新低探至 31.86 元。收盘获利盘降至 0.0% 触发 R7 筹码警报，T-1 融资大额净流出 3549.82 万元（R5）。评级维持“空仓等待”，关注 30.50 元支撑。",
        "sources": ["hithink-astock-selector", "hithink-market-query", "hithink-event-query", "mx-data", "mx-search"]
    }
    
    with open(facts_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(fact_entry, ensure_ascii=False) + "\n")
    print("Appended fact entry successfully.")

if __name__ == "__main__":
    main()
