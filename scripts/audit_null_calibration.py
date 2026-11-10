"""Predeclared synthetic null/predictive calibration of the CURRENT screen().

No market-data or profitability claims. Tracks *false discoveries* of the
single-tape shifted-feature exploratory diagnostic, not independent days.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import mean
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from queue_research.research import screen
from queue_research.synthetic import generate


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    if n < 1 or not 0 <= k <= n:
        raise ValueError('invalid Wilson interval counts')
    p = k / n
    d = 1 + z*z/n
    center = (p + z*z/(2*n))/d
    radius = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [round(center-radius, 6), round(center+radius, 6)]


def evaluate(seeds: int = 250, events: int = 4000, shifts: int = 99) -> dict:
    if not 1 <= seeds <= 1000 or not 1000 <= events <= 200000 or not 0 <= shifts <= 1000:
        raise ValueError('invalid experiment configuration')
    out = []
    for predictive in (False, True):
        cases = []
        for seed in range(seeds):
            result = screen(generate(events, seed, predictive), horizon=30,
                            thresholds=(.15,.25,.35,.45),
                            train_fraction=.6, null_iterations=shifts,
                            seed=seed+4141)
            cases.append({'seed':seed, 'test_avg_signed_ticks':result.test_mean_signed_ticks,
                          'test_signals':result.test_samples,
                          'selected_threshold':result.threshold,
                          'shift_p_value':result.shifted_null_p_value,
                          'null_status':result.null_diagnostic_status})
        tests = [x for x in cases if x['shift_p_value'] is not None]
        sig = sum(x['shift_p_value'] <= .05 for x in tests)
        positive = sum(x['test_avg_signed_ticks'] > 0 for x in cases if x['test_avg_signed_ticks'] is not None)
        out.append({'name':'injected_predictive' if predictive else 'null_no_predictive_relation',
                    'seeds':[0,seeds-1], 'tests_evaluated':len(tests),
                    'p_le_0_05':sig, 'p_le_0_05_fraction':round(sig/len(tests),6) if tests else None,
                    'wilson_95_fraction':wilson(sig,len(tests)) if tests else None,
                    'mean_test_signed_ticks':round(mean(x['test_avg_signed_ticks'] for x in cases
                                                         if x['test_avg_signed_ticks'] is not None),8),
                    'positive_holdout_mean':positive,'cases':cases})
    return {'scope':'SYNTHETIC method calibration only; not real alpha',
            'configuration':{'seed_range':[0,seeds-1], 'events_per_seed':events,
                             'null_offsets_per_seed':shifts, 'horizon_events':30,
                             'train_fraction':.6,'thresholds':[.15,.25,.35,.45],
                             'nominal_alpha':.05,'null_random_seed_offset':4141},
            'source_sha256':{
                p:sha256((ROOT/p).read_bytes()).hexdigest() for p in
                ('src/queue_research/research.py','src/queue_research/synthetic.py')},
            'results':out,
            'limitations':['Synthetic regimes reuse a fixed simple generator; test seeds are independent RNG streams, not independent market days.',
                           'P-value is a single-path feature circular-shift diagnostic, with no calibrated guarantee under exchange dynamics or multiple hypotheses.',
                           'A significant synthetic null case is a false positive relative to the known data-generating process, not a financial trade.',
                           'Wilson intervals describe binomial seed-to-seed occurrence, not actual market confidence or strategy Sharpe.']}


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--seeds',type=int,default=250)
    p.add_argument('--events',type=int,default=4000)
    p.add_argument('--shifts',type=int,default=99)
    p.add_argument('--output',type=Path,default=Path('lab-output/null-calibration.json'))
    a=p.parse_args()
    report=evaluate(a.seeds,a.events,a.shifts)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    for x in report['results']:
        print(x['name'],x['p_le_0_05'],'/',x['tests_evaluated'],
              '95% Wilson',x['wilson_95_fraction'],
              'mean signed ticks',x['mean_test_signed_ticks'])
    print('report:',a.output)
    return 0

if __name__=='__main__':raise SystemExit(main())
