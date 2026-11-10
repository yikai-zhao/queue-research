"""Counterexamples for research/execution time ordering at the markout horizon."""
import unittest
from queue_research.data import BookEvent
from queue_research.execution import simulate_order, comparison


def row(i, *, kind=1, qty=10, bid=1_000_000, ask=1_000_200, bid_qty=20,
        price=1_000_000, segment=0):
    return BookEvent(i, i * 1_000_000, kind, 100 + i, qty, price, 1,
                     ask, 20, bid, bid_qty, segment)


class StrictMarkoutHorizonTests(unittest.TestCase):
    def test_execution_at_markout_timestamp_is_not_a_historical_fill(self):
        tape = [row(0), row(1, bid_qty=20), row(2), row(3),
                row(4, kind=4, qty=30, bid_qty=1, bid=999_900)]
        for model in ('conservative', 'cancel_ahead'):
            with self.subTest(model=model):
                fill = simulate_order(tape, 0, 1, model=model,
                                      latency_events=1, horizon_events=4)
                self.assertEqual(fill.filled, 0)
                self.assertIsNone(fill.markout_ticks)

    def test_before_horizon_visible_execution_remains_eligible(self):
        tape = [row(0), row(1, bid_qty=20), row(2),
                row(3, kind=4, qty=30, bid_qty=1), row(4)]
        f = simulate_order(tape, 0, 1, latency_events=1, horizon_events=4)
        self.assertEqual(f.filled, 10)
        self.assertEqual(f.fill_index, 3)
        self.assertIsNotNone(f.markout_ticks)

    def test_no_end_of_horizon_fill_in_reported_fraction(self):
        tape = [row(0), row(1, bid_qty=20), row(2), row(3),
                row(4, kind=4, qty=30, bid_qty=1)]
        result = comparison(tape, [(0,1)], latency_events=1,
                            horizon_events=4, quantity=10)
        self.assertEqual(result['conservative']['filled_orders'], 0)
        self.assertEqual(result['cancel_ahead']['filled_orders'], 0)
        # Deliberately unrealistic model is still a distinct upper-bound toy.
        self.assertEqual(result['naive_touch']['filled_orders'], 1)
