#!/usr/bin/env python3
"""功能二：客户周用量折线图 (PIL) — 仅绘制当月Top10客户

补丁记录：
- v3: 只保留功能一计算出的当月Top10客户，其余全部剔除
- v3: 金额前缀统一为 "$" (USD)
"""
import csv, os, sys, textwrap, re, statistics
from collections import defaultdict
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

SALES_NAME = sys.argv[1] if len(sys.argv) > 1 else "扶铿"
CURRENT_YEAR = sys.argv[2] if len(sys.argv) > 2 else "2026"

FONT_REG = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size=12, index=2)
FONT_BOLD = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", size=12, index=2)
FONT_TITLE = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", size=16, index=2)
FONT_SMALL = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size=10, index=2)

# ---- 读取当月Top10客户列表（由功能一生成） ----
top10_file = f"top10_monthly_{SALES_NAME}.txt"
TOP10_SET = set()
if os.path.exists(top10_file):
    with open(top10_file, "r", encoding="utf-8") as f:
        TOP10_SET = {line.strip() for line in f if line.strip()}
    print(f"功能二：读取到 {len(TOP10_SET)} 个当月Top10客户")
else:
    print(f"警告：未找到 {top10_file}，将绘制所有客户")

rows = []
with open(f"ali_all_local_data_{SALES_NAME}.csv", newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['year'] == CURRENT_YEAR:
            rows.append(r)

cust_week = defaultdict(lambda: defaultdict(float))
for r in rows:
    name = r['customer_name']
    # ---- 补丁：只保留Top10客户 ----
    if TOP10_SET and name not in TOP10_SET:
        continue
    try:
        dt = datetime.strptime(r['cost_date'], '%Y-%m-%d')
        wn = dt.isocalendar()[1]
    except:
        continue
    cust_week[name][wn] += float(r['pretaxgrossamount'])

active_cust = {}
for name, weeks in cust_week.items():
    total = sum(weeks.values())
    if total > 0:
        active_cust[name] = dict(weeks)

sorted_cust = sorted(active_cust.items(), key=lambda x: sum(x[1].values()), reverse=True)

all_weeks = set()
for _, weeks in sorted_cust:
    all_weeks.update(weeks.keys())
if not all_weeks:
    print("无数据，跳过功能二")
    sys.exit(0)

min_week, max_week = min(all_weeks), max(all_weeks)
week_list = list(range(min_week, max_week + 1))

COLORS = [
    (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40),
    (148, 103, 189), (140, 86, 75), (227, 119, 194), (127, 127, 127),
    (188, 189, 34), (23, 190, 207), (174, 199, 232), (255, 187, 120),
    (152, 223, 138), (255, 152, 150), (197, 176, 213), (196, 156, 148),
]

W, H = 1400, 700
LEGEND_W = 250
PLOT_W = W - LEGEND_W - 80
PLOT_H = H - 120
MARGIN_L, MARGIN_R = 60, 20
MARGIN_T, MARGIN_B = 60, 60

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

draw.text((MARGIN_L, 10), f"阿里云客户周用量趋势 — {SALES_NAME} ({CURRENT_YEAR}年) | 仅当月Top10客户", fill=(68, 114, 196), font=FONT_TITLE)

# Y轴动态范围
all_vals = []
for _, weeks in sorted_cust:
    for wn in week_list:
        all_vals.append(weeks.get(wn, 0))

non_zero_vals = [v for v in all_vals if v > 0]
if not non_zero_vals:
    print("所有周用量为0，跳过功能二")
    sys.exit(0)

weekly_avg = statistics.mean(non_zero_vals)
weekly_max = max(non_zero_vals)

if weekly_max > weekly_avg * 3:
    WEEKLY_CAP = weekly_avg * 3
    y_max = WEEKLY_CAP * 1.15
else:
    WEEKLY_CAP = weekly_max
    y_max = weekly_max * 1.15

plot_x0, plot_y0 = MARGIN_L, MARGIN_T
plot_x1, plot_y1 = MARGIN_L + PLOT_W, MARGIN_T + PLOT_H
draw.rectangle([plot_x0, plot_y0, plot_x1, plot_y1], outline=(200, 200, 200))

for i in range(6):
    val = y_max * i / 5
    yp = plot_y1 - (val / y_max) * PLOT_H
    draw.line([(plot_x0 - 5, yp), (plot_x0, yp)], fill=(180, 180, 180))
    draw.text((plot_x0 - 55, yp - 7), f"${val:,.0f}", fill=(128, 128, 128), font=FONT_SMALL)
    if i > 0:
        draw.line([(plot_x0, yp), (plot_x1, yp)], fill=(230, 230, 230))

if len(week_list) > 1:
    step = max(1, len(week_list) // 12)
    for i, wn in enumerate(week_list):
        xp = plot_x0 + (i / (len(week_list) - 1)) * PLOT_W
        if i % step == 0 or i == len(week_list) - 1:
            draw.line([(xp, plot_y1), (xp, plot_y1 + 5)], fill=(180, 180, 180))
            draw.text((xp - 10, plot_y1 + 8), f"W{wn}", fill=(128, 128, 128), font=FONT_SMALL)

for ci, (name, weeks) in enumerate(sorted_cust):
    color = COLORS[ci % len(COLORS)]
    points = []
    values = []
    for i, wn in enumerate(week_list):
        xp = plot_x0 + (i / (len(week_list) - 1)) * PLOT_W if len(week_list) > 1 else plot_x0 + PLOT_W / 2
        actual_val = weeks.get(wn, 0)
        capped_val = min(actual_val, WEEKLY_CAP) if actual_val > 0 else 0
        yp = plot_y1 - (capped_val / y_max) * PLOT_H if y_max > 0 else plot_y1
        points.append((xp, yp))
        values.append((xp, yp, actual_val))

    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=color, width=2)

    non_zero = [(x, y, v) for x, y, v in values if v > 0]
    if non_zero:
        max_pt = max(non_zero, key=lambda p: p[2])
        min_pt = min(non_zero, key=lambda p: p[2])
        for px, py, pv in [max_pt, min_pt]:
            draw.ellipse([px-4, py-4, px+4, py+4], fill=color, outline="white")
            if pv > WEEKLY_CAP:
                label = f"${pv:,.0f} (⚠️大额续费)"
                label_color = (220, 50, 50)
            else:
                label = f"${pv:,.0f}"
                label_color = (0, 0, 0)
            draw.text((px + 6, py - 14), label, fill=label_color, font=FONT_SMALL)

# 图例
lx = plot_x1 + 15
ly = MARGIN_T
draw.text((lx, ly), "客户图例", fill=(68, 114, 196), font=FONT_BOLD)
ly += 24

def smart_wrap(text, max_chars=12):
    if re.search(r'[\u4e00-\u9fff]', text):
        lines = []
        for i in range(0, len(text), max_chars):
            lines.append(text[i:i+max_chars])
        return '\n'.join(lines)
    else:
        return '\n'.join(textwrap.wrap(text, width=max_chars, break_long_words=False))

for ci, (name, weeks) in enumerate(sorted_cust):
    color = COLORS[ci % len(COLORS)]
    draw.rectangle([lx, ly + 4, lx + 14, ly + 18], fill=color)
    wrapped = smart_wrap(name, 14)
    for li, line in enumerate(wrapped.split('\n')):
        draw.text((lx + 20, ly + li * 14), line, fill=(0, 0, 0), font=FONT_SMALL)
    ly += max(len(wrapped.split('\n')) * 14, 18) + 4

out_path = f"func2_weekly_{SALES_NAME}.png"
img.save(out_path)
print(f"功能二图片已生成: {out_path}")

print("\n=== 周用量统计 (仅Top10客户) ===")
for name, weeks in sorted_cust:
    vals = list(weeks.values())
    avg = sum(vals) / len(week_list) if week_list else 0
    mx = max(vals)
    mn = min(v for v in vals if v > 0) if any(v > 0 for v in vals) else 0
    print(f"{name}: 周均 ${avg:,.0f} | 最高 ${mx:,.0f} | 最低 ${mn:,.0f}")
