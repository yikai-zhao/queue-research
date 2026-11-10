import unittest
from queue_research.data import BookEvent
from queue_research.execution import simulate_order,comparison


def book(i, kind=1, side=1, qty=10, bid=1000000, ask=1000200, bid_qty=20, ask_qty=20, price=None):
    return BookEvent(i,i*1_000_000,kind,i+1,qty,
                     price if price is not None else (bid if side==1 else ask),
                     side,ask,ask_qty,bid,bid_qty)


class QueueTests(unittest.TestCase):
    def test_latent_order_does_not_fill_on_signal_event(self):
        rows=[book(i) for i in range(5)]
        v=simulate_order(rows,0,1,latency_events=1,horizon_events=4)
        self.assertEqual(v.filled,0)
        self.assertEqual(v.activation_index,1)

    def test_naive_touch_is_deliberately_unrealistic(self):
        rows=[book(i) for i in range(5)]
        self.assertEqual(simulate_order(rows,0,1,model='naive_touch',latency_events=1,horizon_events=4).filled,10)
        self.assertEqual(simulate_order(rows,0,1,latency_events=1,horizon_events=4).filled,0)

    def test_conservative_queue_consumes_only_visible_executions(self):
        rows=[book(0),book(1,bid_qty=20),book(2,kind=4,qty=10,bid_qty=10),
              book(3,kind=4,qty=16,bid_qty=2),book(4,kind=4,qty=8,bid_qty=1),book(5)]
        result=simulate_order(rows,0,1,latency_events=1,horizon_events=5)
        self.assertEqual(result.filled,10)
        self.assertEqual(result.fill_index,3)

    def test_partial_fill_does_not_claim_full_fill(self):
        rows=[book(0),book(1,bid_qty=20),book(2,kind=4,qty=24,bid_qty=1),book(3),book(4)]
        result=simulate_order(rows,0,1,latency_events=1,horizon_events=4)
        self.assertEqual(result.filled,4)
        self.assertEqual(result.quantity,10)

    def test_cancellation_model_bounds_queue_position(self):
        rows=[book(0),book(1,bid_qty=20),book(2,kind=2,qty=18,bid_qty=2),
              book(3,kind=4,qty=5,bid_qty=1),book(4),book(5)]
        strict=simulate_order(rows,0,1,latency_events=1,horizon_events=5)
        optimistic=simulate_order(rows,0,1,model='cancel_ahead',latency_events=1,horizon_events=5)
        self.assertEqual(strict.filled,0)
        self.assertEqual(optimistic.filled,3)

    def test_no_free_fill_when_price_level_disappears(self):
        rows=[book(0),book(1),book(2,bid=1000100,ask=1000300),
              book(3,kind=4,qty=200,bid=1000000,ask=1000200),book(4)]
        self.assertEqual(simulate_order(rows,0,1,latency_events=1,horizon_events=4).filled,0)

    def test_side_direction_must_match_resting_order(self):
        rows=[book(0,side=-1),book(1),book(2,kind=4,side=-1,qty=50),book(3),book(4)]
        self.assertEqual(simulate_order(rows,0,1,latency_events=1,horizon_events=4).filled,0)

    def test_sell_side_fills_at_ask(self):
        rows=[book(0),book(1,ask_qty=15),book(2,kind=4,side=-1,qty=30,ask_qty=1),book(3),book(4)]
        self.assertEqual(simulate_order(rows,0,-1,latency_events=1,horizon_events=4).filled,10)

    def test_fee_is_subtracted_for_positive_and_negative_sides(self):
        rows=[book(i) for i in range(5)]
        result=simulate_order(rows,0,1,model='naive_touch',latency_events=1,horizon_events=4,fee_bps=1)
        self.assertAlmostEqual(result.markout_ticks,0.0)
        result=simulate_order(rows,0,-1,model='naive_touch',latency_events=1,horizon_events=4,fee_bps=1)
        self.assertAlmostEqual(result.markout_ticks,-0.0002)

    def test_reject_invalid_inputs(self):
        rows=[book(i) for i in range(5)]
        for args in [dict(direction=0),dict(direction=1,latency_events=0),
                     dict(direction=1,horizon_events=1),dict(direction=1,quantity=0),
                     dict(direction=1,model='oracle'),dict(direction=1,fee_bps=-10)]:
            with self.subTest(args=args),self.assertRaises(ValueError):
                simulate_order(rows,0,**args)

    def test_model_fill_bound_in_comparison(self):
        rows=[book(0),book(1,bid_qty=20),book(2,kind=2,qty=18,bid_qty=2),
              book(3,kind=4,qty=5,bid_qty=1),book(4),book(5)]
        rep=comparison(rows,[(0,1)],latency_events=1,horizon_events=5)
        self.assertEqual(rep['naive_touch']['fill_quantity_fraction'],1)
        self.assertGreaterEqual(rep['cancel_ahead']['fill_quantity_fraction'],rep['conservative']['fill_quantity_fraction'])
        self.assertEqual(rep['conservative']['mean_fill_conditional_markout_ticks'],None)

