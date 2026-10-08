"""Figure for the order-book load sweeps. Run from the project root:  python -m scripts.make_lob_plots

Mean peak lagged correlation against load for gamma = 0 (control), 3 and 10, with the control limit and the level
the README success rule would need (low-load plateau + 0.40).
"""
import matplotlib.pyplot as plt
import numpy as np

SURFACE, INK, INK_2, MUTED, GRID, AXIS = '#fcfcfb', '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'   # categorical slots 1-3 (validated all-pairs)
REQUIRED_RISE = 0.40       # from the README success rule
LOW_LOAD = 0.20            # "low plateau" = mean over loads <= 0.20, as in the results log
CONTROL_LIMIT = 0.20       # from the README success rule


def load_series():
    """Returns [(label, color, marker, loads, runs_of_peak)] for gamma = 0, 3, 10."""
    a, b = np.load('data/lob_sweep.npz'), np.load('data/lob_sweep_gamma10.npz')
    assert np.array_equal(a['loads'], b['loads']), "the two sweeps must share the same load grid"
    return [
        ('γ = 0 (control)', BLUE, 'o', a['loads'], a['peak_correlation'][0]),
        ('γ = 3', ORANGE, 's', a['loads'], a['peak_correlation'][1]),
        ('γ = 10', AQUA, '^', b['loads'], b['peak_correlation'][0]),
    ]


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(AXIS)
    ax.grid(axis='y', color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.xaxis.label.set_color(INK_2)
    ax.yaxis.label.set_color(INK_2)


def draw_series(ax, loads, runs, color, marker, label, label_y):
    """Mean line with markers, a +-1 standard-deviation band over runs, and a direct label past the last point."""
    mean, sd = np.nanmean(runs, axis=1), np.nanstd(runs, axis=1, ddof=1)
    ax.fill_between(loads, mean - sd, mean + sd, color=color, alpha=0.15, linewidth=0)
    ax.plot(loads, mean, color=color, marker=marker, markersize=5, linewidth=2,
            markeredgecolor=SURFACE, markeredgewidth=1.0, label=label)
    ax.text(loads[-1] + 0.02, label_y, label, color=INK_2, fontsize=9, va='center')
    return mean


def main():
    fig, ax = plt.subplots(figsize=(8.5, 4.8), facecolor=SURFACE)

    targets = []   # the correlation each coupled curve would need to reach under the README rule
    for (label, color, marker, loads, peak), label_y in zip(load_series(), (0.095, 0.135, 0.17)):
        mean = draw_series(ax, loads, peak, color, marker, label, label_y)
        targets.append(mean[loads <= LOW_LOAD].mean() + REQUIRED_RISE)

    ax.axhspan(min(targets[1:]), max(targets[1:]), color=INK_2, alpha=0.12, linewidth=0)
    ax.text(0.05, max(targets[1:]) + 0.012, 'level a transition would need (low-load plateau + 0.40)', color=INK_2,
            fontsize=9, va='bottom', ha='left')
    ax.axhline(CONTROL_LIMIT, color=MUTED, linestyle='--', linewidth=1)
    ax.text(0.05, CONTROL_LIMIT + 0.015, 'control limit (0.20)', color=INK_2, fontsize=9, va='bottom')

    ax.set_xlim(0.03, 0.93)
    ax.set_ylim(0, 0.65)
    ax.set_xticks(np.arange(0.1, 0.81, 0.1))   # the data stops at 0.8; the room to the right is for the direct labels
    ax.set_xlabel('Load  ρ = μ / λ')
    ax.set_ylabel('Mean peak lagged correlation')
    ax.set_title('No threshold appears at γ = 3 or γ = 10', color=INK, fontsize=11, loc='left')
    style_axes(ax)
    ax.legend(loc='center left', bbox_to_anchor=(0.01, 0.50), frameon=False, labelcolor=INK_2, fontsize=9)

    fig.text(0.01, 0.01, 'Lines: mean over 20 runs; bands: ±1 standard deviation across runs. '
                         'Windows with an empty side of the book are excluded.', color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig('graphs/lob_sweep_results.png', dpi=300, facecolor=SURFACE)


if __name__ == '__main__':
    main()
