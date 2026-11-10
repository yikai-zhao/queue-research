"""Research-integrity regressions, including previously untested session leak."""
import math
import unittest
from dataclasses import replace
from queue_research.data import BookEvent
from queue_research.execution import comparison, simulate_order
from queue_research.experiment import study
from queue_research.research import screen
from queue_research.robustness import phase_sensitivity, execution_sensitivity
from queue_research.synthetic import generate


def event(i, *, segment=0, kind=1, qty=1, bid_qty=10, price=1000000):
    return BookEvent(i, i*1000000, kind, i+1, qty, price, 1,
                     1000200, 10, 1000000, bid_qty, segment)


class SessionNoLookaheadTests(unittest.TestCase):
    def test_filled_before_halt_cannot_use_post_halt_markout(self):
        rows = [event(0), event(1, bid_qty=3),
                event(2, kind=4, qty=20, bid_qty=1),
                event(3), event(4, segment=1)]
        # The old implementation (incorrectly) filled at t=2 and marked out
        # to a price AFTER the discontinuity. The trade is now ineligible.
        for model in ('naive_touch', 'conservative', 'cancel_ahead'):
            with self.subTest(model=model):
                out = simulate_order(rows, 0, 1, model=model,
                                     latency_events=1, horizon_events=4)
                self.assertEqual(out.filled, 0)
                self.assertIsNone(out.markout_ticks)
                self.assertEqual(out.status, 'ineligible_session_boundary')

    def test_boundary_probes_are_not_counted_as_non_fills(self):
        rows = [event(i, segment=0 if i < 5 else 1) for i in range(10)]
        summary = comparison(rows, [(0, 1)], latency_events=1,
                             horizon_events=5, quantity=10)
        for mode in summary.values():
            self.assertEqual(mode['hypothetical_orders'], 1)
            self.assertEqual(mode['ineligible_session_boundary_orders'], 1)
            self.assertEqual(mode['eligible_orders'], 0)
            self.assertIsNone(mode['eligible_fill_quantity_fraction'])
            self.assertIsNone(mode['mean_fill_conditional_markout_ticks'])

    def test_latency_quote_departure_not_reclassified_as_session_boundary(self):
        rows = [event(i) for i in range(5)]
        rows[1] = replace(rows[1], bid=1000100)
        res = simulate_order(rows, 0, 1, latency_events=1, horizon_events=4)
        self.assertEqual(res.status, 'no_fill_quote_changed_during_latency')
        self.assertEqual(res.limit_price, rows[0].bid)

    def test_fee_changes_only_markout_not_fill(self):
        rows = [event(i) for i in range(5)]
        before = simulate_order(rows, 0, 1, model='naive_touch',
                                latency_events=1, horizon_events=4, fee_bps=0)
        after = simulate_order(rows, 0, 1, model='naive_touch',
                               latency_events=1, horizon_events=4, fee_bps=3)
        self.assertEqual(before.filled, after.filled)
        self.assertEqual(before.limit_price, after.limit_price)
        self.assertAlmostEqual(before.markout_ticks - after.markout_ticks, 3.0)

    def test_queue_model_ordering_for_seeded_generated_events(self):
        rows = generate(4000, seed=123, predictive=False)
        signals = [(i, 1 if rows[i].imbalance > 0 else -1)
                   for i in range(0, 3900, 43)]
        for i, d in signals:
            conservative = simulate_order(rows, i, d, model='conservative')
            optimistic = simulate_order(rows, i, d, model='cancel_ahead')
            naive = simulate_order(rows, i, d, model='naive_touch')
            self.assertLessEqual(conservative.filled, optimistic.filled)
            self.assertLessEqual(optimistic.filled, naive.filled)


class PhaseAndExecutionIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = generate(4000, 11, True)
        cls.fit = screen(cls.rows, null_iterations=0)

    def test_phases_nonoverlapping_label_windows(self):
        result = phase_sensitivity(self.rows, self.fit)
        self.assertEqual(result['phases_evaluated'], self.fit.horizon + 1)
        self.assertTrue(0 <= result['positive_mean_phases'] <= result['phases_evaluated'])
        # A particular offset is a deterministic h+1 spaced cohort.
        start = self.fit.test_start
        expected = [i for i in range(start, len(self.rows)-self.fit.horizon,
                                     self.fit.horizon+1)
                    if abs(self.rows[i].imbalance) >= self.fit.threshold]
        self.assertEqual(result['phases'][0]['signals'], len(expected))
        self.assertEqual(result['signals_min_per_phase'] > 0, True)
        self.assertIn('not independent', result['interpretation'].lower())

    def test_phase_diagnostics_do_not_refit_training(self):
        fit = self.fit
        before = phase_sensitivity(self.rows, fit)
        altered = list(self.rows)
        for i in range(fit.test_start, len(altered)):
            x = altered[i]
            altered[i] = replace(x, bid_qty=x.ask_qty, ask_qty=x.bid_qty)
        after = phase_sensitivity(altered, fit)
        self.assertEqual(fit.threshold, self.fit.threshold)
        self.assertNotEqual(before['phases'], after['phases'])

    def test_phase_diagnostic_rejects_halt_crossings(self):
        rows = [replace(x, segment=0 if i < 3200 else 1)
                for i, x in enumerate(self.rows)]
        before = phase_sensitivity(self.rows, self.fit)
        after = phase_sensitivity(rows, self.fit)
        self.assertLessEqual(after['signals_median_per_phase'],
                             before['signals_median_per_phase'])

    def test_predeclared_sensitivity_changes_execution_only(self):
        signals = [(i, 1) for i in range(2500, 3800, 60)]
        result = execution_sensitivity(self.rows, signals, horizon=30,
                                       latencies=(1, 2), fees_bps=(0, 3))
        self.assertEqual(len(result['grid']), 4)
        self.assertEqual(result['hypothetical_signals'], len(signals))
        for mode in ('naive_touch','conservative','cancel_ahead'):
            # Fixed latency, different hypothetical fees: fills unchanged.
            a = result['grid'][0]['models'][mode]
            b = result['grid'][1]['models'][mode]
            self.assertEqual(a['filled_orders'], b['filled_orders'])
            self.assertEqual(a['fill_quantity_fraction'], b['fill_quantity_fraction'])
            if a['mean_fill_conditional_markout_ticks'] is not None:
                self.assertGreaterEqual(a['mean_fill_conditional_markout_ticks'],
                                        b['mean_fill_conditional_markout_ticks'])

    def test_short_horizon_uses_only_valid_predeclared_latencies(self):
        report = study(self.rows, source='synthetic:predictive',
                       horizon=5, latency=1, null_iterations=0)
        self.assertEqual(report['execution_assumption_sensitivity']
                         ['predeclared_latencies_events'], [1, 2])

    def test_circular_null_refuses_cross_halt_feature_rotation(self):
        rows = [replace(x, segment=0 if i < 3100 else 1)
                for i, x in enumerate(self.rows)]
        result = screen(rows, horizon=30, null_iterations=49, seed=11)
        self.assertGreater(result.test_samples, 0)
        self.assertIsNone(result.shifted_null_p_value)
        self.assertEqual(result.null_diagnostic_status,
                         'disabled_multiple_segments')

    def test_parameter_sensitivity_rejects_invalid_grid(self):
        for extra in ({'latencies': (0,)},{'latencies': (30,)},
                      {'latencies': (1, 1)}, {'fees_bps': (math.nan,)},
                      {'fees_bps': (0, 0)}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                execution_sensitivity(self.rows, [(2500,1)], horizon=30, **extra)

    def test_study_exposes_honest_robustness_breakdown(self):
        report = study(self.rows, source='synthetic:predictive:seed=11',
                       null_iterations=0)
        self.assertEqual(report['source_type'], 'synthetic')
        self.assertEqual(report['holdout_phase_sensitivity']['phases_evaluated'], 31)
        self.assertEqual(len(report['execution_assumption_sensitivity']['grid']), 9)
        self.assertTrue(all(x['models']['conservative']['hypothetical_orders'] ==
                            report['evaluation']['test_probes']
                            for x in report['execution_assumption_sensitivity']['grid']))


if __name__ == '__main__':
    unittest.main()
