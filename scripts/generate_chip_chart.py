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
  <rect width="100%" height="100%" fill="none"/>
  <rect x="10" y="10" width="780" height="330" rx="5" fill="none" stroke="#cccccc" stroke-width="1"/>
  <text x="400" y="175" fill="#000000" font-family="DejaVu Sans, Arial, sans-serif" font-size="16" text-anchor="middle" dominant-baseline="middle">
    {text}
  </text>
</svg>"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(svg_content)
    print(f"Generated placeholder SVG at: {output_path}")

def parse_time(t_str):
    if not t_str:
        return datetime.min
    t_str = t_str.replace(' BJT', '')
    # Try multiple formats
    formats = [
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S+08:00',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(t_str, fmt)
        except ValueError:
            continue
    # Fallback: try removing timezone suffix
    try:
        clean = t_str.split('+')[0].split('T')[0] + 'T' + t_str.split('T')[1].split('+')[0] if 'T' in t_str else t_str
        return datetime.strptime(clean.split('.')[0], '%Y-%m-%dT%H:%M:%S')
    except:
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
        write_placeholder_svg(output_path, "筹码与价格走势图：暂无数据")
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
                    if profit_ratio is None:
                        profit_ratio = d.get('profit_ratio')
                    if profit_ratio is None and 'chip_distribution' in d and isinstance(d['chip_distribution'], dict):
                        profit_ratio = d['chip_distribution'].get('profit_ratio')
                
                if profit_ratio is not None:
                    # Filter for BJT afternoon close runs (hour >= 15)
                    dt = parse_time(ts)
                    if dt != datetime.min and dt.hour >= 9:
                        history.append({
                            'date_key': dt.strftime('%Y-%m-%d'),
                            'ts': ts,
                            'dt': dt,
                            'price': float(price) if price is not None else None,
                            'profit_ratio': float(profit_ratio)
                        })
                        
    # Filter to keep only the latest record per day
    daily_records = {}
    for h in history:
        date_key = h['date_key']
        if date_key not in daily_records or h['dt'] > daily_records[date_key]['dt']:
            daily_records[date_key] = h
            
    sorted_history = sorted(daily_records.values(), key=lambda x: x['dt'])
    
    # Restrict to last 15 days
    sorted_history = sorted_history[-15:]
    
    if len(sorted_history) < 2:
        write_placeholder_svg(output_path, "筹码与价格走势图：数据积累中，需至少 2 天下午收盘数据")
        sys.exit(0)
        
    # 2. Extract arrays
    dates = []
    prices = []
    profits = []
    
    for h in sorted_history:
        dates.append(h['dt'].strftime('%m-%d'))
        profits.append(h['profit_ratio'])
        prices.append(h['price'])
        
    # 3. Plotting
    try:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'DejaVu Sans', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['svg.fonttype'] = 'none' # Render text as text tags in SVG!
        
        # Figure with transparent background
        fig, ax1 = plt.subplots(figsize=(10, 4.5), facecolor='none')
        ax1.set_facecolor('none')
        
        # Grid lines (light grey)
        ax1.grid(True, color='#e0e0e0', linestyle='--', alpha=0.6)
        
        # Axis 1: Profit Ratio (Left Y, Coral Red)
        color_profit = '#ff3366' # Coral Red
        ax1.set_xlabel('日期', color='#000000', labelpad=10)
        ax1.set_ylabel('获利盘比例 (%)', color=color_profit, labelpad=10)
        
        # Plot profit ratio line
        line1 = ax1.plot(dates, profits, color=color_profit, marker='o', linewidth=2.5, label='获利盘比例 (%)')
        
        ax1.tick_params(axis='y', labelcolor=color_profit, colors='#000000')
        ax1.tick_params(axis='x', colors='#000000')
        
        # Limit Profit Ratio to lower half of the chart (max value 100% fits in 0-180 limit)
        ax1.set_ylim(-5, 180)
        
        # Annotate profit ratio points
        for x, y in zip(dates, profits):
            val_str = f"{y:.1f}%" if y % 1 != 0 else f"{int(y)}%"
            ax1.annotate(val_str, 
                         xy=(x, y), 
                         xytext=(0, 8), 
                         textcoords="offset points", 
                         ha='center', 
                         va='bottom', 
                         color=color_profit, 
                         fontsize=10, 
                         fontweight='bold')
                         
        # Axis 2: Stock Price (Right Y, Deep Blue)
        # Filter None prices if any
        valid_prices = [p for p in prices if p is not None]
        if len(valid_prices) >= 2:
            ax2 = ax1.twinx()
            ax2.set_facecolor('none')
            color_price = '#0d47a1' # Deep Blue
            ax2.set_ylabel('收盘价 (元)', color=color_price, labelpad=10)
            
            # Plot price line (dashed)
            line2 = ax2.plot(dates, prices, color=color_price, marker='s', linestyle='--', linewidth=1.5, label='收盘价 (元)')
            ax2.tick_params(axis='y', labelcolor=color_price, colors='#000000')
            
            # Set Y-axis range for price to keep it in the upper portion
            min_p, max_p = min(valid_prices), max(valid_prices)
            range_p = max_p - min_p if max_p - min_p > 0 else max_p * 0.1
            if range_p == 0:
                range_p = 1.0
            ax2.set_ylim(min_p - range_p * 1.0, max_p + range_p * 0.1)
            
            # Annotate price points
            for x, y in zip(dates, prices):
                if y is not None:
                    ax2.annotate(f"{y:.2f}", 
                                 xy=(x, y), 
                                 xytext=(0, 8), 
                                 textcoords="offset points", 
                                 ha='center', 
                                 va='bottom', 
                                 color=color_price, 
                                 fontsize=10, 
                                 fontweight='bold')
                                 
            # Combine legends
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            leg = ax1.legend(lines, labels, loc='upper left', facecolor='none', edgecolor='#cccccc')
            for text in leg.get_texts():
                text.set_color('#000000')
            
            # Set border colors to light grey
            for ax in [ax1, ax2]:
                for spine in ax.spines.values():
                    spine.set_color('#cccccc')
        else:
            # If no price data, just draw border for ax1
            for spine in ax1.spines.values():
                spine.set_color('#cccccc')
                
        plt.title(f'{title_name} 筹码分布与股价走势 (近 {len(sorted_history)} 个交易日收盘)', color='#000000', fontsize=14, pad=15)
        fig.tight_layout()
        
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(output_path, format='svg', bbox_inches='tight', transparent=True)
        plt.close()
        print(f"Successfully generated SVG chart at: {output_path}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error plotting chart: {e}")
        write_placeholder_svg(output_path, f"筹码与价格走势图：绘制失败 ({str(e)})")

if __name__ == '__main__':
    main()
