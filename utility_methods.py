import numpy as np
import matplotlib.pyplot as plt
import math
import tkinter as tk
from tkinter import ttk
import os

plt.style.use('dark_background')

PURE_WHITE = '#FFFFFF'

# Dark & Neutral UI Shades
DARK_BG = '#111111' # Primary deep-black app and chart canvas background.
CHARCOAL_TEXT = '#1a1a1a' # High-contrast dark ink text used on light export charts and tooltip cards.
GRID_SLATE = '#262626' # Subtle dark-mode gridlines and inactive button surfaces.
LIGHT_GRID = '#dddddd' # Subtle light-mode gridlines for exported PNG charts.
SILVER_TEXT = '#e0e0e0' # Crisp off-white foreground text and labels on dark backgrounds.

# Light-Theme Export Counterparts (High-Contrast Print/PNG)
PRINT_CYAN = '#0088AA' # High-contrast teal/cyan counterpart to NEON_CYAN on white backgrounds.
PRINT_PINK = '#D60066' # High-contrast magenta-pink counterpart to NEON_PINK on white backgrounds.
PRINT_GREEN = '#009944' # High-contrast emerald counterpart to NEON_GREEN on white backgrounds.
PRINT_AMBER = '#B37700' # High-contrast gold/amber counterpart to NEON_AMBER on white backgrounds.
LIGHT_LEGEND_BG = '#f4f4f4' # Soft off-white background used for the chart legend box on light-theme PNG
                            # exports so it separates subtly from the PURE_WHITE (#FFFFFF) canvas.

# Neutral Divider & Muted Label Grays
DIVIDER_GRAY = '#666666' # Medium neutral gray used for the vertical Actual | Forecast boundary line (axvline).
MUTED_GRAY = '#888888' # Slightly lighter muted gray used for the "Forecast →" label and forecast month badges (Fcst).
AXIS_GRAY = '#444444' # Medium-dark neutral gray used for the visible bottom/left chart axis spines and subtle footer hint text.

# Pie chart Subtitle & Wedge Edge Shades
SLATE_GRAY = '#555555' # Medium-dark neutral gray used for secondary subtitles on light backgrounds.
SOFT_GRAY = '#aaaaaa' # Light-medium gray used for secondary subtitles and inactive button text on dark backgrounds.
DARK_EDGE = '#222222' # Deep charcoal used for crisp slice borders (edge_color) between dark-mode pie wedges.

# Dialog, Control Surface & Modal Surface Shade
MODAL_BG = '#1c1c1c' # Elevated dark charcoal background used for popup dialogs and help windows so they
                     # stand out cleanly above the DARK_BG main
ZOOM_BG = '#161616' # Elevated near-black surface used for the Sanctuary Zoom Ledger modal and floating tooltips
                    # so they stand out cleanly above the DARK_BG main canvas.

# Treeview Selection Surface Shade
SELECT_TEAL_BG = '#263842' # Deep slate-teal background used for selected rows inside the Filter.Treeview widget
                           # so NEON_CYAN (#00F0FF) selected text stands out clearly without harsh glare.

# Recessed Scroll Surface & Border Shades
RECESSED_BG = '#141414' # Slightly deeper dark surface used inside scrollable text frames and canvas viewports so they
                        # sit recessed within MODAL_BG (#1c1c1c).
CONTROL_BG = '#1e1e1e'  # Dark charcoal fill used for interactive input fields, radio/checkbutton selection wells
                        # (selectcolor), and toggle buttons.
BORDER_GRAY = '#333333' # Subtle dark gray used for 1px container borders (highlightbackground) and thin horizontal
                        # dividers.
BUTTON_BG = '#2a2a2a'   # Medium-dark charcoal fill used for secondary action buttons (Browse..., Cancel, ? Info)
                        # and custom scrollbar thumb handles so they stand out cleanly against MODAL_BG
                        # (#1c1c1c) and CONTROL_BG (#1e1e1e).

# Alert Highlight Background Shade
ALERT_CRIMSON_BG = '#550011' # Deep crimson background used to highlight over-budget or negative-balance rows (red_lbl)
                             # behind NEON_RED (#FF3300) foreground text.

# Pinned Tooltip Status Accent
PINNED_TEAL = '#006688' # Deep ocean teal used for the [Pinned — Drag to Move | Click to Unpin] status prompt on the
                        # light-gray (SILVER_TEXT) tooltip card so it stays crisp and easy to read when pinned.

