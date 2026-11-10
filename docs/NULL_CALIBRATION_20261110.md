# Synthetic false-discovery calibration of the imbalance screen (2026-11-10)

**Question:** Is `screen()`'s exploratory circular-feature-shift p-value a trustworthy 5% significance test under an explicitly known no-predictive-signal generator?

## Predeclared experiment

Using the unchanged `src/queue_research/research.py` signal screen and synthetic generator, run seeds **0–199** independently for each of two generator conditions. Each run contains 4,000 order-book events, a 60% training split, four fixed imbalance thresholds (0.15/0.25/0.35/0.45), 30-event markout and **99** circular-shift surrogates per test. Surrogate RNG seed is `seed+4141`. No test data selects a threshold. Report both null cases (features do not predict forward price move by construction) and deliberately injected positive cases.

| Generator | Nominal p <= 0.05 | Fraction | Wilson 95% CI | Mean held-out signed ticks |
|---|---:|---:|---:|---:|
| Known null | **16/200** | **8%** | [4.984%, 12.599%] | -0.00594 |
| Injected dependence | **170/200** | **85%** | [79.394%, 89.286%] | +0.23275 |

This is a **calibration warning**, not proof that true market false-positive probability is 8%. The interval for the null nearly includes the nominal 5% rate, and these are synthetic RNG instances from a fixed stylized process, not 200 independent stock-days or production incidents. The 85% is **detection of an artificial relationship**, never a win rate or real-world strategy accuracy.

These observations support keeping the shift result labeled **exploratory**, not `statistically significant alpha`. The research flow still needs independent *multi-date market samples*, explicit multiple-hypothesis handling and a truly deployable fill/cost model before any actual performance claim.

## Reproduce

```bash
PYTHONPATH=src python scripts/audit_null_calibration.py --seeds 200 --events 4000 \
  --shifts 99 --output lab-output/calibration-200-seeds.json
PYTHONPATH=src:. python -m unittest discover -s tests -v
sha256sum src/queue_research/research.py src/queue_research/synthetic.py
```

The compact command's JSON output saves all 400 seed-level decisions and the SHA-256 values of the **actual analysis and generator source**. The **compact committed summary** is `evidence/null-calibration-200-seeds-summary.json`, which retains per-condition counts, configuration, code hashes and a SHA-256 of the full 400-decision JSON. The full JSON is retained in the accompanying downloadable audit archive; run the command to independently regenerate it. No capital, exchange connection, cloud API, paid market data, or GitHub Actions are used. This is a result about **research-test reliability**, not market trading profitability.
