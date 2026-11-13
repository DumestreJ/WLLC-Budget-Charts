import numpy as np
import matplotlib.pyplot as plt
import math

plt.style.use('dark_background')
NEON_COLORS = ['#FF007F', '#00F0FF', '#FF00FF', '#7000FF', '#FFB800', '#00FF66', '#FF3300']


def create_smart_pie(fig, sizes, labels, total_value, title, title_color, current_font_size=9, y_threshold=0.16, theme="dark"):
    is_light = theme in ("white", "transparent")
    bg_color = "none" if theme == "transparent" else ("#FFFFFF" if theme == "white" else "#111111")
    fg_color = "#1a1a1a" if is_light else "white"
    sub_color = "#555555" if is_light else "#aaaaaa"
    edge_color = "#FFFFFF" if is_light else "#222222"

    # Deepen bright neon title colors slightly on light backgrounds so they read crisply in print/email
    effective_title_color = title_color
    if is_light:
        if title_color.upper() == "#00F0FF":
            effective_title_color = "#0088AA"
        elif title_color.upper() == "#FF007F":
            effective_title_color = "#D60066"

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

    adjust_side_spacing(right_side_labels, min_gap=0.20)
    adjust_side_spacing(left_side_labels, min_gap=0.20)

    for side_list, x_side in [(right_side_labels, 1), (left_side_labels, -1)]:
        horizontal_align = "left" if x_side > 0 else "right"
        for item in side_list:
            w = item['w']
            if item['y'] < lowest_label_y:
                lowest_label_y = item['y']

            # Snaps the start of the line perfectly flush onto the expanded 1.0 radius rim
            x_start, y_start = w.r * 0.98 * item['x'], w.r * 0.98 * item['y_orig']

            # Increased kink extension out to 1.15 so lines clear the edge of the circle beautifully
            x_kink, y_kink = w.r * 1.15 * item['x'], w.r * 1.15 * item['y_orig']
            x_vertical = x_kink
            y_vertical = item['y']

            # Extended text shelf line out to 1.35 to give labels a secure landing runway
            x_end = 1.35 * x_side

            ax.plot([x_start, x_kink, x_vertical, x_end],
                    [y_start, y_kink, y_vertical, item['y']],
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

    dynamic_bottom_limit = lowest_label_y - 0.35

    ax.set_xlim(-1.35, 2.1)
    ax.set_ylim(max(-1.65, dynamic_bottom_limit), 1.48)
    ax.axis('off')

    return wedges


def create_monthly_line_chart(fig, months, inc_arr, exp_arr, is_fc_flags, title_text, mode_tag, surplus_tag,
                              theme="dark", monthly_budget=0.0, monthly_budget_inc=0.0, is_cumulative=True):
    """Renders a synchronized 72%/28% Top/Bottom dual-panel chart:
    Top: Gross Income vs. Expenses + Budget benchmark line.
    Bottom: Magnified Net Profit/Loss (Income - Expenses) above/below $0 waterline + Budget Net reference.
    """
    is_light = theme in ("white", "transparent")
    bg_color = "none" if theme == "transparent" else ("#FFFFFF" if theme == "white" else "#111111")
    fg_color = "#1a1a1a" if is_light else "#e0e0e0"
    grid_color = "#dddddd" if is_light else "#262626"
    inc_color = "#0088AA" if is_light else "#00F0FF"
    exp_color = "#D60066" if is_light else "#FF007F"
    pos_color = "#009944" if is_light else "#00FF66"
    bud_color = "#B37700" if is_light else "#FFB800"

    fig.clf()
    fig.patch.set_facecolor(bg_color)
    gs = fig.add_gridspec(2, 1, height_ratios=[2.6, 1.0], hspace=0.14)
    ax_top = fig.add_subplot(gs[0])
    ax_bot = fig.add_subplot(gs[1], sharex=ax_top)
    for ax in (ax_top, ax_bot):
        ax.set_facecolor(bg_color)

    x = np.arange(len(months))
    first_fc_idx = next((i for i, flag in enumerate(is_fc_flags) if flag), len(months))
    net_arr = inc_arr - exp_arr

    # --- TOP PANEL: GROSS INCOME vs. EXPENSES + BUDGET BENCHMARK ---
    bud_arr = None
    if monthly_budget > 0 and len(months) > 0:
        bud_arr = np.array([monthly_budget * (i + 1) for i in range(len(months))]) if is_cumulative else np.full(len(months), monthly_budget)
        ax_top.plot(x, bud_arr, color=bud_color, linestyle='--', linewidth=1.3, alpha=0.55, zorder=1)
        ax_top.text(x[-1], bud_arr[-1], f"  Budget (${monthly_budget:,.0f}/mo)", color=bud_color, alpha=0.80,
                    fontsize=8.5, fontweight='bold', va='center', ha='left', clip_on=False)

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
        if 0 < first_fc_idx < len(months):
            ax_top.axvline(x=first_fc_idx - 0.5, color='#666666', linestyle='--', linewidth=1.1, zorder=1)
            ax_bot.axvline(x=first_fc_idx - 0.5, color='#666666', linestyle='--', linewidth=1.1, zorder=1)
            y_top = max(float(np.max(inc_arr)), float(np.max(exp_arr)), float(np.max(bud_arr)) if bud_arr is not None else 0.0)
            ax_top.text(first_fc_idx - 0.42, y_top, "Forecast →", color='#888888', fontsize=8, fontweight='bold', va='top')

    ax_top.set_title(f"{title_text} ({mode_tag} • {surplus_tag})", color=fg_color, fontsize=13.5, fontweight='bold', pad=12)
    ax_top.tick_params(axis='x', labelbottom=False, colors=fg_color)
    ax_top.tick_params(axis='y', colors=fg_color, labelsize=8.5)
    ax_top.yaxis.set_major_formatter('${x:,.0f}')
    ax_top.grid(True, linestyle='--', linewidth=0.6, color=grid_color)
    leg = ax_top.legend(loc='upper left', frameon=True, facecolor='#1a1a1a' if not is_light else '#f4f4f4', edgecolor='#333333', fontsize=8)
    for txt in leg.get_texts(): txt.set_color(fg_color)
    max_data_y = max(float(np.max(inc_arr)), float(np.max(exp_arr)), float(np.max(bud_arr)) if bud_arr is not None else 0.0, 1.0)
    ax_top.set_ylim(0, math.ceil(max_data_y / 50000.0) * 50000)

    # --- BOTTOM PANEL: MAGNIFIED NET PROFIT / LOSS ($0 WATERLINE) ---
    ax_bot.axhline(0, color='#888888' if not is_light else '#555555', linewidth=1.1, zorder=2)
    bud_net_mo = monthly_budget_inc - monthly_budget
    bud_net_arr = np.array([bud_net_mo * (i + 1) for i in range(len(months))]) if is_cumulative else np.full(len(months), bud_net_mo)
    if abs(bud_net_mo) > 1.0:
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

    ax_bot.set_ylabel("Net P&L", color=fg_color, fontsize=8.5, fontweight='bold')
    ax_bot.set_xticks(x)
    ax_bot.set_xticklabels(months, color=fg_color, fontweight='bold', fontsize=9)
    ax_bot.tick_params(axis='y', colors=fg_color, labelsize=8)
    ax_bot.yaxis.set_major_formatter('${x:,.0f}')
    ax_bot.grid(True, linestyle='--', linewidth=0.5, color=grid_color)
    max_abs_net = max(float(np.max(np.abs(net_arr))), float(np.max(np.abs(bud_net_arr))), 5000.0)
    y_pad = math.ceil((max_abs_net * 1.25) / 5000.0) * 5000
    ax_bot.set_ylim(-y_pad, y_pad)

    for ax in (ax_top, ax_bot):
        for spine in ['top', 'right']: ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']: ax.spines[spine].set_color('#444444')

    v_top = ax_top.axvline(x=0, color='#888888', linestyle=':', linewidth=1.2, visible=False, zorder=5)
    v_bot = ax_bot.axvline(x=0, color='#888888', linestyle=':', linewidth=1.2, visible=False, zorder=5)
    d_top, = ax_top.plot([], [], marker='o', markersize=10, markerfacecolor='none', markeredgewidth=2.2, visible=False, zorder=6)
    d_bot, = ax_bot.plot([], [], marker='o', markersize=9, markerfacecolor='none', markeredgewidth=2.2, visible=False, zorder=6)

    fig.subplots_adjust(left=0.10, right=0.88, top=0.90, bottom=0.08)
    return ax_top, ax_bot, v_top, v_bot, d_top, d_bot
