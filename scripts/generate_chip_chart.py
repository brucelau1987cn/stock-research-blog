#!/usr/bin/env python3
import os
import sys
import json
import re
from datetime import datetime

# Set matplotlib backend to Agg before importing pyplot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def write_placeholder_svg(output_path, text="筹码与价格走势图：数据积累中，需至少 2 次跟踪记录"):
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="350" viewBox="0 0 800 350">
  <rect width="100%" height="100%" fill="#121212"/>
  <rect x="10" y="10" width="780" height="330" rx="5" fill="#1e1e1e" stroke="#2d2d2d" stroke-width="1"/>
  <text x="400" y="175" fill="#888888" font-family="DejaVu Sans, Arial, sans-serif" font-size="16" text-anchor="middle" dominant-baseline="middle">
    {text}
  </text>
</svg>"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(svg_content)
    print(f"Generated placeholder SVG at: {output_path}")

def parse_time(t_str):
    t_str = t_str.replace(' BJT', '')
    # Strip timezone offset for datetime parsing if needed
    clean_str = t_str
    if '+' in clean_str and 'T' in clean_str:
        clean_str = clean_str.split('+')[0]
    
    for fmt in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S+08:00', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S.%f'):
        try:
            return datetime.strptime(clean_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            try:
                return datetime.strptime(t_str, fmt)
            except ValueError:
                pass
    return datetime.min

def main():
    if len(sys.argv) < 3:
        print("Usage: generate_chip_chart.py <slug> <title_name>")
        sys.exit(1)
        
    slug = sys.argv[1]
    title_name = sys.argv[2]
    
    facts_path = f'/root/.hermes/state/{slug}_tracker_facts.jsonl'
    output_dir = '/root/projects/stock-research-blog/public/assets/chips'
    output_path = os.path.join(output_dir, f'{slug}.svg')
    
    if not os.path.exists(facts_path):
        write_placeholder_svg(output_path, "筹码与价格走势图：暂无跟踪数据（等待首次运行）")
        sys.exit(0)
        
    # 1. Parse history
    history = []
    with open(facts_path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            
            ts = d.get('ts') or d.get('as_of')
            price = None
            profit_ratio = None
            
            if ts:
                if 'iwencai' in d and isinstance(d['iwencai'], dict):
                    price = d['iwencai'].get('price') or d['iwencai'].get('close')
                    profit_ratio = d['iwencai'].get('profit_ratio')
                if price is None:
                    price = d.get('price') or d.get('close')
                if profit_ratio is None:
                    profit_ratio = d.get('chip_profit_ratio')
                    if profit_ratio is None and 'chip_distribution' in d and isinstance(d['chip_distribution'], dict):
                        profit_ratio = d['chip_distribution'].get('profit_ratio')
                
                if price is not None and profit_ratio is not None:
                    history.append({
                        'ts': ts,
                        'price': float(price),
                        'profit_ratio': float(profit_ratio)
                    })
                    
    # Filter unique timestamps to avoid duplication in plotting
    unique_history = {}
    for h in history:
        unique_history[h['ts']] = h
    history = list(unique_history.values())
    
    history.sort(key=lambda x: parse_time(x['ts']))
    
    # Restrict to last 15 points
    history = history[-15:]
    
    if len(history) < 2:
        write_placeholder_svg(output_path, "筹码与价格走势图：数据积累中，需至少 2 次跟踪记录")
        sys.exit(0)
        
    # 2. Extract arrays
    dates = []
    prices = []
    profits = []
    
    for h in history:
        dt = parse_time(h['ts'])
        dates.append(dt.strftime('%m-%d\n%H:%M'))
        prices.append(h['price'])
        profits.append(h['profit_ratio'])
        
    # 3. Plotting
    try:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'DejaVu Sans', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, ax1 = plt.subplots(figsize=(10, 4.5), facecolor='#1e1e1e')
        ax1.set_facecolor('#121212')
        
        # Grid lines
        ax1.grid(True, color='#2d2d2d', linestyle='--', alpha=0.5)
        
        # Axis 1: Profit Ratio (Left Y)
        color_profit = '#00e676' # Bright green
        ax1.set_xlabel('时间 (BJT)', color='#e0e0e0', labelpad=10)
        ax1.set_ylabel('获利盘比例 (%)', color=color_profit, labelpad=10)
        line1 = ax1.plot(dates, profits, color=color_profit, marker='o', linewidth=2.5, label='获利盘比例 (%)')
        ax1.tick_params(axis='y', labelcolor=color_profit, colors='#888888')
        ax1.tick_params(axis='x', colors='#888888')
        ax1.set_ylim(-5, 105) # Profit ratio is always 0-100
        
        # Axis 2: Closing Price (Right Y)
        ax2 = ax1.twinx()
        color_price = '#ffb300' # Amber/Gold
        ax2.set_ylabel('股价 (元)', color=color_price, labelpad=10)
        line2 = ax2.plot(dates, prices, color=color_price, marker='s', linestyle='--', linewidth=1.5, label='收盘价 (元)')
        ax2.tick_params(axis='y', labelcolor=color_price, colors='#888888')
        
        # Set Y-axis range for price with some padding
        min_p, max_p = min(prices), max(prices)
        pad = max((max_p - min_p) * 0.1, 0.05)
        ax2.set_ylim(min_p - pad, max_p + pad)
        
        # Combine legends
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        leg = ax1.legend(lines, labels, loc='upper left', facecolor='#1e1e1e', edgecolor='#2d2d2d')
        for text in leg.get_texts():
            text.set_color('#e0e0e0')
            
        plt.title(f'{title_name} 筹码分布与股价走势 (近 {len(history)} 次跟踪)', color='#e0e0e0', fontsize=14, pad=15)
        
        # Adjust layout and borders
        for ax in [ax1, ax2]:
            for spine in ax.spines.values():
                spine.set_color('#2d2d2d')
                
        fig.tight_layout()
        
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(output_path, format='svg', bbox_inches='tight', transparent=True)
        plt.close()
        print(f"Successfully generated SVG chart at: {output_path}")
        
    except Exception as e:
        print(f"Error plotting chart: {e}")
        write_placeholder_svg(output_path, f"筹码与价格走势图：绘制失败 ({str(e)})")

if __name__ == '__main__':
    main()
