#!/usr/bin/env python3
"""功能一：多维大盘汇总 + 当月Top10客户排行 PIL 图片表格 + 大盘日用量趋势图

补丁记录：
- v3: 大盘汇总改为【本季度/本月/本周/当年累计】+ MoM 环比
- v3: 客户排行改为按【当月用量】Top10，列改为 本月/上月/月环比
- v3: 金额前缀统一为 "$" (USD)
"""
import csv, os, sys, statistics
from datetime import datetime, timedelta
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

SALES_NAME = sys.argv[1] if len(sys.argv) > 1 else "扶铿"
CURRENT_YEAR = sys.argv[2] if len(sys.argv) > 2 else "2026"
LAST_YEAR = str(int(CURRENT_YEAR) - 1)
QUARTER_END_MONTH = int(sys.argv[3]) if len(sys.argv) > 3 else 6
CURRENT_QUARTER = "Q2" if QUARTER_END_MONTH <= 6 else ("Q3" if QUARTER_END_MONTH <= 9 else "Q4")

# ---- 当前日期（确定本月/本周） ----
TODAY = datetime.now()
CUR_MONTH = TODAY.month
CUR_YEAR = TODAY.year
CUR_WEEK = TODAY.isocalendar()[1]
# 季度月份范围
Q_START = (QUARTER_END_MONTH - 1) // 3 * 3 + 1  # Q2->4, Q3->7, Q4->10
Q_END = QUARTER_END_MONTH

FONT_REG = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size=14, index=2)
FONT_BOLD = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", size=14, index=2)
FONT_TITLE = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", size=18, index=2)
FONT_SMALL = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", size=12, index=2)

