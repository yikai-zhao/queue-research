# Validation and evidence boundaries

- Python 3.11+ standard library only, no network or remote actions.
- 55 deterministic tests: CSV/ZIP schema, strict row alignment, nanosecond precision, invalid quote/time/order rejection, auction exclusion; conservative/optimistic queue bounds, partial fill, quote departure, *final execution that changes the quote*, stale quote after latency, fee arithmetic, and session-halt purging; train-only fitting and test isolation; seeded negative/positive controls and deterministic CLI outputs.
- Fixed 12-seed controlled panel: 12 null + 12 injected-positive simulated sequences, 4,000 events each, 49 circular shifts per test. **0/12 nominal null positives and 8/12 nominal positive detections.** Counts describe this constructed panel only, not market significance/predictive accuracy.
- Input LOBSTER samples: **not acquired in the runtime**. Actual replay results must be produced before résumé claims involving NASDAQ historical price predictability, exchange fill calibration or strategy monetization.
- No GitHub Actions workflows, paid services or authenticated exchange APIs.

Run:

```
PYTHONPATH=src:. python -m unittest discover -s tests -v
PYTHONPATH=src:. python scripts/run_controls.py --output lab-output/seed-panel.json
```

Raw synthetic panel: `evidence/seed-panel.json` (generated with source-controlled code and documented seeds). All null and positive cases, including missed positives, remain in evidence instead of being discarded. The intended result is a **falsifiable research workflow**, not a guaranteed strong Alpha.

## 2026-11-09 robustness milestone

- Added explicit `ineligible_session_boundary` outcomes: an order filled before a halt is **not** marked to the post-halt midprice, and invalid experiments do not enter eligible fill denominators.
- All retained event-time label windows within an individual `h+1` phase are disjoint. We show all phases, their sample sizes and sign variability. Other phases reuse observations and cannot be combined into an independent significance test.
- Execution sensitivity uses exactly the frozen holdout signals and predeclared event latencies 1/2/5 (subject to `latency < horizon`) and hypothetical 0/1/3 bps fees. No best fee or latency is picked from test outcomes.
- Circular shift diagnostics are **not produced** if the holdout crosses a halt/auction: no surrogate p-value from rotations between distinct trading segments.
- Added 13 adversarial and metamorphic tests for these invariants. That revision passed **55/55** tests; the later 2026-11-10 audit is described below. This is algorithm correctness evidence, not real-data accuracy or profit evidence.
- The legacy synthetic seed panel was rerun unchanged: **0/12** nominal null rejections, **8/12** nominal injected-positive detections, still not a calibrated test of finance hypotheses.

## 2026-11-10 execution and evidence consistency audit

- Before fix: three same-event fill/markout counterexample assertions failed;
  corrected the scan to require `activation < fill < markout`.
- Re-generated both seeded 16,000-event examples and robustness aggregate with
  the current execution and walk-forward implementation; the prior committed
  examples were stale and displayed earlier fill percentages.
- Added full-report reproducibility tests and a manifest over all current
  source/tests/docs/evidence files (excluding the manifest itself).
- Re-ran the 12-seed controlled panel unchanged: 0/12 nominal null detections
  and 8/12 injected-positive detections. These are synthetic outcomes only.
- Audited local targeted/clean unit suite: **66/66 passed** on 2026-11-10.
  No empirical real-market or execution-capacity claim follows from this.
