"""Failure-oriented checks for time ordering in within-tape walk forward."""
import unittest
from dataclasses import replace
from queue_research.synthetic import generate
from queue_research.walkforward import expanding_folds


class ExpandingWalkforwardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = generate(4000, seed=11, predictive=True)

    def test_nonoverlap_and_fold_boundaries(self):
        result = expanding_folds(self.rows, horizon=30)
        self.assertEqual(result['fold_count'],4)
        self.assertEqual([f['test_start'] for f in result['folds']],[1600,2200,2800,3400])
        self.assertTrue(all(f['test_end_exclusive'] - f['test_start'] >= 31 for f in result['folds']))
        self.assertTrue(all(f['test_count'] <= (f['test_end_exclusive']-f['test_start'])//31+1 for f in result['folds']))
        self.assertEqual(sum(f['test_count'] for f in result['folds']),result['total_disjoint_test_signals'])

    def test_cannot_tune_first_fold_on_future(self):
        original = expanding_folds(self.rows, horizon=30)
        tampered=list(self.rows)
        for i in range(1600,len(tampered)):
            x=tampered[i]
            tampered[i]=replace(x,ask_qty=x.bid_qty,bid_qty=x.ask_qty)
        changed = expanding_folds(tampered,horizon=30)
        self.assertEqual(original['folds'][0]['chosen_threshold'],changed['folds'][0]['chosen_threshold'])
        self.assertEqual(original['folds'][0]['train_signals'],changed['folds'][0]['train_signals'])
        # The test statistic may coincidentally be zero in both tapes; only
        # the fitted threshold and training evidence must be invariant.

    def test_halt_boundary_excludes_labels(self):
        rows=[replace(x,segment=i//30) for i,x in enumerate(self.rows)]
        result=expanding_folds(rows,horizon=30)
        self.assertEqual(result['total_disjoint_test_signals'],0)
        self.assertIsNone(result['pooled_nonoverlap_mean_signed_ticks'])

    def test_deterministic(self):
        self.assertEqual(expanding_folds(self.rows),expanding_folds(self.rows))

    def test_invalid_splits_and_thresholds(self):
        for kwargs in (dict(horizon=5000),dict(fold_fraction=.00001),
                       dict(initial_train_fraction=.9,fold_fraction=.2),
                       dict(thresholds=()),dict(thresholds=(.2,.2)),
                       dict(min_training_signals=0)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                expanding_folds(self.rows,**kwargs)

    def test_no_signal_does_not_fake_zero_profit(self):
        result=expanding_folds(self.rows,thresholds=(1,),min_training_signals=10**6)
        self.assertTrue(all(f['status']=='insufficient_training_signals' for f in result['folds']))
        self.assertIsNone(result['pooled_nonoverlap_mean_signed_ticks'])


if __name__=='__main__': unittest.main()
