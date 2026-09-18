import numpy as np
import matplotlib.pyplot as plt

# Parameters
road_length : int = 100
max_speed : int = 5
p_rule3 : float = 0.3
nb_steps : int = 1000

# No longer necessary, we incorporated this into the main loop
'''
road = np.full(road_length, -1)
positions = np.random.choice(road_length, nb_cars, replace=False)
init_speeds = np.random.randint(0, max_speed + 1, nb_cars)
road[positions] = init_speeds
'''


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

# No longer necessary, we incorporated this into the main loop
'''
road_history = [road.copy()]
for step in range(nb_steps):
    road = new_road(road)
    road_history.append(road.copy())
'''


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

    for i in range(50):
        road = np.full(road_length, -1)
        positions = np.random.choice(road_length, nb_cars, replace=False)
        init_speeds = np.random.randint(0, max_speed + 1, nb_cars)
        road[positions] = init_speeds

        road_history = [road.copy()]
        for step in range(nb_steps):
            road = new_road(road)
            road_history.append(road.copy())

        avg_velocity = average_velocity(np.array(road_history), grace_period=10)
        avg_velocities.append(avg_velocity)

    avg_velocities_nbcars.append(np.mean(avg_velocities).item())

print(avg_velocities_nbcars)

densities = np.array([nb_cars / road_length for nb_cars in range(1, 50)])

fig, ax = plt.subplots()
ax.plot(densities, avg_velocities_nbcars)
ax.set_xlabel('Density')
ax.set_ylabel('Average velocity')

plt.savefig('densities_avgvelocities.png', dpi=300)
plt.show()

# This was to plot the average velocity of the vehicles on the road as a way to determine what the grace period to ignore for actual calculations should be, when we actually exploit the statistical data of each run

'''
def averaged_velocity_trajectory(num_runs=100) -> np.ndarray:
    all_runs = []  # will hold one array per run, not one flat list

    for i in range(num_runs):
        road = np.full(road_length, -1)
        positions = np.random.choice(road_length, nb_cars, replace=False)
        init_speeds = np.random.randint(0, max_speed + 1, nb_cars)
        road[positions] = init_speeds

        road_history = [road.copy()]
        for step in range(nb_steps):
            road = new_road(road)
            road_history.append(road.copy())

        run_velocities = [np.mean(r[r != -1]) for r in road_history]
        all_runs.append(run_velocities)

    all_runs = np.array(all_runs)
    return np.mean(all_runs, axis=0)

velocities = averaged_velocity_trajectory()

print(np.mean(velocities[10:30]))
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
plt.show()

'''

# This was to plot the traffic simulation as a heatmap, where the x-axis is the position on the road, the y-axis is the time step, and the color represents the speed of the vehicles at that position and time.

'''
road_history = np.array(road_history)

print(road_history)


traffic_simulation = plt.imshow(road_history, cmap='viridis', interpolation='nearest')
plt.colorbar()
plt.xlabel('Position on the road')
plt.ylabel('Time step')
plt.title('Traffic Simulation using NaSch Model (nb_cars = 30, p_rule3 = 0.3)')

plt.savefig('traffic_simulation.png', dpi=300)
plt.show()

'''

