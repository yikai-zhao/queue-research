# Quant research integrity: what was actually repaired

**Question:** when we measure a directional signal, how fragile are the result and assumed executions? This is a methodological audit, **not** a new trading strategy.

## Two error modes

1. **Cross-session markout leakage (corrected):** a resting order can receive a visible fill before a halt, yet the fixed-horizon price can be from *after* the halt. Such a markout is not a valid continuous-market outcome. The probe now returns `ineligible_session_boundary`, does not register a fill and does not contribute to eligible-fill denominators. A targeted test reproduces this case.
2. **Circular null across regime boundaries (corrected):** circularly rotating imbalance observations from after a halt into a prior session falsely treats separate segments as stationary. The exploratory circular-shift diagnostic now returns `None` and status `disabled_multiple_segments` in this case.

## Robustness checks

- Holdout metrics remain chronological with label purging. A second diagnostic uses every offset in `[0, h]`, spacing observations by `h+1` events **within each offset**. Report all phase means and sample counts; do **not** treat correlated phase offsets as 31 independent tests or confidence limits.
- The execution comparison uses fixed, **previously selected** signals from the test period. It reports all 3 event-latency assumptions (1/2/5) times all 3 illustrative fee assumptions (0/1/3 bps), for each queue model. **No search for the best test result.** For horizons <=5, remove predeclared latencies that would exceed the horizon, and report the actual grid.
- Full-queue versus cancellation-ahead versus instant-touch comparisons remain explicitly counterfactual: the real order position, own market impact and true queue priority are not observed from level-one depth.

## Observed on synthetic seed 11, 16,000 events (NOT real NASDAQ data)

| Quantity | Known-null generator | Deliberately predictive generator |
|---|---:|---:|
| OOS mean signed forward markout | +0.0175 ticks | +0.1772 ticks |
| Exploratory circular-shift tail probability | 0.3663 | 0.0099 |
| Non-overlapping phases with positive average | 21/31 | 31/31 |
| Conservative fill share fraction, 2-event delay, 1 bp | 17.2% | 14.2% |
| Optimistic cancellation-ahead fill fraction | 34.1% | 30.8% |
| Deliberately naive instant-touch fill fraction | 98.8% | 96.5% |

The generator deliberately creates a correlation between current displayed depth imbalance and later midprice changes in one group, and not in the null group. These results validate code behavior only. All numbers are from an artificial tape, not a strategy backtest. One-day historical LOBSTER samples (if separately supplied) are still insufficient for reliable multi-day out-of-sample performance claims.

## Reproduce

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -v
PYTHONPATH=src python -m queue_research --synthetic-null --rows 16000 --seed 11 --output lab-output/null.json
PYTHONPATH=src python -m queue_research --synthetic-predictive --rows 16000 --seed 11 --output lab-output/predictive.json
PYTHONPATH=src:. python scripts/run_controls.py --output lab-output/seed-panel.json
```

Any claimed performance improvements or true market alpha must be supported later by a licensed real market tape, multiple independent dates, predeclared evaluation, costs and a meaningful execution/calibration model. None is claimed here.
