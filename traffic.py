import numpy as np

# Parameters

road_length : int = 100
nb_cars : int = 30
max_speed : int = 5
p_rule3 : float = 0.3
nb_steps : int = 10

road = np.full(road_length, -1)

positions = np.random.choice(road_length, nb_cars, replace=False)
init_speeds = np.random.randint(0, max_speed + 1, nb_cars)

road[positions] = init_speeds

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

road_history = [road.copy()]
for step in range(nb_steps):
    road = new_road(road)
    road_history.append(road.copy())

print(road_history)
