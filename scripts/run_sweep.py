"""python -m scripts.run_sweep"""
import os

import numpy as np

from phantom.nasch import simulate
from phantom.metrics import average_velocity, run_correlation_strength

ROAD_LENGTH = 100
MAX_SPEED = 5
P_SLOWDOWN = 0.3
NB_STEPS = 1000
GRACE_PERIOD = 15  # transient length justified in the README (grace_period experiment)
MAX_LAG = 10
NB_RUNS = 50
NB_CARS_RANGE = range(2, 50)
SEED = 0

def run_one(nb_cars, rng):
    """Simulate once and return (avg_velocity, correlation_strength, frac_defined)."""
    road_history, _, speeds_history = simulate(nb_cars, ROAD_LENGTH, NB_STEPS, MAX_SPEED, P_SLOWDOWN, rng)

    speeds_array = speeds_history
    avg_velocity = average_velocity(road_history, grace_period=GRACE_PERIOD)
    mean_peak, frac_defined = run_correlation_strength(speeds_array, grace_period=GRACE_PERIOD, max_lag=MAX_LAG)

    return avg_velocity, mean_peak, frac_defined


def main():
    streams = np.random.SeedSequence(SEED).spawn(len(NB_CARS_RANGE) * NB_RUNS)

    avg_velocities = np.empty((len(NB_CARS_RANGE), NB_RUNS))
    correlation_strengths = np.empty((len(NB_CARS_RANGE), NB_RUNS))
    defined_fractions = np.empty((len(NB_CARS_RANGE), NB_RUNS))

    for d, nb_cars in enumerate(NB_CARS_RANGE):
        for r in range(NB_RUNS):
            rng = np.random.default_rng(streams[d * NB_RUNS + r])
            avg_velocities[d, r], correlation_strengths[d, r], defined_fractions[d, r] = run_one(nb_cars, rng)

    os.makedirs('data', exist_ok=True)
    np.savez('data/phase1_sweep.npz',
             densities=np.array([n / ROAD_LENGTH for n in NB_CARS_RANGE]),
             avg_velocities=np.nanmean(avg_velocities, axis=1),
             correlation_strengths=np.nanmean(correlation_strengths, axis=1),
             correlation_strengths_runs=correlation_strengths,
             defined_fractions=np.nanmean(defined_fractions, axis=1),
             # provenance: the parameters that produced this file
             road_length=ROAD_LENGTH, max_speed=MAX_SPEED, p_slowdown=P_SLOWDOWN, nb_steps=NB_STEPS,
             grace_period=GRACE_PERIOD, max_lag=MAX_LAG, nb_runs=NB_RUNS, seed=SEED)


if __name__ == '__main__':
    main()
