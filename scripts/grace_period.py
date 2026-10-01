"""Determine the burn-in grace period. Run from the project root:  python -m scripts.grace_period"""
import matplotlib.pyplot as plt
import numpy as np

from phantom.nasch import simulate

ROAD_LENGTH = 100
MAX_SPEED = 5
P_SLOWDOWN = 0.3
NB_STEPS = 500
NB_CARS = 25
NB_RUNS = 100
SEED = 0


def averaged_velocity_trajectory():
    """Mean velocity at each time step, averaged over NB_RUNS independent runs."""
    streams = np.random.SeedSequence(SEED).spawn(NB_RUNS)
    all_runs = []

    for stream in streams:
        road_history, _, _ = simulate(NB_CARS, ROAD_LENGTH, NB_STEPS, MAX_SPEED, P_SLOWDOWN, np.random.default_rng(stream))
        all_runs.append([np.mean(road[road != -1]) for road in road_history])

    return np.mean(np.array(all_runs), axis=0)


def main():
    velocities = averaged_velocity_trajectory()

    print(np.mean(velocities[15:30]))
    print(np.mean(velocities[30:100]))
    print(np.mean(velocities[200:400]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))

    ax1.plot(velocities[:100])
    ax1.set_xlabel('Timestep')
    ax1.set_ylabel('Average velocity')
    ax1.set_title('Zoomed in (first 100 steps)')

    ax2.plot(velocities)
    ax2.set_xlabel('Timestep')
    ax2.set_ylabel('Average velocity')
    ax2.set_title('Full run')

    plt.tight_layout()
    plt.savefig('graphs/grace_period.png', dpi=300)


if __name__ == '__main__':
    main()
