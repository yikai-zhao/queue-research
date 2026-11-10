import unittest
from scripts.run_controls import panel

class ControlsTests(unittest.TestCase):
    def test_reproducible_negative_and_positive_control_panel(self):
        a=panel([11,12],count=1500,permutations=5)
        b=panel([11,12],count=1500,permutations=5)
        self.assertEqual(a,b)
        self.assertEqual(len(a['negative_and_positive_controls']),4)
        self.assertEqual(a['n_seeds'],2)
        self.assertIn('null_nominal_5pct_false_positives',a)
