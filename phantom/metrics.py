import numpy as np


def lagged_correlation(leader_speeds, follower_speeds, lag):
    T = len(leader_speeds)

    leader_slice = leader_speeds[0: T-lag]
    follower_slice = follower_speeds[lag:T]

    if np.std(leader_slice) == 0 or np.std(follower_slice) == 0:
        return np.nan  # Zero std would make the correlation undefined (division by zero).
    return np.corrcoef(leader_slice, follower_slice)[0, 1]


def peak_lagged_correlation(leader_speeds, follower_speeds, max_lag):
    correlations = np.array([lagged_correlation(leader_speeds, follower_speeds, lag) for lag in range(max_lag)])

    if np.isnan(correlations).all():
        return np.nan, np.nan  # No valid correlation could be computed.
    peak_lag = np.nanargmax(correlations)
    return peak_lag, correlations[peak_lag]


def run_correlation_strength(speeds_array, grace_period, max_lag):
    speeds = speeds_array[grace_period:]  # Ignore the initial transient, as for average velocity.
    n = speeds.shape[1]
    peaks = []

    for f in range(n):
        leader = speeds[:, (f+1) % n]
        follower = speeds[:, f]
        _, peak = peak_lagged_correlation(leader, follower, max_lag)
        peaks.append(peak)

    peaks = np.array(peaks)
    frac_defined = np.mean(~np.isnan(peaks))  # Fraction of car pairs with non-zero speed variance on both sides.
    mean_peak = np.nanmean(peaks) if frac_defined > 0 else np.nan

    return mean_peak, frac_defined


def critical_density(densities, correlations):
    slopes = np.diff(correlations)/np.diff(densities)
    k = np.nanargmax(slopes)
    return (densities[k] + densities[k+1])/2