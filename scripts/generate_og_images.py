# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"

STOCK_META = {
    "601012-ljln": {
        "ticker": "601012",
        "name": "隆基绿能",
        "action_rating": "🚨 强力观望 / 严禁左侧抄底",
        "action_color": "#ef4444",
        "confirm_up": "14.50 元"
    },
    "002459-jakt": {
        "ticker": "002459",
        "name": "晶澳科技",
        "action_rating": "🚨 弱势探底 / 拒绝左侧抄底",
        "action_color": "#ef4444",
        "confirm_up": "13.20 元"
    },
    "600438-twgf": {
        "ticker": "600438",
        "name": "通威股份",
        "action_rating": "🟡 硅料筑底 / 场外静待右侧",
        "action_color": "#eab308",
        "confirm_up": "18.50 元"
    },
    "600580-wldq": {
        "ticker": "600580",
        "name": "卧龙电驱",
        "action_rating": "🟡 战术观望 / 拒绝题材虚火",
        "action_color": "#eab308",
        "confirm_up": "13.50 元"
    },
    "603997-jfgf": {
        "ticker": "603997",
        "name": "继峰股份",
        "action_rating": "🟡 订单高增但利润率阵痛",
        "action_color": "#eab308",
        "confirm_up": "12.80 元"
    },
    "002810-shda": {
        "ticker": "002810",
        "name": "山东赫达",
        "action_rating": "🟡 周期底摩擦 / 静待补库",
        "action_color": "#eab308",
        "confirm_up": "13.20 元"
    },
    "002026-swd": {
        "ticker": "002026",
        "name": "山东威达",
        "action_rating": "🚨 弱势盘整 / 警惕换电风险",
        "action_color": "#ef4444",
        "confirm_up": "7.50 元"
    }
}

def draw_gradient_background(draw, width, height, color1, color2):
    for y in range(height):
        r = int(color1[0] + (color2[0] - color1[0]) * (y / height))
        g = int(color1[1] + (color2[1] - color1[1]) * (y / height))
        b = int(color1[2] + (color2[2] - color1[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

def generate_default_og():
    w, h = 1200, 630
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    
    draw_gradient_background(draw, w, h, (7, 12, 20), (11, 15, 25))
    
    grid_color = (18, 24, 38)
    for x in range(0, w, 60):
        draw.line([(x, 0), (x, h)], fill=grid_color, width=1)
    for y in range(0, h, 60):
        draw.line([(0, y), (w, y)], fill=grid_color, width=1)
        
    draw.rectangle([(0, 0), (20, h)], fill=(37, 99, 235))
    
    font_large = ImageFont.truetype(FONT_PATH, 110)
    font_medium = ImageFont.truetype(FONT_PATH, 36)
    font_small = ImageFont.truetype(FONT_PATH, 24)
    
    draw.text((100, 180), "AI选股", fill=(255, 255, 255), font=font_large)
    draw.text((100, 340), "A-Share Quantitative & Technical Analysis", fill=(148, 163, 184), font=font_medium)
    draw.text((100, 420), "Brucelau1987 自营操盘量化投研系统 · 筹码分布对峙分析", fill=(71, 85, 105), font=font_small)
    
    dest = Path("/root/projects/stock-research-blog/src/assets/og-cover.png")
    img.save(dest, "PNG")
    print(f"Generated default OG cover at {dest}")

def generate_stock_ogs():
    w, h = 1200, 630
    og_dir = Path("/root/projects/stock-research-blog/public/assets/og")
    og_dir.mkdir(parents=True, exist_ok=True)
    
    for slug, d in STOCK_META.items():
        slug_short = slug.split('-')[1]
        
        json_path = Path(f'/root/.hermes/state/{slug_short}_tracker.json')
        if not json_path.exists():
            continue
        t_data = json.loads(json_path.read_text(encoding='utf-8'))
        price = t_data.get('price', 0.0)
        pct = t_data.get('pct', 0.0)
        chip = t_data.get('chip_distribution', {})
        profit_ratio = chip.get('profit_ratio', 0.0)
        trapped_ratio = chip.get('trapped_ratio', 0.0)
        avg_cost = chip.get('avg_cost', 0.0)
        
        img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)
        
        draw_gradient_background(draw, w, h, (15, 23, 42), (2, 6, 23))
        
        grid_color = (25, 33, 50)
        for x in range(0, w, 50):
            draw.line([(x, 0), (x, h)], fill=grid_color, width=1)
        for y in range(0, h, 50):
            draw.line([(0, y), (w, y)], fill=grid_color, width=1)
            
        bar_color = tuple(int(d['action_color'].lstrip('#')[k:k+2], 16) for k in (0, 2, 4))
        draw.rectangle([(0, 0), (25, h)], fill=bar_color)
        
        font_code = ImageFont.truetype(FONT_PATH, 42)
        font_title = ImageFont.truetype(FONT_PATH, 78)
        font_rating = ImageFont.truetype(FONT_PATH, 48)
        font_metric = ImageFont.truetype(FONT_PATH, 32)
        font_label = ImageFont.truetype(FONT_PATH, 24)
        
        draw.text((100, 70), f"{d['ticker']} · A-Share", fill=(148, 163, 184), font=font_code)
        draw.text((100, 130), d['name'], fill=(255, 255, 255), font=font_title)
        
        draw.rectangle([(100, 250), (950, 330)], fill=(30, 41, 59))
        draw.text((120, 260), f"交易决策指令：{d['action_rating']}", fill=(248, 250, 252), font=font_rating)
        
        col_w = 230
        metrics = [
            ("收盘价格", f"{price:.2f} 元", f"{pct:+.2f}%"),
            ("筹码获利比", f"{profit_ratio:.2f}%", "极端套牢"),
            ("筹码套牢比", f"{trapped_ratio:.2f}%", f"平均成本 {avg_cost:.2f}元"),
            ("多头确认线", d['confirm_up'], "站方可评估")
        ]
        
        for idx, (label, val, note) in enumerate(metrics):
            cx = 100 + idx * col_w
            draw.rectangle([(cx, 380), (cx + col_w - 20, 520)], fill=(15, 23, 42), outline=(51, 65, 85), width=2)
            draw.text((cx + 15, 395), label, fill=(148, 163, 184), font=font_label)
            v_color = (56, 189, 248) if idx != 3 else (244, 63, 94)
            draw.text((cx + 15, 430), val, fill=v_color, font=font_metric)
            draw.text((cx + 15, 480), note, fill=(100, 116, 139), font=font_label)
            
        draw.text((100, 560), "Brucelau1987 自营操盘量化仪表盘 · 每日盘后自动校准", fill=(71, 85, 105), font=font_label)
        
        dest_path = og_dir / f"{slug_short}.png"
        img.save(dest_path, "PNG")
        print(f"Generated stock OG image for {d['name']} at {dest_path}")

def main():
    generate_default_og()
    generate_stock_ogs()

if __name__ == '__main__':
    main()
