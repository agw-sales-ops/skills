#!/usr/bin/env python3
"""功能三：客户月度用量分组柱状图 (PIL) — 仅展示当月Top10客户

补丁记录：
- v3: 横轴只展示功能一计算出的当月Top10客户
- v3: 横轴客户名统一顺时针倾斜45度
- v3: 金额前缀统一为 "$" (USD)
"""
import csv, os, sys, textwrap, re, math
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

SALES_NAME = sys.argv[1] if len(sys.argv) > 1 else "扶铿"
CURRENT_YEAR = sys.argv[2] if len(sys.argv) > 2 else "2026"

FONT_REG = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size=11, index=2)
FONT_BOLD = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", size=11, index=2)
FONT_TITLE = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", size=16, index=2)
FONT_SMALL = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size=9, index=2)

# ---- 读取当月Top10客户列表（由功能一生成） ----
top10_file = f"top10_monthly_{SALES_NAME}.txt"
TOP10_LIST = []
TOP10_SET = set()
if os.path.exists(top10_file):
    with open(top10_file, "r", encoding="utf-8") as f:
        TOP10_LIST = [line.strip() for line in f if line.strip()]
    TOP10_SET = set(TOP10_LIST)
    print(f"功能三：读取到 {len(TOP10_LIST)} 个当月Top10客户")
else:
    print(f"警告：未找到 {top10_file}，将按当年累计取Top10兜底")

rows = []
with open(f"ali_all_local_data_{SALES_NAME}.csv", newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['year'] == CURRENT_YEAR:
            rows.append(r)

cust_month = defaultdict(lambda: defaultdict(float))
for r in rows:
    name = r['customer_name']
    # ---- 补丁：只保留Top10客户 ----
    if TOP10_SET and name not in TOP10_SET:
        continue
    m = int(r['month'])
    cust_month[name][m] += float(r['pretaxgrossamount'])

# 若没有Top10文件，则兜底为年累计Top10，不扩大到全部客户
if not TOP10_SET:
    all_cust_month = defaultdict(lambda: defaultdict(float))
    for r in rows:
        m = int(r['month'])
        all_cust_month[r['customer_name']][m] += float(r['pretaxgrossamount'])
    totals = {name: sum(months.values()) for name, months in all_cust_month.items()}
    TOP10_LIST = [name for name, _ in sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]]
    TOP10_SET = set(TOP10_LIST)
    cust_month = defaultdict(lambda: defaultdict(float))
    for r in rows:
        if r['customer_name'] not in TOP10_SET:
            continue
        m = int(r['month'])
        cust_month[r['customer_name']][m] += float(r['pretaxgrossamount'])

# 保持功能一Top10顺序；若兜底则按总额排序
if TOP10_LIST:
    sorted_cust = [(name, sum(cust_month[name].values())) for name in TOP10_LIST if sum(cust_month[name].values()) > 0]
else:
    cust_total = {name: sum(months.values()) for name, months in cust_month.items() if sum(months.values()) > 0}
    sorted_cust = sorted(cust_total.items(), key=lambda x: x[1], reverse=True)[:10]

available_months = sorted(set(m for name, _ in sorted_cust for m in cust_month[name].keys()))
if not available_months:
    print("无数据，跳过功能三")
    sys.exit(0)

MONTH_COLORS = [
    (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40),
    (148, 103, 189), (140, 86, 75), (227, 119, 194), (127, 127, 127),
    (188, 189, 34), (23, 190, 207), (174, 199, 232), (255, 187, 120),
]

all_vals = []
for name, _ in sorted_cust:
    for m in available_months:
        all_vals.append(cust_month[name].get(m, 0))
y_max = max(all_vals) * 1.15 if all_vals else 1

