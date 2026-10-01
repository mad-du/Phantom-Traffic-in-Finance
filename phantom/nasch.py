import numpy as np


def new_road(road, max_speed, p_slowdown, rng):
    """
    One parallel NaSch update. road[i] == -1 means cell i is empty, otherwise it holds that car's speed.
    """
    new_road = np.full_like(road, -1)
    road_length = len(road)

    for i in range(road_length):
        if road[i] != -1:
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

            # 3 : Random slowdown (origin of phantom traffic in the NaSch model)
            if speed > 0 and rng.random() < p_slowdown:
                speed = max(speed - 1, 0)

            # 4 : Move the car (the circuit is a loop)
            new_road[(i + speed) % road_length] = speed

    return new_road


def advance_cars(road, vehicle_positions):
    """
    Follow each car across one update.
    Returns: (new_positions, speeds), both lists in the same car order.
    """

    speeds = []
    new_positions = []

    for car in range(len(vehicle_positions)):
        pos = vehicle_positions[car]
        i = pos
        while road[i] == -1:
            i = (i + 1) % len(road)
        new_positions.append(i)
        speeds.append(road[i])

    return new_positions, speeds


def simulate(nb_cars, road_length, nb_steps, max_speed, p_slowdown, rng):
    """
    Run one simulation and return (road_history, positions_history, speeds_history).
    """
    road = np.full(road_length, -1)
    positions = rng.choice(road_length, nb_cars, replace=False)
    road[positions] = rng.integers(0, max_speed + 1, nb_cars)

    vehicle_positions = [i for i in range(road_length) if road[i] != -1]
    speeds = [road[i] for i in vehicle_positions]

    road_history = [road.copy()]
    positions_history = [vehicle_positions.copy()]
    speeds_history = [speeds.copy()]

    for _ in range(nb_steps):
        road = new_road(road, max_speed, p_slowdown, rng)
        vehicle_positions, speeds = advance_cars(road, vehicle_positions)

        road_history.append(road.copy())
        positions_history.append(vehicle_positions.copy())
        speeds_history.append(speeds.copy())

    return np.array(road_history), np.array(positions_history), np.array(speeds_history)
