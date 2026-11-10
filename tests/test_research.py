import math
import unittest
from dataclasses import replace
from queue_research.research import screen,side
from queue_research.synthetic import generate


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.null=generate(4000,11,False)
        cls.predictive=generate(4000,11,True)

    def test_side_threshold_and_no_signal(self):
        self.assertEqual([side(x,.25) for x in (-.5,-.1,0,.1,.5)],[-1,0,0,0,1])

    def test_hypothesis_selection_uses_train_only(self):
        before=screen(self.null, horizon=30,null_iterations=0)
        cut=before.train_end
        tampered=list(self.null)
        for i in range(cut,len(tampered)):
            old=tampered[i]
            tampered[i]=replace(old,bid_qty=old.ask_qty,ask_qty=old.bid_qty)
        after=screen(tampered,horizon=30,null_iterations=0)
        self.assertEqual(after.threshold,before.threshold)
        self.assertEqual(after.train_mean_signed_ticks,before.train_mean_signed_ticks)
        self.assertEqual(after.train_samples,before.train_samples)

    def test_split_and_horizon_both_chronological(self):
        x=screen(self.null,horizon=30,null_iterations=0)
        self.assertEqual(x.train_end,x.test_start)
        self.assertGreater(x.test_samples,0)
        self.assertGreater(x.train_samples,0)
        self.assertIsNone(x.shifted_null_p_value)

    def test_seeded_reproducible_test_and_null(self):
        self.assertEqual(screen(self.null,null_iterations=20,seed=37),
                         screen(self.null,null_iterations=20,seed=37))

    def test_predeclared_signal_grid_has_known_predictive_control(self):
        x=screen(self.predictive,horizon=30,null_iterations=40,seed=11)
        self.assertGreater(x.test_mean_signed_ticks,0)
        self.assertGreater(x.test_samples,50)
        # This is constructed synthetic positive control, not market alpha.

    def test_null_control_is_not_guaranteed_significant(self):
        x=screen(self.null,horizon=30,null_iterations=40,seed=11)
        self.assertGreater(x.shifted_null_p_value,0.1)

    def test_bad_selection_controls_raise(self):
        for kwargs in [dict(horizon=0),dict(train_fraction=1),dict(null_iterations=-1),
                       dict(thresholds=(-.1,)),dict(thresholds=(math.nan,))]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                screen(self.null,**kwargs)

    def test_short_sample_cannot_fake_robust_labeling(self):
        with self.assertRaises(ValueError):screen(self.null[:100],horizon=30)

    def test_null_association_can_fluctuate(self):
        values=[screen(generate(3000,i,False),null_iterations=0).test_mean_signed_ticks for i in range(4)]
        self.assertTrue(all(isinstance(x,float) for x in values))
        self.assertTrue(any(x != values[0] for x in values[1:]))

class HaltPurgingTests(unittest.TestCase):
    def test_labels_do_not_cross_session_boundary(self):
        from queue_research.research import _scores
        rows=generate(200,seed=12,predictive=True)
        rows=[replace(x,segment=0 if i<100 else 1) for i,x in enumerate(rows)]
        scores=_scores(rows,horizon=20,start=90,end=130,threshold=.01)
        self.assertEqual(len(scores),10)  # first 10 of window have invalid labels
