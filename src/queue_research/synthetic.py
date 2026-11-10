"""Small stylized, seeded book generator; NEVER presented as empirical market data."""
from __future__ import annotations
import random
from .data import BookEvent


def generate(count: int = 6000, seed: int = 17, predictive: bool = False) -> list[BookEvent]:
    if count < 100 or count > 200_000:
        raise ValueError('count must be 100..200000')
    rng = random.Random(seed)
    mid_tick = 10_000
    bid_qty = ask_qty = 180
    regime = 1
    records = []
    for i in range(count):
        # Deliberately stylized controlled intervention, not an exchange tape.
        # In predictive mode the next midprice change follows the current
        # book-pressure regime; under the null it is independent of that regime.
        if i % 80 == 0:
            regime = rng.choice((-1, 1))
            bid_qty = 240 if regime == 1 else 75
            ask_qty = 75 if regime == 1 else 240
        if i % 80 == 65:
            mid_tick += regime if predictive else rng.choice((-1, 1))
            bid_qty = 200 if regime == 1 else 90
            ask_qty = 90 if regime == 1 else 200
        bid, ask = (mid_tick - 1)*100, (mid_tick + 1)*100
        side = 1 if rng.random() < 0.5 else -1
        kind = rng.choices((1, 2, 4), weights=(5, 2, 5))[0]
        qty = rng.randrange(5, 45)
        if side == 1:
            if kind == 1:
                bid_qty += qty
            else:
                qty = min(qty, bid_qty - 1)
                bid_qty -= qty
        else:
            if kind == 1:
                ask_qty += qty
            else:
                qty = min(qty, ask_qty - 1)
                ask_qty -= qty
        records.append(BookEvent(i, i * 4_000_000, kind, i+1, qty,
                                 bid if side == 1 else ask, side,
                                 ask, ask_qty, bid, bid_qty))
    return records
