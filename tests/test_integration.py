import json
import tempfile
from pathlib import Path
import unittest
from queue_research.synthetic import generate
from queue_research.experiment import study, main


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
