import json

state_file = '/root/.hermes/state/wldq_tracker.json'
with open(state_file, 'r', encoding='utf-8') as f:
    state = json.load(f)

trigger_reasons = state.get('trigger_reasons', [])
trigger_str = "\\n  ".join(trigger_reasons) if trigger_reasons else "筹码盘后例行更新 (触发状态: False)"

iwencai = state.get('iwencai', {})
close_price = iwencai.get('close', 0.0)
pct = iwencai.get('pct', 0.0)
turnover_rate = iwencai.get('turnover_rate', 0.0)

mx_data = state.get('mx_data', {})
price = mx_data.get('price', close_price)

iwencai_market = state.get('iwencai_market', {})
big_net_val = iwencai_market.get('big_net', 0.0)
big_net = f"{big_net_val/100000000:.2f} 亿元"

volume_check = state.get('volume_check', {})
vol_ratio = volume_check.get('ratio_to_5d_avg', 0.0)

chip_distribution = state.get('chip_distribution', {})
profit_ratio = chip_distribution.get('profit_ratio', 0.0)

key_levels = state.get('key_levels', {}).get('scaled', {})
stop = key_levels.get('stop', 0.0)
buy_mid = key_levels.get('buy_mid', 0.0)
buy_low = key_levels.get('buy_low', 0.0)

dist = state.get('distance_to_key_levels_pct', {})
stop_dist = dist.get('stop_28.0', 0.0)
buy_mid_dist = dist.get('buy_mid_33.5', 0.0)
buy_low_dist = dist.get('buy_low_30.5', 0.0)

message = f"""📊 卧龙电驱 600580.SH 跟踪 (操盘日志)

⏰ 2026-06-26 15:47 BJT
💰 最新价：{price:.2f} 元（{pct:+.2f}%）
📈 动能资金：量比 {vol_ratio:.2f}x · 换手率 {turnover_rate:.2f}% · 主力大单 {big_net}
🧩 获利盘：{profit_ratio:.2f}%

🚨 触发：{trigger_str}

🛡 对峙边界：
- 🔼 阻力位：{buy_mid:.2f} 元（距 {buy_mid_dist:+.2f}%）
- 🔽 支撑位：{buy_low:.2f} 元（距 {buy_low_dist:+.2f}%）
- 🚨 止损位：{stop:.2f} 元（距 {stop_dist:+.2f}%）

🎯 执行计划：
- IF 向上：若日内大幅放量（量比 > 1.5x）重新站稳 {buy_mid:.2f} 元攻击线 → 考虑维持“右侧观望”评级并观察资金流入持续度；否则不主动加仓。
- IF 向下：若收盘实质性跌破 {buy_low:.2f} 元防守线 → 离场观望，防范向 {stop:.2f} 元风控底线寻底的风险。

🔗 https://stock.peekabo.cc/600580-wldq/"""
print(message)
