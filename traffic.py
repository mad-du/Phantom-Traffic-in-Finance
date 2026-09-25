import numpy as np
import matplotlib.pyplot as plt

# Parameters
road_length : int = 100
max_speed : int = 5
p_rule3 : float = 0.3
nb_steps : int = 5 #Change back to 1000 after testing

def new_road(road : np.ndarray) -> np.ndarray:
    '''
    This function takes the state of the current road and for each car on the road, goes through the 4 steps of the NaSch model before returning a new road with the updated positions of the vehicles.
    '''

    new_road : np.ndarray = np.full_like(road,-1)
    road_length : int = len(road)

    for i in range(road_length):
        if road[i] != -1 : # as road[i] == -1 signifies that the cell is empty
            speed : int = road[i]

            # 1 : Acceleration of the vehicle
            if speed < max_speed:
                speed += 1

            # 2 : Braking of the vehicle if necessary
            distance : int = 1
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


def average_velocity(road_history : np.ndarray, grace_period : int) -> float:
    '''
    This function takes the history of the road and a grace period as input and returns the average velocity of the vehicles on the road after the grace period.
    '''
    velocities = []
    for road in road_history[grace_period:]:
        velocities.append(np.mean(road[road != -1]))
    return np.mean(velocities)

avg_velocities_nbcars : list = []

for nb_cars in range(1,50):

    avg_velocities : list = []

    for i in range(5): #Change back to 50 after testing
        road = np.full(road_length, -1)
        positions = np.random.choice(road_length, nb_cars, replace=False)
        init_speeds = np.random.randint(0, max_speed + 1, nb_cars)
        road[positions] = init_speeds

        vehicle_positions : list = []
        speeds : list = []
        for i in range(road_length):
            if road[i] != -1:
                vehicle_positions.append(i)
                speeds.append(road[i])

        road_history : list = [road.copy()]
        positions_history : list = [vehicle_positions.copy()]
        speeds_history : list = [speeds.copy()]

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

        avg_velocity = average_velocity(np.array(road_history), grace_period=10)
        avg_velocities.append(avg_velocity)

    avg_velocities_nbcars.append(np.mean(avg_velocities).item())

densities = np.array([nb_cars / road_length for nb_cars in range(1, 50)])

speeds_array = np.array(speeds_history)

def lagged_correlation(leader_speeds : np.ndarray, follower_speeds : np.ndarray, lag: int):
    '''
    This function takes the speeds of the leading and following vehicles as input, along with a lag value, and returns the lagged correlation between the two speed arrays.
    '''

    T = len(leader_speeds)

    leader_slice = leader_speeds[0: T-lag]
    follower_slice = follower_speeds[lag:T]

    return np.corrcoef(leader_slice, follower_slice)[0, 1] # Calculates correlation coefficient between the two slices of the speed arrays, thus giving us a value between -1 and 1.

def peak_lagged_correlation(leader_speeds, follower_speeds, max_lag):
    correlations = []
    for lag in range(0, max_lag):
        correlations.append(lagged_correlation(leader_speeds, follower_speeds, lag))
    correlations = np.array(correlations)
    peak_lag = np.argmax(correlations)  
    peak_value = correlations[peak_lag]
    return peak_lag, peak_value

'''
for t in range(len(road_history)):
    for cars in range(len(vehicle_positions)):
        pos = positions_history[t][cars]
        assert speeds_history[t][cars] == road_history[t][pos], \
            f"Mismatch at t={t}, car={cars}: speeds_history says {speeds_history[t][cars]}, " \
            f"but road_history[{t}][{pos}] = {road_history[t][pos]}"

print("All speeds_history entries match road_history lookups — consistent.")
'''

print(speeds_array[:, 2])
print(speeds_array[:, 1])