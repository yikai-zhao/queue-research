"""Unit contracts for reproducible calibration, not fit to favorable outcomes."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_null_calibration import evaluate,wilson

class NullCalibrationTests(unittest.TestCase):
    def test_wilson_bounds(self):
        self.assertEqual(wilson(0,100)[0],0)
        self.assertLess(wilson(0,100)[1],.04)
        self.assertGreater(wilson(100,100)[0],.96)
    def test_bad_counts(self):
        for k,n in ((-1,10),(11,10),(0,0)):
            with self.assertRaises(ValueError):wilson(k,n)
    def test_repeatable_seed_panel(self):
        a=evaluate(seeds=3,events=1000,shifts=9)
        b=evaluate(seeds=3,events=1000,shifts=9)
        self.assertEqual(a,b)
        self.assertEqual(len(a['results']),2)
        self.assertEqual(a['results'][0]['cases'][0]['seed'],0)
        self.assertEqual(a['results'][1]['cases'][-1]['seed'],2)
        self.assertEqual(a['configuration']['thresholds'],[.15,.25,.35,.45])
    def test_rejects_invalid_setup(self):
        with self.assertRaises(ValueError):evaluate(seeds=0)
        with self.assertRaises(ValueError):evaluate(events=100)
        with self.assertRaises(ValueError):evaluate(shifts=1001)
if __name__=='__main__':unittest.main()
