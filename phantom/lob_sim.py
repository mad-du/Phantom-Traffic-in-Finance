import math
from dataclasses import dataclass

import numpy as np

from phantom.lob import OrderBook


@dataclass
class LOBParams:
    limit_rate: float = 1.0     # lambda: arrival rate of new (passive) limit orders
    market_rate: float = 0.3    # mu: arrival rate of market orders
    cancel_rate: float = 0.02   # theta: cancellation rate PER RESTING ORDER
    mean_offset: float = 2.0    # mean distance (ticks) behind the touch at which new limit orders are placed
    max_size: int = 5           # order sizes are uniform on 1..max_size
    mid0: int = 100             # starting mid price (ticks)
    init_levels: int = 5        # price levels seeded on each side before the simulation starts
    n_snapshot_levels: int = 5  # depth is recorded for this many levels counted from the touch
    coupling_strength: float = 0.0  # gamma: how strongly recent cancellations one tick ahead raise an order's cancel hazard (0 = no coupling)
    stress_memory: float = 50.0     # T: time constant (in events) over which a cancellation's effect fades; tied to the window W = 50


def sample_event_type(book, params, rng):
    """Pick the next event: 'limit', 'market' or 'cancel'.

    The probability of each type is proportional to its total rate:
        limit  -> params.limit_rate
        market -> params.market_rate
        cancel -> params.cancel_rate * (number of resting orders in the book)
    Returns one of the three strings.
    """
    total_rate = params.limit_rate + params.market_rate + params.cancel_rate * len(book.orders)
    if total_rate > 0:
        p_limit = params.limit_rate / total_rate
        p_market = params.market_rate / total_rate
        p_cancel = params.cancel_rate * len(book.orders) / total_rate
        return rng.choice(['limit', 'market', 'cancel'], p=[p_limit, p_market, p_cancel])


def placement_price(book, side, offset, last_mid):
    """Price for a new passive limit order, `offset` ticks behind the opposite-side touch (never crossing)."""
    if side == 'buy':
        touch = book.best_ask - 1 if book.best_ask is not None else round(last_mid) - 1
        return max(touch - offset, 1)
    touch = book.best_bid + 1 if book.best_bid is not None else round(last_mid) + 1
    return touch + offset


def depth_profile(book, side, n_levels):
    """Resting size at the first n_levels price ticks from the touch (0 where a tick is empty or the side is empty)."""
    if side == 'buy':
        touch, step = book.best_bid, -1
    else:
        touch, step = book.best_ask, 1
    if touch is None:
        return [0] * n_levels
    return [book.depth_at(side, touch + step * k) for k in range(n_levels)]


class StressTracker:
    """Decaying tally of recently CANCELLED volume per price tick, keyed by the absolute (side, price).

    Each cancellation adds the cancelled volume to its tick's tally, which fades exponentially with time
    constant `memory` events (decay is applied lazily). Fills from market orders are never recorded here.
    Keying by absolute price means the tally is unaffected by the touch moving.
    """

    PRUNE_BELOW = 1e-2  # tallies that have faded below this volume are dropped

    def __init__(self, memory):
        self.memory = memory
        self._tally = {}  # (side, price) -> (volume at time of last update, time of last update)

    def _decayed(self, key, t):
        entry = self._tally.get(key)
        if entry is None:
            return 0.0
        volume, t0 = entry
        return volume * math.exp(-(t - t0) / self.memory)

    def add_cancel(self, side, price, volume, t):
        key = (side, price)
        self._tally[key] = (self._decayed(key, t) + volume, t)

    def stress(self, book, side, price, t):
        """Recently cancelled volume as a fraction of (that volume + the depth still resting): in [0, 1), 0 if none."""
        d = self._decayed((side, price), t)
        if d <= 0:
            return 0.0
        return d / (d + book.depth_at(side, price))

    def stressed_ticks(self, t):
        """Yield ((side, price), decayed volume) for every tick still above PRUNE_BELOW, dropping the faded ones."""
        for key in list(self._tally):
            d = self._decayed(key, t)
            if d < self.PRUNE_BELOW:
                del self._tally[key]
            else:
                yield key, d


def hazard_multiplier(book, tracker, order, gamma, t):
    """Factor on an order's baseline cancel rate: 1 + gamma * (stress of the tick one step AHEAD of it).

    "Ahead" is one tick closer to the touch on the same side (price + 1 for bids, price - 1 for asks).
    """
    ahead = order.price + 1 if order.side == 'buy' else order.price - 1
    return 1.0 + gamma * tracker.stress(book, order.side, ahead, t)


