"""Event-level check of the coupling, independent of the correlation measure.
Run from the project root:  python -m scripts.check_coupling

Question: after a cancellation at a price tick, how many cancellations follow within HORIZON events at
  - the tick directly BEHIND it (the one the coupling is designed to push),
  - the tick directly AHEAD of it (nearer the touch; the coupling should not push this one),
  - the tick two steps behind it (to see how far the effect reaches)?
Comparing gamma = 0 with gamma > 0 isolates what the coupling adds. This counts events, it never uses the
correlation measure, so it separates 'the coupling is too weak' from 'the measurement misses it'.
"""
import bisect

import numpy as np

import phantom.lob_sim as ls
from phantom.lob import OrderBook
from phantom.lob_sim import LOBParams, simulate_lob

LOADS = (0.1, 0.4, 0.7)
GAMMAS = (0.0, 3.0)
N_EVENTS = 40_000
NB_RUNS = 5
REFILL_SUPPRESSION = 0.0   # sigma: 0 = the original coupling only
HORIZON = 50   # events; the same length as the stress memory and the measurement window
SEED = 0


def log_cancellations(params, rng):
    """Run one book and return every cancellation as (event index, side, price)."""
    log, clock = [], [0]
    real_cancel, real_depth = OrderBook.cancel_order, ls.depth_profile

    def cancel(self, order_id):
        order = self.orders.get(order_id)
        done = real_cancel(self, order_id)
        if done:
            log.append((clock[0], order.side, order.price))
        return done

    def depth(book, side, n):          # simulate_lob calls this once per side per event: use it as the event clock
        if side == 'buy':
            clock[0] += 1
        return real_depth(book, side, n)

    OrderBook.cancel_order, ls.depth_profile = cancel, depth
    try:
        simulate_lob(N_EVENTS, params, rng)
    finally:
        OrderBook.cancel_order, ls.depth_profile = real_cancel, real_depth
    return log


def followups_per_cancellation(log):
    """Mean number of cancellations within HORIZON events after a cancellation, at the tick behind / ahead / two behind."""
    times = {}
    for t, side, price in log:
        times.setdefault((side, price), []).append(t)   # already in time order

    counts = {'behind': 0, 'ahead': 0, 'two_behind': 0}
    for t, side, price in log:
        step = -1 if side == 'buy' else 1                # 'behind' = farther from the touch on the same side
        for name, tick in (('behind', price + step), ('ahead', price - step), ('two_behind', price + 2 * step)):
            ts = times.get((side, tick))
            if ts:
                counts[name] += bisect.bisect_right(ts, t + HORIZON) - bisect.bisect_right(ts, t)
    return {name: c / len(log) for name, c in counts.items()}, len(log)


def main():
    streams = np.random.SeedSequence(SEED).spawn(len(GAMMAS) * len(LOADS) * NB_RUNS)
    print(f"cancellations within {HORIZON} events after a cancellation, per triggering cancellation "
          f"(mean over {NB_RUNS} runs, +- standard error)\n")
    print(f"{'load':>5} {'gamma':>6} {'triggers/run':>13} {'behind':>16} {'ahead':>16} {'two behind':>16}")

    for l, mu in enumerate(LOADS):
        for g, gamma in enumerate(GAMMAS):
            rows, n_trig = [], []
            for r in range(NB_RUNS):
                rng = np.random.default_rng(streams[(g * len(LOADS) + l) * NB_RUNS + r])
                ratios, n = followups_per_cancellation(log_cancellations(LOBParams(market_rate=mu, coupling_strength=gamma, refill_suppression=REFILL_SUPPRESSION), rng))
                rows.append([ratios['behind'], ratios['ahead'], ratios['two_behind']])
                n_trig.append(n)
            rows = np.array(rows)
            m, se = rows.mean(axis=0), rows.std(axis=0, ddof=1) / np.sqrt(NB_RUNS)
            print(f"{mu:5.2f} {gamma:6.1f} {np.mean(n_trig):13.0f} "
                  + " ".join(f"{m[k]:8.3f} +-{se[k]:.3f}" for k in range(3)))
        print()


if __name__ == '__main__':
    main()