# Hover Accent Shades
HOVER_MAGENTA = '#ff66ff' # Lighter glowing tint of NEON_MAGENTA used on button press/hover (activebackground).
HOVER_CYAN = '#66f5ff'    # Lighter glowing tint of NEON_CYAN used on button press/hover (activebackground).
HOVER_GOLD = '#ffcc66'    # Lighter glowing tint of NEON_GOLD used on button press/hover (activebackground).
HOVER_GREEN = '#66ff99'   # Lighter glowing tint of NEON_GREEN used on button press/hover (activebackground).

# Secondary Italic & Hint Label Shade
HINT_GRAY = '#777777' # Medium neutral gray used for italic implied-remainder rows (Other Income, Other Expenses),
                      # zoom footer instructions, and scrollbar arrow indicators.
SUBITEM_GRAY = '#bbbbbb' # Soft light gray used for indented subcategory detail lines (• ...) inside the Sanctuary
                         # Zoom Ledger modal so they recede slightly below bold PURE_WHITE parent headers.
ROW_HOVER_BG = '#242424' # Subtle dark-gray highlight used on mouse hover (<Enter>) for expandable category rows
                         # inside the Sanctuary Zoom Ledger modal.

# Colors used for buttons, pie wedges and linechart lines
NEON_PINK = '#FF007F'     # Expenses / Negative / Expense Accent
NEON_CYAN = '#00F0FF'     # Income / Primary Action / Active Accent
NEON_MAGENTA = '#FF00FF'  # Secondary Series / Category Palette
NEON_PURPLE = '#7000FF'   # Tertiary Series / Category Palette
NEON_AMBER = '#FFB800'    # Budget Benchmark / Forecast Warning
NEON_GREEN = '#00FF66'    # Positive Net Surplus / Actual Badge
NEON_RED = '#FF3300'      # Deficit / Alert / Over-Budget
NEON_VIOLET = '#B366FF'   # Bright electric violet/lavender used as an extra category accent.
NEON_ORANGE = '#FF6600'   # Vivid neon tangerine/orange used as an extra category accent.
NEON_SKY = '#33CCFF'      # Bright electric sky blue used as an extra category accent.
NEON_ROSE = '#FF66B2'     # Bright pastel-neon rose pink used as an extra category accent.
NEON_GOLD = '#FFaa00'     # Warm gold/orange used for the primary Create / Update CSV File button (btn_save) and forecast status badges (Fcst).

NEON_COLORS = [
    NEON_PINK,
    NEON_CYAN,
    NEON_MAGENTA,
    NEON_PURPLE,
    NEON_AMBER,
    NEON_GREEN,
    NEON_RED,
    NEON_VIOLET,
    NEON_ORANGE,
    NEON_SKY,
    NEON_ROSE,
    NEON_GOLD
]


