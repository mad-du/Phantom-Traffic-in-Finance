from collections import deque
from dataclasses import dataclass


@dataclass(eq=False)  # eq=False: two orders are the same only if they are the same object (identity, not field values)
class Order:
    order_id: int
    side: str   # 'buy' or 'sell'
    price: int  # integer price ticks
    size: int   # remaining (unfilled) size


class OrderBook:
    """Single-asset limit order book with integer price ticks and price-time priority.

    bids / asks map price -> deque of resting Orders, oldest first (FIFO within a price level).
    A buy order rests in `bids`, a sell order rests in `asks`.
    """

    def __init__(self):
        self.bids = {}
        self.asks = {}
        self.orders = {}   # order_id -> Order, resting orders only
        self._next_id = 0
        # Volume bookkeeping, used by check_invariants:  resting == rested - matched - cancelled
        self.volume_rested = 0
        self.volume_matched = 0    # counted on the MAKER (resting) side of each fill
        self.volume_cancelled = 0

    # ---- read-only views -------------------------------------------------------------

    @property
    def best_bid(self):
        return max(self.bids) if self.bids else None

    @property
    def best_ask(self):
        return min(self.asks) if self.asks else None

    def depth_at(self, side, price):
        """Total resting size at one price level of the given side ('buy' = bids, 'sell' = asks)."""
        level = (self.bids if side == 'buy' else self.asks).get(price)
        return sum(order.size for order in level) if level else 0

    # ---- matching (yours) ------------------------------------------------------------

    def _match(self, taker_side, size, limit_price=None):
        """
        Match an incoming (taker) order of `size` against the opposite side of the book.
        """

        if taker_side not in ('buy', 'sell'):
            raise ValueError("taker_side must be 'buy' or 'sell'")
        if taker_side == 'buy':
            book = self.asks
            price_iter = iter(sorted(book))  # lowest ask first
            price_cmp = lambda price: limit_price is None or price <= limit_price
        else:  # taker_side == 'sell'
            book = self.bids
            price_iter = iter(sorted(book, reverse=True))  # highest bid first
            price_cmp = lambda price: limit_price is None or price >= limit_price

        fills = []
        for price in price_iter:
            if not price_cmp(price):
                break  # limit price stops the walk

            level = book[price]
            while level and size > 0:
                maker_order = level[0]
                fill_size = min(size, maker_order.size)
                fills.append((maker_order.order_id, price, fill_size))
                size -= fill_size
                maker_order.size -= fill_size
                self.volume_matched += fill_size

                if maker_order.size == 0:
                    # fully filled: remove from the front of the deque and from the id index
                    level.popleft()
                    del self.orders[maker_order.order_id]

            if not level:
                del book[price]  # remove empty price level

            if size == 0:
                break  # taker order fully filled

        return fills

    # ---- public order entry (done) ---------------------------------------------------

    def match_market_order(self, side, size):
        """Execute a market order. Any part the book cannot fill is dropped. Returns the fills."""
        if size <= 0:
            raise ValueError("order size must be positive")
        fills = self._match(side, size)
        self.check_invariants()
        return fills

    def add_limit_order(self, side, price, size):
        """Submit a limit order: trade whatever crosses the spread now, rest the remainder.

        Returns (order_id, fills). The order_id is for cancelling; it is only usable if some size rested.
        """
        if size <= 0:
            raise ValueError("order size must be positive")
        order_id = self._next_id
        self._next_id += 1

        fills = self._match(side, size, limit_price=price)
        remaining = size - sum(fill_size for _, _, fill_size in fills)

        if remaining > 0:
            order = Order(order_id, side, price, remaining)
            book = self.bids if side == 'buy' else self.asks
            book.setdefault(price, deque()).append(order)
            self.orders[order_id] = order
            self.volume_rested += remaining

        self.check_invariants()
        return order_id, fills

    def cancel_order(self, order_id):
        """Remove a resting order from the book. Returns True if it was resting, False otherwise."""
        order = self.orders.pop(order_id, None)
        if order is None:
            return False

        book = self.bids if order.side == 'buy' else self.asks
        level = book[order.price]
        level.remove(order)  # identity match thanks to eq=False; O(n) in the level length
        if not level:
            del book[order.price]

        self.volume_cancelled += order.size
        self.check_invariants()
        return True

    # ---- invariants ------------------------------------------------------------------

    def check_invariants(self):
        """Raise AssertionError if the book is in an impossible state. Called after every event."""
        if self.bids and self.asks:
            assert max(self.bids) < min(self.asks), f"crossed book: bid {max(self.bids)} >= ask {min(self.asks)}"

        resting = 0
        for book, side in ((self.bids, 'buy'), (self.asks, 'sell')):
            for price, level in book.items():
                assert level, f"empty price level left in the book at {price}"
                for order in level:
                    assert order.size > 0, f"order {order.order_id} has non-positive size {order.size}"
                    assert order.side == side and order.price == price, f"order {order.order_id} is on the wrong level"
                    assert self.orders.get(order.order_id) is order, f"order {order.order_id} missing from the id index"
                    resting += order.size

        assert len(self.orders) == sum(len(level) for book in (self.bids, self.asks) for level in book.values()), \
            "id index and price levels disagree on the number of resting orders"
        assert resting == self.volume_rested - self.volume_matched - self.volume_cancelled, \
            f"volume not conserved: resting {resting} != rested {self.volume_rested} - matched {self.volume_matched} - cancelled {self.volume_cancelled}"