n_cust = len(sorted_cust)
n_months = len(available_months)
bar_group_w = 70
bar_w = max(3, bar_group_w // max(n_months, 1) - 1)
group_gap = 28

W = max(1200, n_cust * (bar_group_w + group_gap) + 220)
H = 760
MARGIN_L, MARGIN_R = 80, 40
MARGIN_T, MARGIN_B = 60, 180
PLOT_W = W - MARGIN_L - MARGIN_R
PLOT_H = H - MARGIN_T - MARGIN_B

img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

draw.text((MARGIN_L, 10), f"阿里云客户月度用量 — {SALES_NAME} ({CURRENT_YEAR}年) | 仅当月Top10客户", fill=(68, 114, 196), font=FONT_TITLE)

plot_x0, plot_y0 = MARGIN_L, MARGIN_T
plot_x1, plot_y1 = MARGIN_L + PLOT_W, MARGIN_T + PLOT_H
draw.rectangle([plot_x0, plot_y0, plot_x1, plot_y1], outline=(200, 200, 200))

for i in range(6):
    val = y_max * i / 5
    yp = plot_y1 - (val / y_max) * PLOT_H
    draw.line([(plot_x0 - 5, yp), (plot_x0, yp)], fill=(180, 180, 180))
    draw.text((plot_x0 - 65, yp - 7), f"${val:,.0f}", fill=(128, 128, 128), font=FONT_SMALL)
    if i > 0:
        draw.line([(plot_x0, yp), (plot_x1, yp)], fill=(230, 230, 230))

def smart_wrap(text, max_chars=10):
    if re.search(r'[\u4e00-\u9fff]', text):
        return text[:max_chars] + ("…" if len(text) > max_chars else "")
    else:
        wrapped = textwrap.wrap(text, width=max_chars, break_long_words=False)
        return (wrapped[0] + "…") if len(wrapped) > 1 else text

def draw_rotated_label(base_img, text, x, y, angle=-45):
    """顺时针45度绘制标签。PIL rotate 正值逆时针，所以传 -45。"""
    label = smart_wrap(text, 12)
    bbox = FONT_SMALL.getbbox(label)
    tw, th = bbox[2] - bbox[0] + 8, bbox[3] - bbox[1] + 8
    txt_img = Image.new('RGBA', (tw, th), (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    txt_draw.text((4, 4), label, fill=(0, 0, 0, 255), font=FONT_SMALL)
    rot = txt_img.rotate(angle, expand=True, resample=Image.BICUBIC)
    base_img.paste(rot, (int(x), int(y)), rot)

for ci, (name, total) in enumerate(sorted_cust):
    gx = plot_x0 + ci * (bar_group_w + group_gap) + group_gap // 2
    for mi, m in enumerate(available_months):
        val = cust_month[name].get(m, 0)
        bx = gx + mi * bar_w
        bar_h = (val / y_max) * PLOT_H if y_max > 0 else 0
        by = plot_y1 - bar_h
        color = MONTH_COLORS[mi % 12]
        draw.rectangle([bx, by, bx + bar_w - 1, plot_y1], fill=color)

        if bar_h > 10:
            label = f"${val:,.0f}"
            bbox = draw.textbbox((0, 0), label, font=FONT_SMALL)
            tw = bbox[2] - bbox[0]
            draw.text((bx + bar_w/2 - tw/2, by - 14), label, fill=(0, 0, 0), font=FONT_SMALL)

    # ---- 补丁：横轴客户名顺时针45度 ----
    label_x = gx + bar_group_w / 2 - 8
    label_y = plot_y1 + 18
    draw_rotated_label(img, name, label_x, label_y, angle=-45)

# 图例
ly = H - 45
lx = MARGIN_L
for mi, m in enumerate(available_months):
    color = MONTH_COLORS[mi % 12]
    draw.rectangle([lx, ly, lx + 14, ly + 14], fill=color)
    draw.text((lx + 18, ly), f"{m}月", fill=(0, 0, 0), font=FONT_SMALL)
    lx += 50

out_path = f"func3_monthly_{SALES_NAME}.png"
img.save(out_path)
print(f"功能三图片已生成: {out_path}")
