"""Checks that the lagged-correlation measure finds what it should, on data where the answer is known."""
import os

import numpy as np
import pytest

from phantom.metrics import MIN_VALID_PAIRS, column_pairs, lagged_correlation, peak_lagged_correlation, run_correlation_strength

DELAY = 2


def planted_cascade(n_windows=2000, n_levels=5, delay=DELAY, noise=0.3, seed=0):
    """Column 0 is random noise (the touch); every deeper level copies the one in front `delay` windows later, plus noise."""
    rng = np.random.default_rng(seed)
    levels = [rng.normal(size=n_windows)]
    for _ in range(1, n_levels):
        levels.append(np.concatenate([np.zeros(delay), levels[-1][:-delay]]) + noise * rng.normal(size=n_windows))
    return np.column_stack(levels)


def strength(signal):
    mean_peak, _ = run_correlation_strength(signal, grace_period=0, max_lag=10, ring=False)
    return mean_peak


def test_planted_cascade_reads_high_and_recovers_the_delay():
    signal = planted_cascade()
    assert strength(signal) > 0.9
    peak_lag, _ = peak_lagged_correlation(signal[:, 0], signal[:, 1], max_lag=10)   # touch leads, next level follows
    assert peak_lag == DELAY


def test_reversed_cascade_reads_low():
    """The same data with the deepest level leading must NOT register as outward propagation: the measure has a direction."""
    assert strength(planted_cascade()[:, ::-1]) < 0.15


def test_pure_noise_sits_at_the_floor():
    """Not zero: the peak over 10 lags of pure noise is biased upward a little (about 0.05)."""
    noise = np.random.default_rng(7).normal(size=(2000, 5))
    assert 0.0 < strength(noise) < 0.12


def test_scattered_missing_windows_do_not_break_the_measure():
    signal = planted_cascade()
    rng = np.random.default_rng(3)
    signal[rng.random(signal.shape) < 0.10] = np.nan
    before = signal.copy()
    assert strength(signal) > 0.9
    assert np.array_equal(signal, before, equal_nan=True)    # the measure must not modify its input


def test_mostly_missing_data_is_undefined_not_a_fluke():
    leader, follower = planted_cascade()[:, 0].copy(), planted_cascade()[:, 1].copy()
    leader[:1980] = np.nan
    assert np.isnan(lagged_correlation(leader, follower, DELAY))


def test_pairs_are_counted_not_values():
    """Each series has 190 usable values (> MIN_VALID_PAIRS) but they almost never coincide, so the correlation is undefined."""
    signal = planted_cascade(n_windows=400)
    leader, follower = signal[:, 0].copy(), signal[:, 1].copy()
    leader[:210] = np.nan
    follower[190:] = np.nan
    assert (~np.isnan(leader)).sum() > MIN_VALID_PAIRS and (~np.isnan(follower)).sum() > MIN_VALID_PAIRS
    assert np.isnan(lagged_correlation(leader, follower, DELAY))


def test_clean_data_matches_the_plain_correlation_formula():
    signal = planted_cascade(n_windows=300)
    leader, follower = signal[:, 0], signal[:, 1]
    for lag in range(10):
        expected = np.corrcoef(leader[:300 - lag], follower[lag:])[0, 1]
        assert lagged_correlation(leader, follower, lag) == pytest.approx(expected)


def test_column_pairs_orientation():
    assert column_pairs(5, ring=False) == [(0, 1), (1, 2), (2, 3), (3, 4)]             # touch leads, no wrap-around
    assert column_pairs(5, ring=True) == [(1, 0), (2, 1), (3, 2), (4, 3), (0, 4)]      # traffic: the car ahead leads, the ring wraps


@pytest.mark.skipif(not os.path.exists('data/phase1_sweep.npz'), reason="saved Phase 1 sweep not present")
def test_traffic_path_still_reproduces_the_saved_phase1_values():
    """Regression guard for the ring (traffic) path. Fails if run_sweep's constants or the seeding scheme change."""
    from scripts.run_sweep import NB_CARS_RANGE, NB_RUNS, SEED, run_one
    saved = np.load('data/phase1_sweep.npz')['correlation_strengths_runs']
    streams = np.random.SeedSequence(SEED).spawn(len(NB_CARS_RANGE) * NB_RUNS)
    for density_index, nb_cars in ((12, 14), (30, 32)):
        _, peak, _ = run_one(nb_cars, np.random.default_rng(streams[density_index * NB_RUNS]))
        assert peak == saved[density_index, 0]
