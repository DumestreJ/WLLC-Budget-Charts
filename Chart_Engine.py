import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')
NEON_COLORS = ['#FF007F', '#00F0FF', '#FF00FF', '#7000FF', '#FFB800', '#00FF66', '#FF3300']


def create_smart_pie(fig, sizes, labels, total_value, title, title_color, current_font_size=9, y_threshold=0.16):
    # 1. COMPLETELY PURGE THE OLD GRAPH AND ALL LINGERING TEXT ENTIRELY
    fig.clf()

    # Stretch the internal subplot grid box to fill 100% of the canvas height and width space,
    # pulling the left margin right up to the edge and expanding the right side wide for text.
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.02, top=0.82)

    # Create our clean drawing canvas inside the newly stretched figure
    ax = fig.add_subplot(111)
    ax.set_facecolor('#111111')

    if not sizes or sum(sizes) == 0:
        ax.text(0, 0, "No Data Available", color='white', weight="bold", ha="center")
        ax.set_title(title, color=title_color, fontsize=12, weight='bold', pad=10)
        ax.axis('off')
        return []

    # FIXED: Lock the slice radius to 1.0. Because the subplot adjustments stretch the drawing box,
    # a 1.0 radius circle naturally swells outward to fill the full vertical height available.
    wedges, _ = ax.pie(
        sizes, colors=NEON_COLORS[:len(sizes)], startangle=270, counterclock=False,
        radius=1.0,
        wedgeprops=dict(edgecolor='#222222', linewidth=2, antialiased=True, width=None)
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
                    color="white", weight="bold", fontsize=current_font_size,
                    ha=horizontal_align, va="center")

    # Anchoring at x=0.0 centers the main title directly over the pie circle's center axis
    # 2. WIDTH-DRIVEN TITLE FONT SCALING:
    # Reads the actual width of the chart figure in inches (~3.8" at min width up to ~7.5" at max)
    # Scales smoothly from 11.0pt (no left clipping) up to 18.0pt when maximized
    fig_w = fig.get_figwidth()
    dynamic_title_size = min(18.0, max(10.5, 10.5 + ((fig_w - 3.8) * 2.0)))

    ax.text(0.0, 1.38, title,
            color=title_color, fontsize=dynamic_title_size, weight='bold',
            horizontalalignment='center', verticalalignment='center')

    # 3. Keep the Total subtitle pinned right below it on the exact same x=0.0 centerline
    dynamic_sub_size = min(10.5, max(8.0, dynamic_title_size * 0.58))
    ax.text(0.0, 1.22, f"Total: ${total_value:,.0f}",
            color='#aaaaaa', fontname='Arial', fontsize=dynamic_sub_size, weight='bold',
            horizontalalignment='center', verticalalignment='center')

    dynamic_bottom_limit = lowest_label_y - 0.35

    ax.set_xlim(-1.35, 2.1)
    ax.set_ylim(max(-1.65, dynamic_bottom_limit), 1.48)
    ax.axis('off')

    return wedges