# --- 读取数据 ---
rows = []
with open(f"ali_all_local_data_{SALES_NAME}.csv", newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        rows.append(r)

# ---- 大盘多维汇总计算 ----
ytd_total = 0.0          # 当年累计
q_total = 0.0            # 本季度累计
m_total = 0.0            # 本月累计
w_total = 0.0            # 本周累计
last_m_total = 0.0       # 上月累计

daily_total = defaultdict(float)

for r in rows:
    if r['year'] != CURRENT_YEAR:
        continue
    amt = float(r['pretaxgrossamount'])
    ytd_total += amt
    daily_total[r['cost_date']] += amt
    
    m = int(r['month'])
    if Q_START <= m <= Q_END:
        q_total += amt
    if m == CUR_MONTH:
        m_total += amt
    if m == CUR_MONTH - 1:
        last_m_total += amt
    # 本周判断：ISO week match
    try:
        dt = datetime.strptime(r['cost_date'], '%Y-%m-%d')
        if dt.isocalendar()[1] == CUR_WEEK and dt.year == CUR_YEAR:
            w_total += amt
    except:
        pass

# MoM 环比
mom = (m_total - last_m_total) / last_m_total if last_m_total > 0 else None

# ---- 客户排行：按当月用量 Top10 ----
cust_month = defaultdict(float)   # 本月
cust_last_month = defaultdict(float)  # 上月

for r in rows:
    if r['year'] != CURRENT_YEAR:
        continue
    amt = float(r['pretaxgrossamount'])
    m = int(r['month'])
    name = r['customer_name']
    if m == CUR_MONTH:
        cust_month[name] += amt
    if m == CUR_MONTH - 1:
        cust_last_month[name] += amt

top10 = sorted(cust_month.items(), key=lambda x: x[1], reverse=True)[:10]

# --- 绘制表格 ---
HEADER_BG = (68, 114, 196)
HEADER_FG = (255, 255, 255)
ZEBRA_LIGHT = (242, 247, 251)
ZEBRA_WHITE = (255, 255, 255)
HIGHLIGHT_BG = (214, 228, 240)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
RED = (220, 50, 50)

ROW_H = 28
PAD_X = 10
PAD_Y = 6
TITLE_H = 40
SUBTITLE_H = 24
GAP = 20
SAFETY_MARGIN = 60

# ====== 表1：大盘多维汇总 ======
headers_mkt = ["维度", "金额 (USD)", "MoM 环比"]
col_w_mkt = [180, 180, 180]

# 数据行：本季度、本月、本周、当年累计
mkt_rows = [
    ("本季度累计", q_total),
    ("本月累计", m_total),
    ("本周累计", w_total),
    ("当年累计", ytd_total),
]

# ====== 表2：当月Top10客户 ======
headers_cust = ["#", "客户名称", "本月 (USD)", "上月 (USD)", "MoM"]
col_w_cust = [40, 200, 140, 140, 120]

total_data_rows = len(mkt_rows) + 1 + len(top10) + 1  # mkt表头+mkt行 + gap + cust表头 + top10行
img_w = max(sum(col_w_mkt) + PAD_X * 2, sum(col_w_cust) + PAD_X * 2) + 40
img_h = TITLE_H + SUBTITLE_H + ROW_H * total_data_rows + GAP * 4 + PAD_Y * 2 + SAFETY_MARGIN

img = Image.new("RGB", (img_w, img_h), "white")
draw = ImageDraw.Draw(img)

def fmt_usd(v):
    return f"${v:,.0f}"

def fmt_mom(cur, last):
    if last == 0 or last is None:
        return "新增" if cur > 0 else "—"
    pct = (cur - last) / last * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"

def draw_cell(x, y, w, h, text, font, bg=None, fg=BLACK, align="left", bold=False):
    if bg:
        draw.rectangle([x, y, x+w, y+h], fill=bg)
    f = FONT_BOLD if bold else font
    bbox = draw.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    ty = y + (h - th) // 2
    if align == "right":
        tx = x + w - tw - PAD_X
    elif align == "center":
        tx = x + (w - tw) // 2
    else:
        tx = x + PAD_X
    draw.text((tx, ty), text, fill=fg, font=f)

y = PAD_Y
draw_cell(PAD_X, y, img_w - PAD_X*2, TITLE_H, f"阿里云销售周报 — {SALES_NAME} ({CURRENT_YEAR}年)", FONT_TITLE, fg=HEADER_BG, bold=True)
y += TITLE_H
draw_cell(PAD_X, y, img_w - PAD_X*2, SUBTITLE_H, f"数据截止: {TODAY.strftime('%Y-%m-%d')} | 当月: {CUR_MONTH}月 | 本周: W{CUR_WEEK}", FONT_SMALL, fg=GRAY)
y += SUBTITLE_H + GAP

# ---- 大盘多维汇总表 ----
x_start = PAD_X + 20
for i, (hdr, cw) in enumerate(zip(headers_mkt, col_w_mkt)):
    draw_cell(x_start, y, cw, ROW_H, hdr, FONT_BOLD, bg=HEADER_BG, fg=HEADER_FG, align="center", bold=True)
    x_start += cw
y += ROW_H

for idx, (dim, val) in enumerate(mkt_rows):
    bg = ZEBRA_LIGHT if idx % 2 == 0 else ZEBRA_WHITE
    is_cum = dim == "当年累计"
    if is_cum:
        bg = HIGHLIGHT_BG
    x_start = PAD_X + 20
    draw_cell(x_start, y, col_w_mkt[0], ROW_H, dim, FONT_BOLD if is_cum else FONT_REG, bg=bg, bold=is_cum)
    x_start += col_w_mkt[0]
    draw_cell(x_start, y, col_w_mkt[1], ROW_H, fmt_usd(val), FONT_BOLD if is_cum else FONT_REG, bg=bg, align="right", bold=is_cum)
    x_start += col_w_mkt[1]
    # MoM 只在本月行显示，其他行留空
    mom_text = fmt_mom(m_total, last_m_total) if dim == "本月累计" else ""
    mom_color = RED if mom_text and mom_text.startswith("-") else BLACK
    draw_cell(x_start, y, col_w_mkt[2], ROW_H, mom_text, FONT_BOLD if is_cum else FONT_REG, bg=bg, align="center", bold=is_cum, fg=mom_color)
    y += ROW_H

y += GAP

# ---- 当月Top10客户排行表 ----
x_start = PAD_X + 20
for i, (hdr, cw) in enumerate(zip(headers_cust, col_w_cust)):
    draw_cell(x_start, y, cw, ROW_H, hdr, FONT_BOLD, bg=HEADER_BG, fg=HEADER_FG, align="center", bold=True)
    x_start += cw
y += ROW_H

for idx, (name, cost) in enumerate(top10, 1):
    last_cost = cust_last_month.get(name, 0)
    bg = ZEBRA_LIGHT if idx % 2 == 0 else ZEBRA_WHITE
    x_start = PAD_X + 20
    draw_cell(x_start, y, col_w_cust[0], ROW_H, str(idx), FONT_REG, bg=bg, align="center")
    x_start += col_w_cust[0]
    draw_cell(x_start, y, col_w_cust[1], ROW_H, name, FONT_REG, bg=bg)
    x_start += col_w_cust[1]
    draw_cell(x_start, y, col_w_cust[2], ROW_H, fmt_usd(cost), FONT_REG, bg=bg, align="right")
    x_start += col_w_cust[2]
    draw_cell(x_start, y, col_w_cust[3], ROW_H, fmt_usd(last_cost) if last_cost > 0 else "—", FONT_REG, bg=bg, align="right")
    x_start += col_w_cust[3]
    mom_text = fmt_mom(cost, last_cost)
    mom_color = RED if mom_text and mom_text.startswith("-") else BLACK
    draw_cell(x_start, y, col_w_cust[4], ROW_H, mom_text, FONT_REG, bg=bg, align="center", fg=mom_color)
    y += ROW_H

out_table = f"func1_quarterly_{SALES_NAME}.png"
img.save(out_table)
print(f"表格图片已生成: {out_table}")

# ========== 大盘日用量趋势图（Y轴动态范围 + 大额截断） ==========
if not daily_total:
    print("无大盘日数据，跳过趋势图")
    sys.exit(0)

sorted_dates = sorted(daily_total.keys())
values = [daily_total[d] for d in sorted_dates]

non_zero_vals = [v for v in values if v > 0]
if not non_zero_vals:
    print("所有日用量为0，跳过趋势图")
    sys.exit(0)

daily_avg = statistics.mean(non_zero_vals)
daily_max = max(non_zero_vals)

if daily_max > daily_avg * 3:
    DAILY_CAP = daily_avg * 3
    y_max2 = DAILY_CAP * 1.15
else:
    DAILY_CAP = daily_max
    y_max2 = daily_max * 1.15

W2, H2 = 1400, 500
MARGIN_L2, MARGIN_R2 = 80, 40
MARGIN_T2, MARGIN_B2 = 60, 80
PLOT_W2 = W2 - MARGIN_L2 - MARGIN_R2
PLOT_H2 = H2 - MARGIN_T2 - MARGIN_B2

img2 = Image.new("RGB", (W2, H2), "white")
draw2 = ImageDraw.Draw(img2)

title2 = f"{SALES_NAME} - 阿里云所有客户每日总用量趋势大盘 ({CURRENT_YEAR} {CURRENT_QUARTER})"
draw2.text((MARGIN_L2, 12), title2, fill=(68, 114, 196), font=FONT_TITLE)

plot_x0, plot_y0 = MARGIN_L2, MARGIN_T2
plot_x1, plot_y1 = MARGIN_L2 + PLOT_W2, MARGIN_T2 + PLOT_H2

draw2.rectangle([plot_x0, plot_y0, plot_x1, plot_y1], outline=(200, 200, 200))

for i in range(6):
    val = y_max2 * i / 5
    yp = plot_y1 - (val / y_max2) * PLOT_H2
    draw2.line([(plot_x0 - 5, yp), (plot_x0, yp)], fill=(180, 180, 180))
    draw2.text((plot_x0 - 65, yp - 7), f"${val:,.0f}", fill=GRAY, font=FONT_SMALL)
    if i > 0:
        draw2.line([(plot_x0, yp), (plot_x1, yp)], fill=(230, 230, 230))

n_dates = len(sorted_dates)
if n_dates > 1:
    tick_step = max(1, n_dates // 15)
    for i, d in enumerate(sorted_dates):
        xp = plot_x0 + (i / (n_dates - 1)) * PLOT_W2
        if i % tick_step == 0 or i == n_dates - 1:
            label = d[5:] if len(d) > 5 else d
            draw2.line([(xp, plot_y1), (xp, plot_y1 + 5)], fill=(180, 180, 180))
            draw2.text((xp - 15, plot_y1 + 8), label, fill=GRAY, font=FONT_SMALL)

# 绘制折线（使用截断后的Y值）
points = []
for i, d in enumerate(sorted_dates):
    xp = plot_x0 + (i / (n_dates - 1)) * PLOT_W2 if n_dates > 1 else plot_x0 + PLOT_W2 / 2
    actual_val = values[i]
    capped_val = min(actual_val, DAILY_CAP) if actual_val > 0 else 0
    yp = plot_y1 - (capped_val / y_max2) * PLOT_H2 if y_max2 > 0 else plot_y1
    points.append((xp, yp, actual_val))

DEEP_BLUE = (31, 80, 180)
for i in range(len(points) - 1):
    draw2.line([(points[i][0], points[i][1]), (points[i+1][0], points[i+1][1])], fill=DEEP_BLUE, width=3)

# 标注最高/最低点
non_zero_pts = [(xp, yp, v) for xp, yp, v in points if v > 0]
if non_zero_pts:
    max_pt = max(non_zero_pts, key=lambda p: p[2])
    min_pt = min(non_zero_pts, key=lambda p: p[2])
    for px, py, pv in [max_pt, min_pt]:
        draw2.ellipse([px-5, py-5, px+5, py+5], fill=DEEP_BLUE, outline="white")
        if pv > DAILY_CAP:
            label = f"${pv:,.0f} (⚠️大额续费)"
            label_color = RED
        else:
            label = f"${pv:,.0f}"
            label_color = BLACK
        draw2.text((px + 8, py - 16), label, fill=label_color, font=FONT_SMALL)

out_daily = f"func1_daily_market_{SALES_NAME}.png"
img2.save(out_daily)
print(f"大盘日趋势图已生成: {out_daily}")

# ---- 保存 Top10 客户列表供功能二/三使用 ----
with open(f"top10_monthly_{SALES_NAME}.txt", "w", encoding="utf-8") as f:
    for name, _ in top10:
        f.write(name + "\n")
print(f"Top10客户列表已保存: top10_monthly_{SALES_NAME}.txt")
