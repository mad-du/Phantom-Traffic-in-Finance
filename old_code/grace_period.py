import numpy as np
import matplotlib.pyplot as plt

# Parameters
road_length : int = 100
max_speed : int = 5
p_rule3 : float = 0.3
nb_steps : int = 500
nb_cars : int = 25

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
plt.show()