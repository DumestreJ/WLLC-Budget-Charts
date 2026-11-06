import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')
NEON_COLORS = ['#FF007F', '#00F0FF', '#FF00FF', '#7000FF', '#FFB800', '#00FF66', '#FF3300']


# CHANGED: First argument is now 'fig' instead of 'ax'
def create_smart_pie(fig, sizes, labels, total_value, title, title_color, current_font_size=9, y_threshold=0.16):
    # 1. COMPLETELY PURGE THE OLD GRAPH AND ALL LINGERING TEXT ENTIRELY
    fig.clf()

    # 2. Create a clean, centered drawing canvas inside the cleared figure
    ax = fig.add_subplot(111)
    ax.set_facecolor('#111111')

    if not sizes or sum(sizes) == 0:
        ax.text(0, 0, "No Data Available", color='white', weight="bold", ha="center")
        ax.set_title(title, color=title_color, fontsize=12, weight='bold', pad=10)
        ax.axis('off')
        return

    wedges, _ = ax.pie(
        sizes, colors=NEON_COLORS[:len(sizes)], startangle=270, counterclock=False,
        radius=1.05,
        wedgeprops=dict(edgecolor='#222222', linewidth=2, antialiased=True)
    )

    left_side_labels = []
    right_side_labels = []
    lowest_label_y = -1.5

    for i, w in enumerate(wedges):
        percentage = (sizes[i] / total_value) * 100 if total_value > 0 else 0
        ang = (w.theta2 - w.theta1) / 2. + w.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))

        label_text = f"{labels[i]}\n${sizes[i]:,.0f} ({percentage:.1f}%)"

        if percentage >= 15.0:
            ix = w.r * 0.58 * x
            iy = w.r * 0.58 * y
            ax.text(ix, iy, label_text, color="black", weight="bold", fontsize=current_font_size,
                    ha='center', va='center')
        else:
            target_y = w.r * 1.25 * y
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

            x_start, y_start = w.r * 0.98 * item['x'], w.r * 0.98 * item['y_orig']
            x_kink, y_kink = w.r * 1.15 * item['x'], w.r * 1.15 * item['y_orig']
            x_vertical = x_kink
            y_vertical = item['y']
            x_end = 1.30 * x_side

            ax.plot([x_start, x_kink, x_vertical, x_end],
                    [y_start, y_kink, y_vertical, item['y']],
                    color=item['color'], linewidth=1.5, zorder=1)

            ax.text(x_end + (0.04 * x_side), item['y'], item['text'],
                    color="white", weight="bold", fontsize=current_font_size,
                    ha=horizontal_align, va="center")

    ax.set_title(title, color=title_color, fontsize=18, weight='bold', pad=15)

    ax.text(0.53, 1.01, f"Total: ${total_value:,.0f}",
            color='#aaaaaa', fontname='Arial', fontsize=10, weight='bold',
            horizontalalignment='center', verticalalignment='center',
            transform=ax.transAxes)

    dynamic_bottom_limit = lowest_label_y - 0.20

    ax.set_xlim(-1.5, 1.9)
    ax.set_ylim(dynamic_bottom_limit, 1.5)
    ax.axis('off')
