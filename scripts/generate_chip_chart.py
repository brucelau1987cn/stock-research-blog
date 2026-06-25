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

def write_placeholder_svg(output_path, text="筹码分布走势图：数据积累中，需至少 2 天收盘数据"):
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
        write_placeholder_svg(output_path, "筹码分布走势图：暂无收盘数据（等待首次下午运行）")
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
                    # Filter for BJT afternoon close runs (hour >= 15)
                    dt = parse_time(ts)
                    if dt != datetime.min and dt.hour >= 15:
                        history.append({
                            'date_key': dt.strftime('%Y-%m-%d'),
                            'ts': ts,
                            'dt': dt,
                            'profit_ratio': float(profit_ratio)
                        })
                        
    # Filter to keep only the latest record per day (in case of multiple afternoon runs)
    daily_records = {}
    for h in history:
        date_key = h['date_key']
        if date_key not in daily_records or h['dt'] > daily_records[date_key]['dt']:
            daily_records[date_key] = h
            
    sorted_history = sorted(daily_records.values(), key=lambda x: x['dt'])
    
    # Restrict to last 15 days
    sorted_history = sorted_history[-15:]
    
    if len(sorted_history) < 2:
        write_placeholder_svg(output_path, "筹码分布走势图：数据积累中，需至少 2 天下午收盘数据")
        sys.exit(0)
        
    # 2. Extract arrays
    dates = []
    profits = []
    
    for h in sorted_history:
        dates.append(h['dt'].strftime('%m-%d'))
        profits.append(h['profit_ratio'])
        
    # 3. Plotting
    try:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'DejaVu Sans', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, ax1 = plt.subplots(figsize=(10, 4.5), facecolor='#1e1e1e')
        ax1.set_facecolor('#121212')
        
        # Grid lines
        ax1.grid(True, color='#2d2d2d', linestyle='--', alpha=0.5)
        
        # Axis 1: Profit Ratio (Only Y)
        color_profit = '#00e676' # Bright green
        ax1.set_xlabel('日期', color='#e0e0e0', labelpad=10)
        ax1.set_ylabel('获利盘比例 (%)', color=color_profit, labelpad=10)
        
        # Plot single line
        line = ax1.plot(dates, profits, color=color_profit, marker='o', linewidth=2.5, label='获利盘比例 (%)')
        
        ax1.tick_params(axis='y', labelcolor=color_profit, colors='#888888')
        ax1.tick_params(axis='x', colors='#888888')
        ax1.set_ylim(-5, 115) # Leave room at the top for labels
        
        # Annotate points with values
        for x, y in zip(dates, profits):
            val_str = f"{y:.1f}%" if y % 1 != 0 else f"{int(y)}%"
            ax1.annotate(val_str, 
                         xy=(x, y), 
                         xytext=(0, 8), 
                         textcoords="offset points", 
                         ha='center', 
                         va='bottom', 
                         color='#00e676', 
                         fontsize=10, 
                         fontweight='bold')
                         
        plt.title(f'{title_name} 筹码分布历史走势 (近 {len(sorted_history)} 个交易日收盘)', color='#e0e0e0', fontsize=14, pad=15)
        
        # Adjust borders
        for spine in ax1.spines.values():
            spine.set_color('#2d2d2d')
            
        fig.tight_layout()
        
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(output_path, format='svg', bbox_inches='tight', transparent=True)
        plt.close()
        print(f"Successfully generated SVG chart at: {output_path}")
        
    except Exception as e:
        print(f"Error plotting chart: {e}")
        write_placeholder_svg(output_path, f"筹码分布走势图：绘制失败 ({str(e)})")

if __name__ == '__main__':
    main()
