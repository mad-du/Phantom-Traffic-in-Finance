import os
import numpy as np
import matplotlib.pyplot as plt

# Parameters
road_length = 100
max_speed = 5
p_rule3 = 0.3
nb_steps = 1000

def new_road(road):

    new_road = np.full_like(road,-1)
    road_length = len(road)

    for i in range(road_length):
        if road[i] != -1 : # as road[i] == -1 signifies that the cell is empty
            speed = road[i]

            # 1 : Acceleration of the vehicle
            if speed < max_speed:
                speed += 1

            # 2 : Braking of the vehicle if necessary
            distance = 1
            while distance <= speed and road[(i + distance) % road_length] == -1:
                distance += 1
            distance -= 1

            speed = min(speed, distance)

            # 3 : Randomly brakes the vehicle (origin of phantom traffick in our NaSch model)
            if speed > 0 and np.random.rand() < p_rule3:
                speed = max(speed - 1, 0)

            # 4 : Move the car (the circuit is a loop)
            new_position = (i + speed) % road_length
            new_road[new_position] = speed

    return new_road


def average_velocity(road_history, grace_period):
    velocities = []
    for road in road_history[grace_period:]:
        velocities.append(np.mean(road[road != -1]))
    return np.mean(velocities)

def lagged_correlation(leader_speeds, follower_speeds, lag):
    T = len(leader_speeds)

    leader_slice = leader_speeds[0: T-lag]
    follower_slice = follower_speeds[lag:T]

    if np.std(leader_slice) == 0 or np.std(follower_slice) == 0:
        return np.nan  # Return NaN if either slice has zero standard deviation to avoid division by zero in correlation calculation.
    return np.corrcoef(leader_slice, follower_slice)[0, 1] # Calculates correlation coefficient between the two slices of the speed arrays, thus giving us a value between -1 and 1.

def peak_lagged_correlation(leader_speeds, follower_speeds, max_lag):
    correlations = np.array([lagged_correlation(leader_speeds, follower_speeds, lag) for lag in range(max_lag)])

    if np.isnan(correlations).all():
        return np.nan, np.nan  # Return None if all correlations are NaN, indicating no valid correlation could be computed.
    peak_lag = np.nanargmax(correlations)  
    return peak_lag, correlations[peak_lag]  # Returns the lag at which the correlation is maximum and the corresponding correlation value.

def run_correlation_strength(speeds_array, grace_period, max_lag):
    speeds = speeds_array[grace_period:] # Ignoring the initial grace period like for average velocity computation
    n = speeds.shape[1]
    peaks = []
    lags = []

    for f in range(n):
        leader = speeds[:, (f+1)%n]
        follower = speeds[:, f]
        lag, peak = peak_lagged_correlation(leader, follower, max_lag)
        peaks.append(peak)
        lags.append(lag)

    peaks = np.array(peaks)
    frac_defined = np.mean(~np.isnan(peaks))  # fraction of car pairs with non-zero speed variance on both sides
    mean_peak = np.nanmean(peaks) if frac_defined > 0 else np.nan

    return mean_peak, frac_defined

avg_velocities_nbcars = []
correlation_strengths_nbcars = []
defined_fractions_nbcars = []

# for nb_cars in range(5,10): # Change back to in range(2,50) after testing !!!

for nb_cars in range(2,50):

    avg_velocities = []
    correlation_strengths = []
    defined_fractions = []

    for i in range(50):
        road = np.full(road_length, -1)
        positions = np.random.choice(road_length, nb_cars, replace=False)
        init_speeds = np.random.randint(0, max_speed + 1, nb_cars)
        road[positions] = init_speeds

        vehicle_positions = []
        speeds = []
        for i in range(road_length):
            if road[i] != -1:
                vehicle_positions.append(i)
                speeds.append(road[i])

        road_history = [road.copy()]
        positions_history = [vehicle_positions.copy()]
        speeds_history = [speeds.copy()]

        for step in range(nb_steps):
            road = new_road(road)

            for cars in range(len(vehicle_positions)):
                i = vehicle_positions[cars]
                while road[i] == -1:
                    i = (i + 1) % road_length
                vehicle_positions[cars] = i
                speeds[cars] = road[i]

            positions_history.append(vehicle_positions.copy())
            speeds_history.append(speeds.copy())
            road_history.append(road.copy())

            
        speeds_array = np.array(speeds_history)
        avg_velocity = average_velocity(np.array(road_history), grace_period=10)
        avg_velocities.append(avg_velocity)

        mean_peak, frac_defined = run_correlation_strength(speeds_array, grace_period=10, max_lag=10)
        correlation_strengths.append(mean_peak)
        defined_fractions.append(frac_defined) 

    avg_velocities_nbcars.append(np.mean(avg_velocities).item())
    correlation_strengths_nbcars.append(np.mean(correlation_strengths).item())
    defined_fractions_nbcars.append(np.mean(defined_fractions).item())


densities = np.array([nb_cars / road_length for nb_cars in range(2, 50)])

os.makedirs('data', exist_ok=True)
np.savez('data/phase1_sweep.npz',
         densities=densities,
         avg_velocities=np.array(avg_velocities_nbcars),
         correlation_strengths=np.array(correlation_strengths_nbcars),
         defined_fractions=np.array(defined_fractions_nbcars))


'''
for t in range(len(road_history)):
    for cars in range(len(vehicle_positions)):
        pos = positions_history[t][cars]
        assert speeds_history[t][cars] == road_history[t][pos], \
            f"Mismatch at t={t}, car={cars}: speeds_history says {speeds_history[t][cars]}, " \
            f"but road_history[{t}][{pos}] = {road_history[t][pos]}"

print("All speeds_history entries match road_history lookups — consistent.")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

ax1.plot(densities, avg_velocities_nbcars)
ax1.set_xlabel('Density')
ax1.set_ylabel('Average velocity')
ax1.set_title('Fundamental diagram')
ax1.axhline(y=max_speed, color='gray', linestyle='--', alpha=0.5, label='v_max')
ax1.legend()

ax2.plot(densities, correlation_strengths_nbcars)
ax2.set_xlabel('Density')
ax2.set_ylabel('Average peak correlation strength')
ax2.set_title('Lagged correlation order parameter')

plt.tight_layout()
plt.savefig('fundamental_and_correlation.png', dpi=300)
plt.show()

'''