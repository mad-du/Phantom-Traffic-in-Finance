# Phantom Traffic in Financial Markets

A study of how phantom traffic jams emerge spontaneously from pure randomness in a cellular automaton model of traffic, and an exploration of whether the same critical-threshold applies to financial markets.

## Motivation

One day, before entering a market to buy groceries, I noticed that a small car had randomly slowed down to a stop in the middle of the road, causing the cars behind it to slow down as well. I didn't think much of it until, when I left the market, I was met with a full blown traffic on all four roads of the intersection. I couldn't have possibly been sure that it was caused by this small Renault, but one can always theorize.

When looking at financial markets, we often see parallels with cars on a road. There are gaps between cars and gaps between 'bids' and 'asks'. Too many cars on the road can lead to traffic, just like how too many orders might lead to long waiting times for orders to be fulfilled. A large highway can better accommodate for an influx of vehicles, much like how a 'deep' order book can handle massive trades without moving much.

As such, it is perhaps quite logical to wonder what happens if the financial market's equivalent of a random sudden stop were to occur. What happens when a large market order suddenly disrupts the market and perhaps more importantly, given hypothetical circumstances, how large of a disruption can a market absorb?

## Phase 1 : Traffic simulation (Nagel-Schreckenberg model)

#### The Model

A 1D cellular automaton on a ring : vehicles occupy cells on a looping track, each with a randomized initial integer velocity (between 0 and 5). Following Nagel-Schreckenberg's model, at every timestep, all vehicles update via four rules : acceleration, braking (relative to the gap ahead), random slowdown (with probability p), and movement.

In order to study the limits of such a model, notably at what point do cars cause too much propagating traffic, we need to isolate density $\rho = N/L$ as our clean control parameter, hence why we used a ring, not an open road. This also mirrors Sugiyama's famous 2008 experiment which demonstrated that traffic jams can form with no obstacle and no new additions of vehicles.

#### Verifying the base simulation

Before trusting proceeding statistical measurements, the simulation was first validated with two scenarios. First, if $p = 0$, the simulation would be entirely deterministic, vehicles would move at fixed speeds after accelerating to the maximum velocity. 

![Nagel-Schreckenberg model, p=0](https://github.com/mad-du/Phantom-Traffic-in-Finance/blob/main/graphs/nasch_graph_p0.png)

Setting $p = 0.3$, we obtain a graph which show the propagating stop-and-go effect that you can expect from the Nagel-Schreckenberg model.

![Nagel-Schreckenberg model, p=0.3](https://github.com/mad-du/Phantom-Traffic-in-Finance/blob/main/graphs/nasch_graph_p03.png)

#### Choosing the burn-in grace period

Considering the random nature of each vehicle's assigned velocity, it is perhaps wise to do our statistical measurements after a given grace period for it to reach its steady-state behavior. To do this, we can model the average of the average velocity at the vehicles on the road at each timestep for a large number of simulations, thus giving us a more accurate idea of when the transient is resolved, as one single simulation, affected by randomness, can not possibly be representative.

![Grace Period Determination](https://github.com/mad-du/Phantom-Traffic-in-Finance/blob/main/graphs/grace_period.png)

We observe that the transient resolves within approximately the first 15 steps. We can confirm this by calculating the average velocities between 15-30, 30-100 and 200-400 to determine that they are very close.

#### Average Velocity vs Density

Sweeping density $p = N/L$ (by varying vehicle count $N$ for a fixed track length $L$) and measuring post grace-period average velocity, averaged across 50 independent runs per density for more reliable data, we have the following graph of the average velocity as a function of density.

![Average velocity = f(density)](https://github.com/mad-du/Phantom-Traffic-in-Finance/blob/main/graphs/densities_avgvelocities.png)

#### Limitation

Average velocity dropping is consistent with phantom jam formation but it does nto allow us to directly graph the propagating stop-and-go waves that we are looking to observe both on the roads, and in the financial markets. Notice that, by looking at the graph of velocity over the time steps, we can indeed deduce that this stop-and-go effect happens. Even after the transient state, the average velocity would appear to fluctuate a lot, suggesting that vehicles slow down, causing traffic, before speeding up and repeating this cycle.

That said, in order to properly model this propagating stop-and-go effect and determine the threshold for which the density of the road dramatically increases the effect, we would need a statistical measurement that would capture a vehicle's behavior in comparison to the one in front of it, a statistical measurement that tells us how 2 objects change relative to one another, like the Covariance...