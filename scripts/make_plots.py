"""python -m scripts.make_plots"""
import matplotlib.pyplot as plt
import numpy as np

from phantom.metrics import critical_density, bootstrap_critical_density


def mark_critical_density(ax, rho_c, low, high):
    """Annotate ax with the critical density: a vertical line at rho_c and a shaded band from low to high."""

    ax.axvline(x=rho_c, color='red', linestyle='--', label=f'Critical density: {rho_c:.3f}')
    ax.axvspan(low, high, color='red', alpha=0.2, label=f'95% CI: [{low:.3f}, {high:.3f}]')


def main():
    d = np.load('data/phase1_sweep.npz')
    densities = d['densities']
    max_speed = d['max_speed'].item()

    rho_c = critical_density(densities, d['correlation_strengths'])
    _, (low, high) = bootstrap_critical_density(densities, d['correlation_strengths_runs'])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(densities, d['avg_velocities'])
    ax1.axhline(y=max_speed, color='gray', linestyle='--', alpha=0.5, label='v_max')
    ax1.set_xlabel('Density')
    ax1.set_ylabel('Average velocity')
    ax1.set_title('Fundamental diagram')
    ax1.legend()

    ax2.plot(densities, d['correlation_strengths'])
    ax2.set_xlabel('Density')
    ax2.set_ylabel('Average peak correlation strength')
    ax2.set_title('Lagged correlation order parameter')

    mark_critical_density(ax2, rho_c, low, high)
    ax2.legend()

    plt.tight_layout()
    plt.savefig('graphs/fundamental_and_correlation.png', dpi=300)

    # Standalone fundamental diagram (the README's "Average Velocity vs Density" figure)
    plt.figure(figsize=(7, 5))
    plt.plot(densities, d['avg_velocities'])
    plt.axhline(y=max_speed, color='gray', linestyle='--', alpha=0.5, label='v_max')
    plt.xlabel('Density')
    plt.ylabel('Average velocity')
    plt.title('Average velocity vs density')
    plt.legend()
    plt.tight_layout()
    plt.savefig('graphs/densities_avgvelocities.png', dpi=300)


if __name__ == '__main__':
    main()
