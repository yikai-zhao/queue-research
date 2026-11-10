"""One-command, read-only microstructure investigation and execution sensitivity."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import zipfile
from pathlib import Path
from statistics import mean
from .data import from_lobster_zip
from .execution import comparison
from .research import screen, side
from .robustness import phase_sensitivity, execution_sensitivity
from .synthetic import generate
from .walkforward import expanding_folds


def study(rows, *, source, source_hash=None, horizon=30, latency=2,
          fee_bps=1, null_iterations=100, seed=2026):
    fitted = screen(rows,horizon=horizon,null_iterations=null_iterations,seed=seed)
    # Strictly TEST-only execution probes. Spaced beyond their horizon to avoid
    # turning overlapping hypothetical orders into fake independent trades.
    probes = [(i,side(rows[i].imbalance,fitted.threshold))
              for i in range(fitted.test_start,len(rows)-horizon,horizon+1)]
    probes = [(i,direction) for i,direction in probes if direction]
    actions = comparison(rows,probes,latency_events=latency,
                         horizon_events=horizon,fee_bps=fee_bps)
    trade_events = [r for r in rows if r.kind == 4]
    book_events = [r for r in rows if r.kind in (1,2,3,4)]
    return {
        'source': source, 'sha256': source_hash, 'source_type': 'synthetic' if source.startswith('synthetic:') else 'historical_lobster_sample',
        'events': len(rows), 'orderbook_event_kind_counts': {str(k):sum(r.kind==k for r in rows) for k in (1,2,3,4,5)},
        'visible_execution_event_fraction': round(len(trade_events)/len(book_events), 6) if book_events else None,
        'signal': asdict(fitted), 'execution': actions,
        'holdout_phase_sensitivity': phase_sensitivity(rows, fitted),
        'expanding_walkforward': expanding_folds(rows, horizon=horizon),
        'execution_assumption_sensitivity': execution_sensitivity(
            rows, probes, horizon=horizon,
            latencies=tuple(x for x in (1, 2, 5) if x < horizon)),
        'evaluation': {'chronological_train_fraction':0.6,'purge':'train labels must mature inside train period',
                       'test_probes':len(probes),'max_overlapping_probe_horizons':0,
                       'fees_bps_per_filled_unit':fee_bps,
                       'queue_models':'naive touch is intentionally unrealistic; conservative ignores cancels; cancel-ahead assumes all cancels ahead'},
        'limitations':[
            'No market impact, risk limits, latency measured in events rather than nanoseconds, exchange-specific fee schedule, or production-calibrated execution.',
            'LOBSTER free sample is historical and one day only: time split is not an out-of-day validation.',
            'Visible executions have order-side direction, not aggressor side.',
            'Displayed market-by-price depth cannot reveal exact FIFO position; cancellation ahead is uncertain.',
            'Hypothetical orders are independent counterfactuals; conditional markouts are not a tradable strategy PnL or Sharpe.',
            'Synthetic demonstrations are controlled unit evidence only, never evidence of financial alpha.',
            'Circular-shift null is disabled for holdout segments spanning halts/auctions; elsewhere it remains exploratory and not a rigorous significance guarantee.',
            'Non-overlapping label phases are correlated views of one tape, not independent trials, p-values or confidence intervals.',
            'Execution sensitivity uses fixed test signals for descriptive diagnostics only; no test-set configuration optimization.',
            'Expanding walk-forward folds are within one tape; they are not independent trading days and do not establish a statistically significant alpha.'
        ]
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--lobster-zip',type=Path)
    group.add_argument('--synthetic-null',action='store_true')
    group.add_argument('--synthetic-predictive',action='store_true')
    parser.add_argument('--rows',type=int,default=16000, help='synthetic event count')
    parser.add_argument('--max-historical-events', type=int, help='optional cap for LOBSTER processing; default all')
    parser.add_argument('--seed',type=int,default=17)
    parser.add_argument('--horizon',type=int,default=30)
    parser.add_argument('--fee-bps',type=float,default=1)
    parser.add_argument('--latency-events',type=int,default=2)
    parser.add_argument('--output',type=Path,default=Path('lab-output/research.json'))
    args=parser.parse_args(argv)
    try:
        if args.lobster_zip:
            source=f'LOBSTER sample: {args.lobster_zip.name}'
            source_hash=sha256(args.lobster_zip.read_bytes()).hexdigest()
            rows=from_lobster_zip(args.lobster_zip, limit=args.max_historical_events)
        else:
            positive=args.synthetic_predictive
            source=f'synthetic:{"predictive" if positive else "null"}:seed={args.seed}'
            source_hash=None
            rows=generate(args.rows,args.seed,predictive=positive)
        result=study(rows,source=source,source_hash=source_hash,horizon=args.horizon,
                     latency=args.latency_events,fee_bps=args.fee_bps,seed=args.seed)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(json.dumps({'output':str(args.output),'source':source,'signal':result['signal'],
                          'execution':result['execution']},indent=2,allow_nan=False))
    except (ValueError,OSError,KeyError,zipfile.BadZipFile,UnicodeError) as exc:
        parser.error(str(exc))

if __name__=='__main__':main()