class PostEventQuoteSemanticsTests(unittest.TestCase):
    def test_final_execution_counts_even_if_quote_disappears_same_row(self):
        # Exact real-data semantic: event row j shows the book AFTER execution.
        # Last trade at 1000000 causes bid to move down to 999900.
        rows=[book(0),book(1,bid_qty=8),
              book(2,kind=4,qty=30,bid=999900,ask=1000100,price=1000000),
              book(3,bid=999900,ask=1000100),book(4,bid=999900,ask=1000100)]
        x=simulate_order(rows,0,1,latency_events=1,horizon_events=4)
        self.assertEqual(x.filled,10)
        self.assertEqual(x.fill_index,2)

    def test_quote_leaves_without_execution_does_not_fill(self):
        rows=[book(0),book(1,bid_qty=8),
              book(2,kind=3,qty=8,bid=999900,ask=1000100,price=1000000),
              book(3,bid=999900,ask=1000100),book(4,bid=999900,ask=1000100)]
        self.assertEqual(simulate_order(rows,0,1,latency_events=1,horizon_events=4).filled,0)

class NoActivationLookaheadTests(unittest.TestCase):
    def test_limit_price_is_selected_before_latency_not_at_arrival(self):
        rows=[book(0,bid=1000000,ask=1000200),
              book(1,bid=1000100,ask=1000300),
              book(2,bid=1000100,ask=1000300),
              book(3,bid=1000100,ask=1000300)]
        for model in ('naive_touch','conservative','cancel_ahead'):
            x=simulate_order(rows,0,1,model=model,latency_events=1,horizon_events=3)
            self.assertEqual(x.limit_price,1000000)
            self.assertEqual(x.filled,0)

    def test_future_book_change_cannot_change_signal_quote(self):
        rows=[book(0,bid=1000000,ask=1000200),book(1),book(2),book(3)]
        a=simulate_order(rows,0,1,model='naive_touch',latency_events=1,horizon_events=3)
        rows[3]=book(3,bid=999000,ask=999200)
        b=simulate_order(rows,0,1,model='naive_touch',latency_events=1,horizon_events=3)
        self.assertEqual(a.limit_price,b.limit_price)
        self.assertEqual(a.fill_index,b.fill_index)

class SessionBoundaryTests(unittest.TestCase):
    def test_no_order_entered_on_new_session_after_latency(self):
        from dataclasses import replace
        rows=[book(i) for i in range(5)]
        rows=[replace(x,segment=0 if i==0 else 1) for i,x in enumerate(rows)]
        for model in ('conservative','naive_touch','cancel_ahead'):
            self.assertEqual(simulate_order(rows,0,1,model=model,latency_events=1,horizon_events=4).filled,0)

    def test_no_order_fills_after_session_discontinuity(self):
        from dataclasses import replace
        rows=[book(0),book(1,bid_qty=5),book(2,kind=4,qty=30),book(3),book(4)]
        rows=[replace(x,segment=0 if i<2 else 1) for i,x in enumerate(rows)]
        self.assertEqual(simulate_order(rows,0,1,latency_events=1,horizon_events=4).filled,0)