def create_smart_pie(fig, sizes, labels, total_value, title, title_color, current_font_size=9, y_threshold=0.16, theme="dark"):
    is_light = theme in ("white", "transparent")
    bg_color = "none" if theme == "transparent" else (PURE_WHITE if theme == "white" else DARK_BG)
    fg_color = CHARCOAL_TEXT if is_light else "white"
    sub_color = SLATE_GRAY if is_light else SOFT_GRAY
    edge_color = PURE_WHITE if is_light else DARK_EDGE

    # Deepen bright neon title colors slightly on light backgrounds so they read crisply in print/email
    effective_title_color = title_color
    if is_light:
        if title_color.upper() == NEON_CYAN:
            effective_title_color = PRINT_CYAN
        elif title_color.upper() == NEON_PINK:
            effective_title_color = PRINT_PINK

    # 1. COMPLETELY PURGE THE OLD GRAPH AND ALL LINGERING TEXT ENTIRELY
    fig.clf()
    fig.patch.set_facecolor(bg_color)

    # Stretch the internal subplot grid box to fill 100% of the canvas height and width space,
    # pulling the left margin right up to the edge and expanding the right side wide for text.
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.02, top=0.82)

    # Create our clean drawing canvas inside the newly stretched figure
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg_color)

    if not sizes or sum(sizes) == 0:
        ax.text(0, 0, "No Data Available", color=fg_color, weight="bold", ha="center")
        ax.set_title(title, color=effective_title_color, fontsize=12, weight='bold', pad=10)
        ax.axis('off')
        return []

    # Lock the slice radius to 1.0. Because the subplot adjustments stretch the drawing box,
    # a 1.0 radius circle naturally swells outward to fill the full vertical height available.
    wedges, _ = ax.pie(
        sizes, colors=NEON_COLORS[:len(sizes)], startangle=270, counterclock=False,
        radius=1.0,
        wedgeprops=dict(edgecolor=edge_color, linewidth=2, antialiased=True, width=None)
    )

    left_side_labels = []
    right_side_labels = []
    lowest_label_y = -1.2

    for i, w in enumerate(wedges):
        percentage = (sizes[i] / total_value) * 100 if total_value > 0 else 0
        ang = (w.theta2 - w.theta1) / 2. + w.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))

        label_text = f"{labels[i]}\n${sizes[i]:,.0f} ({percentage:.1f}%)"

        if percentage >= 15.0:  # Inside-wedge text placement
            ix = w.r * 0.55 * x
            iy = w.r * 0.55 * y
            ax.text(ix, iy, label_text, color="black", weight="bold", fontsize=current_font_size,
                    ha='center', va='center')
        else:
            # Re-calibrated callout target distance to sit perfectly flush outside our larger circle
            target_y = w.r * 1.08 * y
            if x > 0:
                right_side_labels.append(
                    {'y': target_y, 'text': label_text, 'color': w.get_facecolor(), 'w': w, 'x': x, 'y_orig': y})
            else:
                left_side_labels.append(
                    {'y': target_y, 'text': label_text, 'color': w.get_facecolor(), 'w': w, 'x': x, 'y_orig': y})

    def adjust_side_spacing(label_list, min_gap):
        if not label_list: return
        label_list.sort(key=lambda item: item['y'], reverse=True)
        for idx in range(1, len(label_list)):
            prev_y = label_list[idx - 1]['y']
            current_y = label_list[idx]['y']
            if (prev_y - current_y) < min_gap:
                label_list[idx]['y'] = prev_y - min_gap

    adjust_side_spacing(right_side_labels, min_gap=0.22)
    adjust_side_spacing(left_side_labels, min_gap=0.22)

    for side_list, x_side in [(right_side_labels, 1), (left_side_labels, -1)]:
        horizontal_align = "left" if x_side > 0 else "right"
        for item in side_list:
            w = item['w']
            if item['y'] < lowest_label_y:
                lowest_label_y = item['y']

            # Snaps the start of the line perfectly flush onto the expanded 1.0 radius rim
            x_start, y_start = w.r * 0.98 * item['x'], w.r * 0.98 * item['y_orig']

            # Pulled in to 1.12 so a 3 o'clock label sits right beside the rim with a short, crisp shelf
            # and gives wide right-side category names plenty of room before the canvas edge.
            x_end = 1.12 * x_side

            # Variable-length radial ray extending directly to item['y'] (no vertical kink),
            # safely clamped between the rim and the horizontal shelf.
            min_reach = abs(x_start) + 0.03
            max_reach = abs(x_end) - 0.03
            if abs(item['y_orig']) > 0.08:
                r_kink = item['y'] / item['y_orig']
                raw_x_kink = r_kink * item['x']
                if x_side > 0:
                    x_kink = min(max_reach, max(min_reach, raw_x_kink))
                else:
                    x_kink = max(-max_reach, min(-min_reach, raw_x_kink))
            else:
                x_kink = (min_reach + 0.03) * x_side

            ax.plot([x_start, x_kink, x_end],
                    [y_start, item['y'], item['y']],
                    color=item['color'], linewidth=1.5, zorder=1)

            ax.text(x_end + (0.04 * x_side), item['y'], item['text'],
                    color=fg_color, weight="bold", fontsize=current_font_size,
                    ha=horizontal_align, va="center")

    # Anchoring at x=0.0 centers the main title directly over the pie circle's center axis
    # 2. WIDTH-DRIVEN TITLE FONT SCALING:
    # Reads the actual width of the chart figure in inches (~3.8" at min width up to ~7.5" at max)
    # Scales smoothly from 11.0pt (no left clipping) up to 18.0pt when maximized
    fig_w = fig.get_figwidth()
    dynamic_title_size = min(18.0, max(10.5, 10.5 + ((fig_w - 3.8) * 2.0)))

    ax.text(0.0, 1.38, title,
            color=effective_title_color, fontsize=dynamic_title_size, weight='bold',
            horizontalalignment='center', verticalalignment='center')

    # 3. Keep the Total subtitle pinned right below it on the exact same x=0.0 centerline
    dynamic_sub_size = min(10.5, max(8.0, dynamic_title_size * 0.58))
    ax.text(0.0, 1.22, f"Total: ${total_value:,.0f}",
            color=sub_color, fontname='Arial', fontsize=dynamic_sub_size, weight='bold',
            horizontalalignment='center', verticalalignment='center')

    # Pad dynamically below the lowest label's vertical midpoint to clear the bottom half of the 2-line text block
    dynamic_bottom_limit = lowest_label_y - 0.18

    ax.set_xlim(-1.35, 2.25)
    ax.set_ylim(dynamic_bottom_limit, 1.48)
    ax.axis('off')

    return wedges, dynamic_bottom_limit


