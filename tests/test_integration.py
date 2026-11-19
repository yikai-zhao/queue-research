import json
import tempfile
from pathlib import Path
import unittest
from statistics import mean
from queue_research.synthetic import generate
from queue_research.experiment import study, main
from queue_research.research import _scores, screen


class IntegrationTests(unittest.TestCase):
    def test_study_is_deterministic_and_labelled_synthetic(self):
        data=generate(4000,seed=11,predictive=True)
        a=study(data,source='synthetic:predictive:seed=11',null_iterations=20,seed=11)
        b=study(data,source='synthetic:predictive:seed=11',null_iterations=20,seed=11)
        self.assertEqual(a,b)
        self.assertEqual(a['source_type'],'synthetic')
        self.assertIn('naive_touch',a['execution'])
        self.assertIn('conservative',a['execution'])
        self.assertEqual(a['signal']['test_start'],2400)
        self.assertEqual(a['predeclared_baselines']['no_prediction']['active_signals'],0)
        self.assertEqual(a['predeclared_baselines']['no_prediction']['mean_signed_ticks'],0.0)
        self.assertEqual(a['predeclared_baselines']['fixed_threshold']['threshold'],0.25)
        self.assertGreater(a['predeclared_baselines']['fixed_threshold']['test_signals'],0)

    def test_fixed_threshold_baseline_is_separate_from_fitted_signal(self):
        data=generate(4000,seed=11,predictive=True)
        result=study(data,source='synthetic:predictive:seed=11',null_iterations=0)
        baseline=result['predeclared_baselines']['fixed_threshold']
        fitted=screen(data,null_iterations=0)
        expected=_scores(data,fitted.horizon,fitted.test_start,len(data),0.25)
        self.assertNotEqual(fitted.threshold,0.25)
        self.assertEqual(baseline['test_signals'],len(expected))
        self.assertEqual(baseline['mean_signed_ticks'],round(mean(expected),6))
        self.assertEqual(baseline['threshold'],0.25)

    def test_cli_writes_valid_json_and_requires_no_api(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'report.json'
            main(['--synthetic-null','--rows','2000','--output',str(path)])
            data=json.loads(path.read_text())
            self.assertEqual(data['events'],2000)
            self.assertEqual(data['source_type'],'synthetic')
            self.assertTrue(data['evaluation']['test_probes']>0)

    def test_no_read_from_future_data_in_training(self):
        data=generate(4000,seed=12,predictive=False)
        baseline=study(data,source='synthetic:null',null_iterations=0)
        self.assertLess(baseline['signal']['train_end']+baseline['signal']['horizon'],len(data))