def cancel_weights(book, params, tracker, t):
    """Total cancel weight of the book and how it splits over stressed ticks.

    Every resting order has weight 1 + extra, where extra = gamma * stress(tick ahead) is shared by all the
    orders on one tick. Returns (total_weight, groups) with groups = [(extra, deque_of_orders), ...] covering
    only the ticks that have extra > 0 and hold orders. total_weight = len(book.orders) + sum(extra * len(orders)).
    """
    groups, total = [], float(len(book.orders))
    for (side, price), _ in tracker.stressed_ticks(t):
        stress = tracker.stress(book, side, price, t)
        behind = price - 1 if side == 'buy' else price + 1  # one tick farther from the touch, same side
        level = (book.bids if side == 'buy' else book.asks).get(behind)
        if level and stress > 0:
            extra = params.coupling_strength * stress
            groups.append((extra, level))
            total += extra * len(level)
    return total, groups


def draw_event_type(params, cancel_intensity, rng):
    """Draw 'limit' / 'market' / 'cancel' with probability proportional to limit_rate, market_rate, cancel_intensity."""
    total = params.limit_rate + params.market_rate + cancel_intensity
    if total <= 0:
        raise ValueError("all event rates are zero")
    return rng.choice(['limit', 'market', 'cancel'],
                      p=[params.limit_rate / total, params.market_rate / total, cancel_intensity / total])


def pick_cancel_target(book, total_weight, groups, rng):
    """Order id to cancel, drawn with probability proportional to its weight (1 + extra)."""
    n = len(book.orders)
    r = rng.random() * total_weight
    if r < n:  # the baseline weight 1 of every order: uniform choice
        return int(rng.choice(list(book.orders)))
    r -= n
    for extra, level in groups:  # the extra weight, shared by the orders of each stressed tick's neighbour
        w = extra * len(level)
        if r < w:
            return level[int(rng.integers(len(level)))].order_id
        r -= w
    return int(rng.choice(list(book.orders)))  # floating-point leftover


def simulate_lob(n_events, params, rng):
    """Run the book for n_events events (one event = one time step) and record its state after each one.

    Time here is event count, not wall-clock. A continuous-time version would add an exponential waiting
    time with mean 1 / (total rate) between events; that is a possible refinement, not needed for now.

    With params.coupling_strength > 0, recent cancellations at a tick raise the cancel hazard of the orders
    one tick behind it (see StressTracker / hazard_multiplier). With 0 the original uncoupled path runs.

    Returns a dict of arrays with one row per event:
        event_type (n,)          0 = limit, 1 = market, 2 = cancel
        best_bid, best_ask (n,)  NaN while that side is empty
        bid_depth, ask_depth (n, n_snapshot_levels)
    """
    book = OrderBook()
    for k in range(1, params.init_levels + 1):
        book.add_limit_order('buy', params.mid0 - k, int(rng.integers(1, params.max_size + 1)))
        book.add_limit_order('sell', params.mid0 + k, int(rng.integers(1, params.max_size + 1)))

    K = params.n_snapshot_levels
    event_type = np.empty(n_events, dtype=int)
    best_bid, best_ask = np.full(n_events, np.nan), np.full(n_events, np.nan)
    bid_depth, ask_depth = np.zeros((n_events, K), dtype=int), np.zeros((n_events, K), dtype=int)
    last_mid = float(params.mid0)
    coupled = params.coupling_strength > 0
    tracker = StressTracker(params.stress_memory) if coupled else None

    for t in range(n_events):
        if coupled:
            total_weight, groups = cancel_weights(book, params, tracker, t)
            kind = draw_event_type(params, params.cancel_rate * total_weight, rng)
        else:
            kind = sample_event_type(book, params, rng)
        size = int(rng.integers(1, params.max_size + 1))
        side = 'buy' if rng.random() < 0.5 else 'sell'

        if kind == 'limit':
            offset = int(rng.geometric(1 / (1 + params.mean_offset))) - 1  # >= 0, mean = mean_offset
            book.add_limit_order(side, placement_price(book, side, offset, last_mid), size)
        elif kind == 'market':
            book.match_market_order(side, size)
        elif book.orders:  # cancel a resting order
            if coupled:  # weighted by hazard multiplier; only cancellations feed the stress tally, never fills
                order_id = pick_cancel_target(book, total_weight, groups, rng)
                order = book.orders[order_id]
                side_, price_, size_ = order.side, order.price, order.size
                book.cancel_order(order_id)
                tracker.add_cancel(side_, price_, size_, t)
            else:  # uniform choice
                book.cancel_order(int(rng.choice(list(book.orders))))

        if book.best_bid is not None and book.best_ask is not None:
            last_mid = (book.best_bid + book.best_ask) / 2

        event_type[t] = ('limit', 'market', 'cancel').index(kind)
        if book.best_bid is not None:
            best_bid[t] = book.best_bid
        if book.best_ask is not None:
            best_ask[t] = book.best_ask
        bid_depth[t] = depth_profile(book, 'buy', K)
        ask_depth[t] = depth_profile(book, 'sell', K)

    return dict(event_type=event_type, best_bid=best_bid, best_ask=best_ask, bid_depth=bid_depth, ask_depth=ask_depth)
