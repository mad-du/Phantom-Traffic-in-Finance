from dataclasses import replace

import numpy as np
import pytest

import phantom.lob_sim as lob_sim
from phantom.lob import OrderBook
from phantom.lob_sim import LOBParams, StressTracker, hazard_multiplier, simulate_lob


def run(params, n_events=3000, seed=0):
    return simulate_lob(n_events, params, np.random.default_rng(seed))


@pytest.mark.parametrize('gamma', [0.0, 3.0])
def test_same_seed_is_reproducible(gamma):
    params = LOBParams(coupling_strength=gamma)
    a, b = run(params), run(params)
    assert all(np.array_equal(a[key], b[key], equal_nan=True) for key in a)


def test_uncoupled_event_mix_and_book_size(monkeypatch):
    """gamma = 0: limit/market/cancel shares and the number of resting orders match the model's steady state."""
    resting = []
    original = lob_sim.sample_event_type
    monkeypatch.setattr(lob_sim, 'sample_event_type', lambda book, params, rng: (resting.append(len(book.orders)), original(book, params, rng))[1])

    out = run(LOBParams(), n_events=30_000)
    mix = np.bincount(out['event_type'], minlength=3) / len(out['event_type'])
    assert mix == pytest.approx([0.497, 0.145, 0.357], abs=0.02)
    assert 33 <= np.mean(resting[5000:]) <= 41  # about (lambda - mu) / theta = 35, measured 37


def test_stress_rises_after_a_cancellation_and_decays_without_one():
    book = OrderBook()
    book.add_limit_order('buy', 100, 6)
    tracker = StressTracker(memory=50.0)

    assert tracker.stress(book, 'buy', 100, t=0) == 0.0
    tracker.add_cancel('buy', 100, 4, t=0)
    at_once = tracker.stress(book, 'buy', 100, t=0)
    assert at_once == pytest.approx(4 / (4 + 6))                   # D / (D + depth)

    later = tracker.stress(book, 'buy', 100, t=50)                 # one time constant later D has shrunk by e
    assert later == pytest.approx(4 / np.e / (4 / np.e + 6))
    assert later < at_once

    tracker.add_cancel('buy', 100, 4, t=50)                        # a fresh cancellation raises it again
    assert tracker.stress(book, 'buy', 100, t=50) > later

    assert tracker.stress(book, 'buy', 100, t=5000) < 1e-6         # fades toward zero
    assert list(tracker.stressed_ticks(t=5000)) == []              # and is pruned


def test_cancellation_raises_hazard_only_one_tick_behind():
    book = OrderBook()
    ids = {}
    for name, side, price in [('bid100', 'buy', 100), ('bid99', 'buy', 99), ('bid98', 'buy', 98),
                              ('ask101', 'sell', 101), ('ask102', 'sell', 102)]:
        ids[name], _ = book.add_limit_order(side, price, 5)
    tracker = StressTracker(memory=50.0)
    tracker.add_cancel('buy', 100, 3, t=0)                         # a bid at 100 was just cancelled

    multiplier = {name: hazard_multiplier(book, tracker, book.orders[order_id], gamma=3.0, t=0) for name, order_id in ids.items()}
    assert multiplier['bid99'] > 1.0                               # directly behind the stressed tick
    assert multiplier['bid99'] == pytest.approx(1 + 3.0 * 3 / (3 + 5))
    for untouched in ('bid100', 'bid98', 'ask101', 'ask102'):      # the stressed tick itself, two ticks behind, the other side
        assert multiplier[untouched] == 1.0

    tracker.add_cancel('sell', 101, 3, t=0)                        # asks mirror it: "behind" an ask is price + 1
    assert hazard_multiplier(book, tracker, book.orders[ids['ask102']], gamma=3.0, t=0) > 1.0


def test_coupled_run_keeps_invariants_and_records_only_cancellations(monkeypatch):
    """check_invariants runs inside every order operation, so a clean run means they held; cancels (not fills) feed the tally."""
    recorded = []
    original = StressTracker.add_cancel
    monkeypatch.setattr(StressTracker, 'add_cancel', lambda self, side, price, volume, t: (recorded.append((side, price, volume)), original(self, side, price, volume, t))[1])

    out = run(LOBParams(coupling_strength=3.0), n_events=5000)
    assert len(recorded) == int(np.sum(out['event_type'] == 2))    # exactly one tally update per cancel event
    assert all(volume > 0 for _, _, volume in recorded)


def test_fills_never_feed_the_stress_tally(monkeypatch):
    """Lots of market-order fills but zero cancellations: the tally must stay empty."""
    recorded = []
    monkeypatch.setattr(StressTracker, 'add_cancel', lambda self, *args: recorded.append(args))

    params = LOBParams(coupling_strength=3.0, cancel_rate=0.0, limit_rate=1.0, market_rate=0.8)
    out = run(params, n_events=3000)
    assert np.sum(out['event_type'] == 1) > 500                    # plenty of market orders
    assert np.sum(out['event_type'] == 2) == 0
    assert recorded == []


def test_coupling_does_not_empty_or_blow_up_the_book(monkeypatch):
    resting = []
    original = lob_sim.cancel_weights
    monkeypatch.setattr(lob_sim, 'cancel_weights', lambda book, params, tracker, t: (resting.append(len(book.orders)), original(book, params, tracker, t))[1])

    run(LOBParams(coupling_strength=3.0, market_rate=0.7), n_events=10_000)
    steady = np.array(resting[2000:])
    # At high load the book can momentarily hit 0 orders even without coupling (measured: 0.08% of steps uncoupled,
    # 0.5% coupled at mu = 0.7), so the checks are: bounded above, usually populated, and it always refills.
    assert steady.max() < 500
    assert steady.mean() > 3
    assert np.mean(steady == 0) < 0.02


def test_all_rates_zero_raises_when_coupled():
    with pytest.raises(ValueError):
        run(LOBParams(coupling_strength=1.0, limit_rate=0.0, market_rate=0.0, cancel_rate=0.0), n_events=5)
