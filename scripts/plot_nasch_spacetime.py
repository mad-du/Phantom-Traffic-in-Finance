"""Space-time diagram of one NaSch run. Run from the project root:  python -m scripts.plot_nasch_spacetime --p 0.3"""
import argparse

import matplotlib.pyplot as plt
import numpy as np

from phantom.nasch import simulate

ROAD_LENGTH = 100
MAX_SPEED = 5
NB_STEPS = 100
NB_CARS = 30
SEED = 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--p', type=float, default=0.0, help='random slowdown probability')
    p = parser.parse_args().p

    road_history, _, _ = simulate(NB_CARS, ROAD_LENGTH, NB_STEPS, MAX_SPEED, p, np.random.default_rng(SEED))

    plt.imshow(road_history, cmap='viridis', interpolation='nearest')
    plt.colorbar()
    plt.xlabel('Position on the road')
    plt.ylabel('Time step')
    plt.title(f'Traffic Simulation using NaSch Model (nb_cars = {NB_CARS}, p = {p})')

    # p=0 -> nasch_graph_p0.png, p=0.3 -> nasch_graph_p03.png (matches the names the README links to)
    plt.savefig(f"graphs/nasch_graph_p{p:g}".replace('.', '') + '.png', dpi=300)


if __name__ == '__main__':
    main()
