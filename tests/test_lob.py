import random

import pytest

from phantom.lob import OrderBook


@pytest.fixture
def asks_book():
    """asks = {101: [A(5), B(3)], 102: [C(4)]}; returns (book, A_id, B_id, C_id)."""
    book = OrderBook()
    a, _ = book.add_limit_order('sell', 101, 5)
    b, _ = book.add_limit_order('sell', 101, 3)
    c, _ = book.add_limit_order('sell', 102, 4)
    return book, a, b, c


def test_partial_fill_keeps_front_of_queue(asks_book):
    book, a, b, _ = asks_book
    assert book.match_market_order('buy', 6) == [(a, 101, 5), (b, 101, 1)]
    front = book.asks[101][0]
    assert front.order_id == b and front.size == 2


def test_market_order_sweeps_side_and_drops_excess(asks_book):
    book, a, b, c = asks_book
    assert book.match_market_order('buy', 20) == [(a, 101, 5), (b, 101, 3), (c, 102, 4)]
    assert not book.asks and not book.orders and book.best_ask is None


def test_limit_price_stops_the_walk(asks_book):
    book, a, b, _ = asks_book
    fills = book._match('buy', 20, limit_price=101)
    book.check_invariants()
    assert fills == [(a, 101, 5), (b, 101, 3)]
    assert book.depth_at('sell', 102) == 4


def test_aggressive_limit_order_fills_then_rests_remainder(asks_book):
    book, *_ = asks_book
    _, fills = book.add_limit_order('buy', 102, 20)
    assert sum(size for _, _, size in fills) == 12
    assert book.best_bid == 102 and book.depth_at('buy', 102) == 8
    assert book.best_ask is None


def test_sell_walks_bids_highest_first_fifo_within_level():
    book = OrderBook()
    x, _ = book.add_limit_order('buy', 99, 4)
    y, _ = book.add_limit_order('buy', 100, 2)
    z, _ = book.add_limit_order('buy', 100, 3)
    assert book.match_market_order('sell', 7) == [(y, 100, 2), (z, 100, 3), (x, 99, 2)]


def test_non_crossing_limit_order_rests():
    book = OrderBook()
    book.add_limit_order('buy', 99, 5)
    book.add_limit_order('sell', 101, 5)
    assert (book.best_bid, book.best_ask) == (99, 101)


def test_cancel_removes_order_and_empty_level(asks_book):
    book, _, b, c = asks_book
    assert book.cancel_order(b)
    assert not book.cancel_order(b)  # already gone
    assert book.depth_at('sell', 101) == 5
    assert book.cancel_order(c)
    assert 102 not in book.asks


@pytest.mark.parametrize('bad_size', [0, -3])
def test_non_positive_size_is_rejected(bad_size):
    book = OrderBook()
    with pytest.raises(ValueError):
        book.add_limit_order('buy', 100, bad_size)
    with pytest.raises(ValueError):
        book.match_market_order('sell', bad_size)


def test_invariant_checker_catches_a_corrupted_book():
    book = OrderBook()
    book.add_limit_order('buy', 100, 5)
    book.volume_matched += 1  # simulate a matching engine that forgot to update the books consistently
    with pytest.raises(AssertionError):
        book.check_invariants()


class NaiveBook:
    """Slow but obviously-correct reference: a flat list of orders, filtered and sorted on every match."""

    def __init__(self):
        self.rows, self.seq = [], 0  # (side, price, arrival_seq, order_id, size)

    def match(self, side, size, limit):
        fills = []
        opposite = 'sell' if side == 'buy' else 'buy'
        while size > 0:
            candidates = [r for r in self.rows if r[0] == opposite
                          and (limit is None or (r[1] <= limit if side == 'buy' else r[1] >= limit))]
            if not candidates:
                break
            key = (lambda r: (r[1], r[2])) if side == 'buy' else (lambda r: (-r[1], r[2]))
            best = min(candidates, key=key)
            traded = min(size, best[4])
            fills.append((best[3], best[1], traded))
            size -= traded
            self.rows.remove(best)
            if best[4] > traded:
                self.rows.append((best[0], best[1], best[2], best[3], best[4] - traded))
        return fills

    def add(self, order_id, side, price, size):
        fills = self.match(side, size, price)
        remaining = size - sum(f[2] for f in fills)
        if remaining:
            self.seq += 1
            self.rows.append((side, price, self.seq, order_id, remaining))
        return fills

    def snapshot(self):
        return sorted((r[0], r[1], r[3], r[4]) for r in self.rows)


@pytest.mark.parametrize('seed', [1, 2, 3])
def test_random_events_match_naive_reference(seed):
    rng = random.Random(seed)
    book, ref, ids = OrderBook(), NaiveBook(), []

    for step in range(10_000):
        r = rng.random()
        if r < 0.55:
            side, price, size = rng.choice(['buy', 'sell']), rng.randint(95, 105), rng.randint(1, 9)
            order_id, fills = book.add_limit_order(side, price, size)
            assert fills == ref.add(order_id, side, price, size), f"limit order mismatch at step {step}"
            ids.append(order_id)
        elif r < 0.8:
            side, size = rng.choice(['buy', 'sell']), rng.randint(1, 25)
            assert book.match_market_order(side, size) == ref.match(side, size, None), f"market order mismatch at step {step}"
        elif ids:
            order_id = rng.choice(ids)
            was_resting = any(row[3] == order_id for row in ref.rows)
            assert book.cancel_order(order_id) == was_resting, f"cancel mismatch at step {step}"
            ref.rows = [row for row in ref.rows if row[3] != order_id]

        if step % 250 == 0:
            snapshot = sorted((o.side, o.price, o.order_id, o.size) for o in book.orders.values())
            assert snapshot == ref.snapshot(), f"book state diverged at step {step}"
