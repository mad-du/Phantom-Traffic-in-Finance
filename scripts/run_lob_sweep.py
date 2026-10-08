"""Order-book load sweep. Run from the project root:  python -m scripts.run_lob_sweep"""
import os

import numpy as np

from phantom.lob_sim import LOBParams, simulate_lob
from phantom.metrics import run_correlation_strength

LOADS = np.round(np.arange(0.05, 0.80 + 1e-9, 0.05), 3)  # rho = mu / lambda, with lambda = 1
GAMMAS = (0.0, 3.0)    # coupling strength: 0 is the control (no coupling)
N_EVENTS = 40_000
BURN_IN = 5_000        # events dropped before measuring, so the book has reached its steady state
WINDOW = 50            # events per window
MAX_LAG = 10           # in windows
NB_RUNS = 20
SEED = 0


def depth_change_signal(depth, best_bid, best_ask, burn_in, window):
    """Turn per-event depth snapshots into the 'speed' signal: change in depth per window of `window` events.
    Returns:  (n_windows, K) array; row i is depth at the end of window i minus depth at its start.
              A window is invalid, and its whole row is NaN, if EITHER side of the book is empty at EITHER
              end of the window. Rows stay in place (never delete them), so lags between windows stay correct.
    """

    depth = depth.astype(float)  # so we can assign NaN to invalid windows

    snapshot_start = depth[burn_in::window]
    snapshot_end = depth[burn_in + window - 1::window]

    empty_snapshots = np.isnan(best_bid[burn_in::window]) | np.isnan(best_ask[burn_in::window]) | \
                      np.isnan(best_bid[burn_in + window - 1::window]) | np.isnan(best_ask[burn_in + window - 1::window])

    snapshot_start[empty_snapshots] = np.nan
    snapshot_end[empty_snapshots] = np.nan

    return snapshot_end - snapshot_start


def run_one(mu, gamma, rng):
    """Simulate one book; return (mean peak correlation, fraction of pairs defined, fraction of windows dropped, mean depth)."""
    params = LOBParams(market_rate=mu, coupling_strength=gamma)
    out = simulate_lob(N_EVENTS, params, rng)

    peaks, defined, dropped = [], [], []
    for depth in (out['bid_depth'], out['ask_depth']):
        signal = depth_change_signal(depth, out['best_bid'], out['best_ask'], BURN_IN, WINDOW)
        peak, frac_defined = run_correlation_strength(signal, grace_period=0, max_lag=MAX_LAG, ring=False)
        peaks.append(peak)
        defined.append(frac_defined)
        dropped.append(np.mean(np.isnan(signal[:, 0])))   # the rule NaNs whole rows, so one column tells the story

    mean_depth = (out['bid_depth'][BURN_IN:] + out['ask_depth'][BURN_IN:]).sum(axis=1).mean()  # volume in the top ticks
    return np.nanmean(peaks), np.mean(defined), np.mean(dropped), mean_depth


def main():
    shape = (len(GAMMAS), len(LOADS), NB_RUNS)
    peak, defined, dropped, depth = (np.full(shape, np.nan) for _ in range(4))

    # One independent RNG stream per (gamma, load, run): reproducible, and no two runs share random numbers.
    streams = np.random.SeedSequence(SEED).spawn(int(np.prod(shape)))

    for g, gamma in enumerate(GAMMAS):
        for l, mu in enumerate(LOADS):
            for r in range(NB_RUNS):
                rng = np.random.default_rng(streams[(g * len(LOADS) + l) * NB_RUNS + r])
                peak[g, l, r], defined[g, l, r], dropped[g, l, r], depth[g, l, r] = run_one(mu, gamma, rng)
        print(f"gamma = {gamma}: done")

    os.makedirs('data', exist_ok=True)
    np.savez('data/lob_sweep.npz',
             loads=LOADS, gammas=np.array(GAMMAS),
             peak_correlation=peak, frac_defined=defined, frac_dropped=dropped, mean_top_depth=depth,
             # provenance: the parameters that produced this file
             n_events=N_EVENTS, burn_in=BURN_IN, window=WINDOW, max_lag=MAX_LAG, nb_runs=NB_RUNS, seed=SEED)


if __name__ == '__main__':
    main()