def create_monthly_line_chart(fig, months, inc_arr, exp_arr, is_fc_flags, title_text, mode_tag, surplus_tag,
                              theme="dark", monthly_budget=0.0, monthly_budget_inc=0.0, is_cumulative=True,
                              custom_series=None, sel_kind=None, show_filtered_budgets=True):
    """Renders a synchronized 72%/28% Top/Bottom dual-panel chart:
    Top: Gross Income vs. Expenses (or custom filtered category/subcategory lines) + Budget benchmark.
    Bottom: Magnified Net Profit/Loss (or Variance vs. Budget when filtered) above/below $0 waterline.
    """
    is_light = theme in ("white", "transparent")
    bg_color = "none" if theme == "transparent" else (PURE_WHITE if theme == "white" else DARK_BG)
    fg_color = CHARCOAL_TEXT if is_light else SILVER_TEXT
    grid_color = LIGHT_GRID if is_light else GRID_SLATE
    inc_color = PRINT_CYAN if is_light else NEON_CYAN
    exp_color = PRINT_PINK if is_light else NEON_PINK
    pos_color = PRINT_GREEN if is_light else NEON_GREEN
    bud_color = PRINT_AMBER if is_light else NEON_AMBER

    fig.patch.set_facecolor(bg_color)
    if len(fig.axes) == 2:
        fig.texts.clear()
        fig.legends.clear()
        ax_top, ax_bot = fig.axes[0], fig.axes[1]
        ax_top.cla()
        ax_bot.cla()
    else:
        fig.clf()
        fig.patch.set_facecolor(bg_color)
        gs = fig.add_gridspec(2, 1, height_ratios=[2.6, 1.0], hspace=0.14)
        ax_top = fig.add_subplot(gs[0])
        ax_bot = fig.add_subplot(gs[1], sharex=ax_top)

    for ax in (ax_top, ax_bot):
        ax.set_facecolor(bg_color)

    x = np.arange(len(months))
    first_fc_idx = next((i for i, flag in enumerate(is_fc_flags) if flag), len(months))
    is_filtered = bool(custom_series)

    # --- TOP PANEL ---
    bud_arr = None
    if (monthly_budget > 0 or is_filtered) and len(months) > 0:
        bud_arr = np.array([monthly_budget * (i + 1) for i in range(len(months))]) if is_cumulative else np.full(len(months), monthly_budget)
        if not is_filtered or (show_filtered_budgets and len(custom_series) == 1):
            ax_top.plot(x, bud_arr, color=bud_color, linestyle='--', linewidth=1.3, alpha=0.55, zorder=1)
            ax_top.text(x[-1], bud_arr[-1], f"  Budget (${monthly_budget:,.0f}/mo)", color=bud_color, alpha=0.80,
                        fontsize=8.5, fontweight='bold', va='center', ha='left', clip_on=False)

    show_single_bud = (not is_filtered) or (show_filtered_budgets and len(custom_series) == 1)
    all_top_vals = [float(np.max(bud_arr))] if (bud_arr is not None and show_single_bud) else [1.0]
    min_top_vals = [float(np.min(bud_arr))] if (bud_arr is not None and show_single_bud) else [0.0]

    if is_filtered:
        draw_indiv_buds = (show_filtered_budgets and len(custom_series) > 1)
        for s in custom_series:
            vals = s["values"]
            col = s["color"]
            lbl = s["label"]
            all_top_vals.append(float(np.max(vals)) if len(vals) else 0.0)
            min_top_vals.append(float(np.min(vals)) if len(vals) else 0.0)

            s_bud_mo = float(s.get("bud_mo", 0.0))
            if draw_indiv_buds and abs(s_bud_mo) > 0.01 and len(months) > 0:
                s_bud_arr = np.array([s_bud_mo * (i + 1) for i in range(len(months))]) if is_cumulative else np.full(len(months), s_bud_mo)
                all_top_vals.append(float(np.max(s_bud_arr)))
                min_top_vals.append(float(np.min(s_bud_arr)))
                ax_top.plot(x, s_bud_arr, color=col, linestyle='--', linewidth=1.1, alpha=0.42, zorder=1)
                ax_top.text(x[-1], s_bud_arr[-1], f"  Bud (${s_bud_mo:,.0f}/mo)", color=col, alpha=0.75,
                            fontsize=7.5, fontweight='bold', va='center', ha='left', clip_on=False)

            if first_fc_idx > 0:
                ax_top.plot(x[:first_fc_idx], vals[:first_fc_idx], color=col, linewidth=2.4,
                            marker='o', markersize=5.5, label=lbl, zorder=3)
            if first_fc_idx < len(months):
                sb = max(0, first_fc_idx - 1)
                fc_lbl = lbl if first_fc_idx == 0 else f"{lbl} (Fcst)"
                ax_top.plot(x[sb:], vals[sb:], color=col, linewidth=1.9, linestyle=':',
                            marker='o', markersize=4, alpha=0.78, label=fc_lbl, zorder=3)

        if sel_kind == "mixed" and len(custom_series) > 1:
            net_arr = np.sum([(-s["values"] if s.get("is_exp") else s["values"]) for s in custom_series], axis=0)
        elif bud_arr is not None:
            tot_vals = np.sum([s["values"] for s in custom_series], axis=0)
            net_arr = (bud_arr - tot_vals) if sel_kind == "expense" else (tot_vals - bud_arr)
        else:
            net_arr = np.sum([s["values"] for s in custom_series], axis=0)
    else:
        all_top_vals.extend([float(np.max(inc_arr)), float(np.max(exp_arr))])
        net_arr = inc_arr - exp_arr
        if first_fc_idx > 0:
            xa = x[:first_fc_idx]
            ax_top.plot(xa, inc_arr[:first_fc_idx], color=inc_color, linewidth=2.5, marker='o', markersize=5.5, label="Income (Actual)", zorder=3)
            ax_top.plot(xa, exp_arr[:first_fc_idx], color=exp_color, linewidth=2.5, marker='o', markersize=5.5, label="Expenses (Actual)", zorder=3)
            ax_top.fill_between(xa, inc_arr[:first_fc_idx], exp_arr[:first_fc_idx], where=(inc_arr[:first_fc_idx] >= exp_arr[:first_fc_idx]), interpolate=True, color=inc_color, alpha=0.18, zorder=2)
            ax_top.fill_between(xa, inc_arr[:first_fc_idx], exp_arr[:first_fc_idx], where=(exp_arr[:first_fc_idx] > inc_arr[:first_fc_idx]), interpolate=True, color=exp_color, alpha=0.18, zorder=2)
        if first_fc_idx < len(months):
            sb = max(0, first_fc_idx - 1)
            xf = x[sb:]
            ax_top.plot(xf, inc_arr[sb:], color=inc_color, linewidth=1.9, linestyle=':', marker='o', markersize=4, alpha=0.75, label="Income (Forecast)", zorder=3)
            ax_top.plot(xf, exp_arr[sb:], color=exp_color, linewidth=1.9, linestyle=':', marker='o', markersize=4, alpha=0.75, label="Expenses (Forecast)", zorder=3)
            ax_top.fill_between(xf, inc_arr[sb:], exp_arr[sb:], where=(inc_arr[sb:] >= exp_arr[sb:]), interpolate=True, color=inc_color, alpha=0.07, zorder=2)
            ax_top.fill_between(xf, inc_arr[sb:], exp_arr[sb:], where=(exp_arr[sb:] > inc_arr[sb:]), interpolate=True, color=exp_color, alpha=0.07, zorder=2)

    max_data_y = max(all_top_vals)
    min_data_y = min(min_top_vals)
    span_y = max(max_data_y - min_data_y, abs(max_data_y) * 0.25, 1.0)
    step = 50000.0 if span_y > 100000 else (5000.0 if span_y > 15000 else (1000.0 if span_y > 2000 else 250.0))

    min_headroom = max(step * 0.6, abs(max_data_y) * 0.08)
    y_upper = max(math.ceil((max_data_y + min_headroom) / step) * step, step)
    y_lower = (math.floor(min_data_y / step) * step) if min_data_y < 0 else 0
    if y_lower < 0:
        ax_top.axhline(0, color=DIVIDER_GRAY, linewidth=0.9, linestyle='-', zorder=1)
    ax_top.set_ylim(y_lower, y_upper)

    if 0 < first_fc_idx < len(months):
        div_x = first_fc_idx - 0.5
        ax_top.axvline(x=div_x, color=DIVIDER_GRAY, linestyle='--', linewidth=1.1, zorder=1)
        ax_bot.axvline(x=div_x, color=DIVIDER_GRAY, linestyle='--', linewidth=1.1, zorder=1)

        y_span = max(y_upper - y_lower, 1.0)
        near_idxs = [i for i in (first_fc_idx - 1, first_fc_idx) if 0 <= i < len(months)]
        local_vals = [v for i in near_idxs for v in (inc_arr[i], exp_arr[i])]
        if custom_series:
            local_vals.extend(s["values"][i] for s in custom_series for i in near_idxs if i < len(s["values"]))

        top_gap = y_upper - max(local_vals) if local_vals else y_span
        bot_gap = min(local_vals) - y_lower if local_vals else 0.0

        if bot_gap > top_gap:
            lbl_y, lbl_va = y_lower + 0.03 * y_span, 'bottom'
        else:
            lbl_y, lbl_va = y_upper - 0.03 * y_span, 'top'

        if first_fc_idx >= len(months) - 1:
            ax_top.text(div_x - 0.12, lbl_y, "Forecast →", color=MUTED_GRAY, fontsize=8, fontweight='bold', ha='right', va=lbl_va)
        else:
            ax_top.text(div_x + 0.12, lbl_y, "Forecast →", color=MUTED_GRAY, fontsize=8, fontweight='bold', ha='left', va=lbl_va)

    ax_top.set_title(f"{title_text} ({mode_tag} • {surplus_tag})", color=fg_color, fontsize=13.5, fontweight='bold', pad=12)
    ax_top.tick_params(axis='x', labelbottom=False, colors=fg_color)
    ax_top.tick_params(axis='y', colors=fg_color, labelsize=8.5)
    ax_top.yaxis.set_major_formatter('${x:,.0f}')
    ax_top.grid(True, linestyle='--', linewidth=0.6, color=grid_color)
    leg = ax_top.legend(loc='upper left', frameon=True, facecolor=CHARCOAL_TEXT if not is_light else LIGHT_LEGEND_BG, edgecolor=BORDER_GRAY, fontsize=8)
    for txt in leg.get_texts():
        txt.set_color(fg_color)

    # --- BOTTOM PANEL: MAGNIFIED NET P&L OR VARIANCE VS. BUDGET ---
    ax_bot.axhline(0, color=MUTED_GRAY if not is_light else SLATE_GRAY, linewidth=1.1, zorder=2)
    bud_net_mo = 0.0 if is_filtered else (monthly_budget_inc - monthly_budget)
    bud_net_arr = np.array([bud_net_mo * (i + 1) for i in range(len(months))]) if is_cumulative else np.full(len(months), bud_net_mo)
    if not is_filtered and abs(bud_net_mo) > 1.0:
        ax_bot.plot(x, bud_net_arr, color=bud_color, linestyle='--', linewidth=1.1, alpha=0.65, zorder=2)
        ax_bot.text(x[-1], bud_net_arr[-1], "  Budget Net", color=bud_color, alpha=0.85, fontsize=8, fontweight='bold', va='center', ha='left', clip_on=False)

    if is_cumulative:
        if first_fc_idx > 0:
            xa = x[:first_fc_idx]
            ax_bot.plot(xa, net_arr[:first_fc_idx], color=fg_color, linewidth=1.8, marker='o', markersize=4.5, zorder=4)
            ax_bot.fill_between(xa, net_arr[:first_fc_idx], 0, where=(net_arr[:first_fc_idx] >= 0), interpolate=True, color=pos_color, alpha=0.28, zorder=3)
            ax_bot.fill_between(xa, net_arr[:first_fc_idx], 0, where=(net_arr[:first_fc_idx] < 0), interpolate=True, color=exp_color, alpha=0.28, zorder=3)
        if first_fc_idx < len(months):
            sb = max(0, first_fc_idx - 1)
            xf = x[sb:]
            ax_bot.plot(xf, net_arr[sb:], color=fg_color, linewidth=1.4, linestyle=':', marker='o', markersize=3.5, alpha=0.75, zorder=4)
            ax_bot.fill_between(xf, net_arr[sb:], 0, where=(net_arr[sb:] >= 0), interpolate=True, color=pos_color, alpha=0.12, zorder=3)
            ax_bot.fill_between(xf, net_arr[sb:], 0, where=(net_arr[sb:] < 0), interpolate=True, color=exp_color, alpha=0.12, zorder=3)
    else:
        bar_colors = [pos_color if v >= 0 else exp_color for v in net_arr]
        bar_alphas = [0.35 if is_fc else 0.80 for is_fc in is_fc_flags]
        for xi, val, col, alp in zip(x, net_arr, bar_colors, bar_alphas):
            ax_bot.bar(xi, val, width=0.52, color=col, alpha=alp, zorder=3)

    ax_bot.set_ylabel("Vs. Budget" if is_filtered else "Net P&L", color=fg_color, fontsize=8.5, fontweight='bold')
    ax_bot.set_xticks(x)
    ax_bot.set_xticklabels(months, color=fg_color, fontweight='bold', fontsize=9)
    ax_bot.tick_params(axis='y', colors=fg_color, labelsize=8)
    ax_bot.yaxis.set_major_formatter('${x:,.0f}')
    ax_bot.grid(True, linestyle='--', linewidth=0.5, color=grid_color)
    max_abs_net = max(float(np.max(np.abs(net_arr))), float(np.max(np.abs(bud_net_arr))), 500.0)
    bot_step = 5000.0 if max_abs_net > 10000 else (1000.0 if max_abs_net > 2000 else 250.0)
    y_pad = math.ceil((max_abs_net * 1.25) / bot_step) * bot_step
    ax_bot.set_ylim(-y_pad, y_pad)

    for ax in (ax_top, ax_bot):
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax.spines[spine].set_color(AXIS_GRAY)

    v_top = ax_top.axvline(x=0, color=MUTED_GRAY, linestyle=':', linewidth=1.2, visible=False, zorder=5)
    v_bot = ax_bot.axvline(x=0, color=MUTED_GRAY, linestyle=':', linewidth=1.2, visible=False, zorder=5)
    d_top, = ax_top.plot([], [], marker='o', markersize=10, markerfacecolor='none', markeredgewidth=2.2, visible=False, zorder=6)
    d_bot, = ax_bot.plot([], [], marker='o', markersize=10, markerfacecolor='none', markeredgewidth=2.2, visible=False, zorder=6)
    fig.subplots_adjust(left=0.09, right=0.88, top=0.90, bottom=0.10)
    return ax_top, ax_bot, v_top, v_bot, d_top, d_bot

