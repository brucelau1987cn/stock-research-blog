import json

state_file = '/root/.hermes/state/wldq_tracker.json'
with open(state_file, 'r', encoding='utf-8') as f:
    state = json.load(f)

state['as_of'] = '2026-06-26T15:47:00+08:00'
state['iwencai']['as_of'] = '2026-06-26 15:47 BJT (iWencai 收盘价[20260626]=31.89, 最新获利=0.0%)'
state['mx_data']['as_of'] = '2026-06-26 15:47 BJT'
state['chip_distribution']['as_of'] = '2026-06-26 15:47 BJT (iWencai 收盘获利[20260626]=0.0%, 套牢盘=100.0%, 平均成本=39.12 元)'

with open(state_file, 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
