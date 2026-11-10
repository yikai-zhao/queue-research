# Walk-forward evaluation (within one tape)

**Question.** Does the predeclared order-book imbalance screen behave similarly
when it is re-fitted on expanding history and evaluated in later, non-overlapping
blocks, rather than relying on a single arbitrary 60/40 split?

The optional companion diagnostic now runs in every `study()` report:

- Four chronological test blocks (60% of the tape, split into four 15% blocks)
  after a 40% initial training block.
- Threshold selection (same four predeclared thresholds) uses only labels that
  fully mature before each block's start.
- Test signals are spaced `horizon+1` events apart, and every test label must
  finish inside its block and the same continuous trading segment.
- Expanding history is re-fit before every later block; earlier test blocks may
  become later training data. This is **not** a second held-out final test.
- The report retains the selected threshold, training sample count, test count,
  per-fold signed midpoint markouts, and explicit empty/insufficient cases.

## Controlled demonstration

Reproduce using the bundled synthetic controls:

```bash
PYTHONPATH=src python -m queue_research --synthetic-null --seed 11 \
  --output lab-output/walkforward-null.json
PYTHONPATH=src python -m queue_research --synthetic-predictive --seed 11 \
  --output lab-output/walkforward-predictive.json
PYTHONPATH=src:. python -m unittest discover -s tests -p test_walkforward.py -v
```

For the 16,000-event `seed=11` synthetic examples, the pooled non-overlapping
signed markout was **+0.0273 ticks (null)** vs **+0.1711 ticks (injected
predictive relationship)**; 220 vs 187 test signals. The null was also
positive. Do not interpret the difference as calibrated prediction accuracy,
market PnL, or a formal significance test.

**Hard limits.** Within-tape folds share the same observed market and regime;
they are not statistically independent days, instruments, or venues. Event
indices are not physical time. A real multi-session out-of-day evaluation,
transaction cost model, and execution model calibration remain necessary
before any generalizable trading claim. A single-day free LOBSTER example
cannot close that evidence gap.