def show_import_help(parent, title, guide_text):
    """Opens a clean dark-themed help popup with an anchored bottom button
    and an auto-hiding vertical scrollbar when text exceeds the viewing area.
    """
    help_win = tk.Toplevel(parent)
    help_win.title(title)
    help_win.configure(bg=MODAL_BG, highlightbackground=NEON_CYAN, highlightthickness=1)
    help_win.geometry("540x430")
    help_win.minsize(420, 280)
    help_win.transient(parent)
    help_win.grab_set()

    mx = parent.winfo_rootx() + (parent.winfo_width() // 2) - 270
    my = parent.winfo_rooty() + (parent.winfo_height() // 2) - 215
    help_win.geometry(f"+{max(20, mx)}+{max(20, my)}")

    def close_help():
        help_win.grab_release()
        help_win.destroy()

    # 1. Anchor header to top and "Got It" button to bottom FIRST so resizing never hides them
    tk.Label(help_win, text=title.upper(), bg=MODAL_BG, fg=NEON_CYAN,
             font=('Arial', 10, 'bold')).pack(side="top", pady=(14, 8))

    btn_bar = tk.Frame(help_win, bg=MODAL_BG)
    btn_bar.pack(side="bottom", fill="x", pady=(8, 14))
    tk.Button(btn_bar, text="Got It", command=close_help, bg=NEON_CYAN, fg='black',
              font=('Arial', 9, 'bold'), padx=22, pady=5, bd=0, cursor="hand2").pack()

    # 2. Middle scrollable text container fills remaining space cleanly
    txt_frame = tk.Frame(help_win, bg=RECESSED_BG, highlightbackground=BORDER_GRAY, highlightthickness=1)
    txt_frame.pack(side="top", fill="both", expand=True, padx=18, pady=4)

    canvas = tk.Canvas(txt_frame, bg=RECESSED_BG, bd=0, highlightthickness=0)
    v_scroll = ttk.Scrollbar(txt_frame, orient="vertical", command=canvas.yview,
                             style="Dark.Vertical.TScrollbar")
    canvas.configure(yscrollcommand=v_scroll.set)
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg=RECESSED_BG)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    lbl = tk.Label(inner, text=guide_text, bg=RECESSED_BG, fg=SILVER_TEXT,
                   font=('Arial', 9), justify="left", anchor="nw", padx=12, pady=10)
    lbl.pack(fill="both", expand=True)

    def sync_scroll(event=None):
        c_w = canvas.winfo_width()
        if c_w > 30:
            canvas.itemconfig(win_id, width=c_w)
            lbl.config(wraplength=c_w - 24)
        help_win.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        if inner.winfo_reqheight() > canvas.winfo_height():
            if not v_scroll.winfo_ismapped():
                v_scroll.pack(side="right", fill="y")
        else:
            v_scroll.pack_forget()
            canvas.yview_moveto(0)

    canvas.bind("<Configure>", sync_scroll)
    inner.bind("<Configure>", sync_scroll)

    def on_wheel(event):
        if inner.winfo_reqheight() > canvas.winfo_height():
            step = 1 if (event.num == 5 or event.delta < 0) else -1
            canvas.yview_scroll(step, "units")

    help_win.bind("<MouseWheel>", on_wheel)
    help_win.bind("<Button-4>", on_wheel)
    help_win.bind("<Button-5>", on_wheel)
    help_win.bind("<Escape>", lambda e: close_help())

def run_with_busy_banner(parent, message, task_fn):
    """Displays a centered dark neon status banner and watch cursor while running a blocking file task."""
    parent.config(cursor="watch")
    overlay = tk.Frame(parent, bg=ZOOM_BG, highlightbackground=NEON_CYAN, highlightthickness=1)
    tk.Label(
        overlay, text=message, bg=ZOOM_BG, fg=NEON_CYAN,
        font=('Arial', 11, 'bold'), padx=30, pady=18
    ).pack()
    overlay.place(relx=0.5, rely=0.5, anchor="center")
    overlay.lift()
    parent.update_idletasks()

    req_w = overlay.winfo_reqwidth() + 50
    cur_w = parent.winfo_width()
    if req_w > cur_w:
        cur_h = parent.winfo_height()
        new_x = max(10, parent.winfo_x() - (req_w - cur_w) // 2)
        parent.geometry(f"{req_w}x{cur_h}+{new_x}+{parent.winfo_y()}")

    parent.update()
    try:
        return task_fn()
    finally:
        overlay.destroy()
        parent.config(cursor="")

def get_user_desktop():
    """Returns the true active Desktop folder on Windows (handling OneDrive/redirected Desktops)
    with clean fallbacks for non-Windows or restricted environments.
    """
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            CSIDL_DESKTOPDIRECTORY = 0x0010
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buf) == 0:
                if buf.value and os.path.isdir(buf.value):
                    return buf.value
        except Exception:
            pass

    home = os.path.expanduser("~")
    for candidate in (
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "Desktop"),
        os.environ.get("PUBLIC", "") and os.path.join(os.environ["PUBLIC"], "Desktop"),
    ):
        if candidate and os.path.isdir(candidate):
            return candidate
    return os.getcwd()
