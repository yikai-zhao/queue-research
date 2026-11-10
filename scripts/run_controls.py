#!/usr/bin/env python3
"""Fixed seed panel: expose null false positives and positive-control misses."""
import argparse
import json
from pathlib import Path
from queue_research.synthetic import generate
from queue_research.research import screen


def panel(seeds=range(10,22),count=4000,permutations=49):
    output=[]
    for seed in seeds:
        for injected in (False,True):
            result=screen(generate(count,seed,predictive=injected),
                          null_iterations=permutations,seed=seed)
            output.append({'seed':seed,'injected_predictability':injected,
                           'selected_threshold':result.threshold,
                           'test_events':result.test_samples,
                           'test_mean_signed_ticks':result.test_mean_signed_ticks,
                           'circular_shift_p_value':result.shifted_null_p_value,
                           'positive_direction':result.test_mean_signed_ticks is not None and result.test_mean_signed_ticks>0,
                           'passes_nominal_5pct':result.shifted_null_p_value is not None and result.shifted_null_p_value<=.05})
    null=[x for x in output if not x['injected_predictability']]
    injected=[x for x in output if x['injected_predictability']]
    return {'data':'synthetic controlled generator only','n_seeds':len(null),'events_per_run':count,
            'null_permutations':permutations,'null_nominal_5pct_false_positives':sum(x['passes_nominal_5pct'] for x in null),
            'positive_nominal_5pct_detected':sum(x['passes_nominal_5pct'] for x in injected),
            'negative_and_positive_controls':output,
            'warning':'Not an estimate of real-market detection power, actual alpha or a validated statistical test under dependence.'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=Path('lab-output/seed-panel.json'))
    p.add_argument('--seeds',type=int,nargs='+',default=list(range(10,22)))
    p.add_argument('--rows',type=int,default=4000)
    p.add_argument('--permutations',type=int,default=49)
    args=p.parse_args()
    if len(set(args.seeds))!=len(args.seeds):p.error('duplicate seeds')
    r=panel(args.seeds,args.rows,args.permutations)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='negative_and_positive_controls'},indent=2))
if __name__=='__main__':main()
