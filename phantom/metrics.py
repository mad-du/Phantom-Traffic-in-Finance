import numpy as np


def average_velocity(road_history, grace_period):
    """
    Compute the average velocity of the road history.
    Returns: the average velocity of all cars across all time steps after the grace period."""
    velocities = []
    for road in road_history[grace_period:]:
        velocities.append(np.mean(road[road != -1]))
    return np.mean(velocities)


MIN_VALID_PAIRS = 30  # fewer valid (t, t+lag) pairs than this and the correlation is reported as undefined


def lagged_correlation(leader_speeds, follower_speeds, lag):
    """
    Compute the lagged correlation between leader and follower speeds.
    Returns: the correlation coefficient, or np.nan if undefined (zero std)."""
    T = len(leader_speeds)

    leader_slice = leader_speeds[0: T-lag]
    follower_slice = follower_speeds[lag:T]

    leader_slice_mask = ~np.isnan(leader_slice)
    follower_slice_mask = ~np.isnan(follower_slice)

    valid = leader_slice_mask & follower_slice_mask

    if valid.sum() < MIN_VALID_PAIRS:
        return np.nan

    if np.std(leader_slice[valid]) == 0 or np.std(follower_slice[valid]) == 0:
        return np.nan  # Zero std would make the correlation undefined (division by zero).
    return np.corrcoef(leader_slice[valid], follower_slice[valid])[0, 1]


def peak_lagged_correlation(leader_speeds, follower_speeds, max_lag):
    """
    Compute the peak lagged correlation between leader and follower speeds.
    Returns: (peak_lag, peak_correlation) where peak_lag is the lag"""
    correlations = np.array([lagged_correlation(leader_speeds, follower_speeds, lag) for lag in range(max_lag)])

    if np.isnan(correlations).all():
        return np.nan, np.nan  # No valid correlation could be computed.
    peak_lag = np.nanargmax(correlations)
    return peak_lag, correlations[peak_lag]


def column_pairs(n, ring):
    """(leader_column, follower_column) index pairs for a signal matrix with n columns.

    ring=True : cars on a ring. Car f follows the car in column f+1, and the last column wraps round to column 0.
    ring=False: an open line of columns ordered from the front outward (for the order book, column 0 is the touch
                and column k+1 lies one price tick behind column k). No wrap-around.
    """
    if ring:
        return [((f + 1) % n, f) for f in range(n)]
    
    return [(f, f+1) for f in range(n - 1)]


def run_correlation_strength(speeds_array, grace_period, max_lag, ring=True):
    """
    Compute the correlation strength of the speeds array.
    ring: whether the columns form a ring (traffic) or an open line from the front outward (order book).
    Returns : (mean_peak, frac_defined) where mean_peak is the mean of the peak correlations across all car pairs, and frac_defined is the fraction of car pairs with non-zero speed variance on both sides."""
    speeds = speeds_array[grace_period:]  # Ignore the initial transient, as for average velocity.
    n = speeds.shape[1]
    peaks = []

    for leader_col, follower_col in column_pairs(n, ring):
        leader = speeds[:, leader_col]
        follower = speeds[:, follower_col]
        _, peak = peak_lagged_correlation(leader, follower, max_lag)
        peaks.append(peak)

    peaks = np.array(peaks)
    frac_defined = np.mean(~np.isnan(peaks))  # Fraction of car pairs with non-zero speed variance on both sides.
    mean_peak = np.nanmean(peaks) if frac_defined > 0 else np.nan

    return mean_peak, frac_defined


def critical_density(densities, correlations):
    """
    Compute the critical density from the correlation strength curve.
    Returns: the density at which the slope of the correlation strength curve is maximal.
    """
    slopes = np.diff(correlations)/np.diff(densities)
    k = np.nanargmax(slopes)
    return (densities[k] + densities[k+1])/2


def bootstrap_critical_density(densities, runs, n_boot=500, seed=0):
    """
    Bootstrap the critical density from the correlation strength curve.
    Returns: (rho_c_samples, (low, high)) where low and high are the 95% confidence interval bounds.
    """

    rng = np.random.default_rng(seed)

    rho_c_samples = []

    for _ in range(n_boot):

        idx = rng.integers(0, runs.shape[1], size=runs.shape[1])

        resampled_runs = runs[:, idx]
        rho_c_samples.append(critical_density(densities, np.nanmean(resampled_runs, axis=1)))

    low, high = np.percentile(rho_c_samples, [2.5, 97.5])
    return np.array(rho_c_samples), (low, high)