# Queue Research

**Order-book imbalance research meets execution reality.** A small, dependency-free Python lab that asks two related questions: Does a best-level order-book imbalance signal survive a chronological holdout? And if it does, would a passive order actually fill under defensible queue assumptions?

Built for investigating **market microstructure, analytical signals, and exchange-simulation assumptions**. It is not a portfolio backtester, a production exchange simulator, or evidence of a profitable strategy.

## What is implemented

- **Historical sample adapter:** accepts a user-downloaded LOBSTER message/orderbook ZIP, matches every event to its **post-event** best quote, uses exact integer price units and nanosecond timestamps, rejects malformed/crossed books, and excludes auction/halt events.
- **Research:** best-level **displayed depth imbalance** (not Cont–Kukanov–Stoikov's order-flow imbalance), four predefined thresholds fitted only on the first 60% of events, purged forward labels, chronological 40% holdout, signed forward midprice markouts, and a cautious circular-shift null diagnostic (disabled if the holdout spans halts/auctions).
- **Execution:** makes an order decision using the quote **available at signal time** and activates it only after a stated event latency; compares intentionally naive instant-touch fills with a conservative trade-only FIFO-ahead estimate and an optimistic cancellation-ahead estimate. Tracks partial fills, fee-adjusted conditional markouts, missed fills, quote departure, and execution of the final displayed level.
- **Research integrity:** 12 fixed null/positive seed pairs; non-overlapping holdout-window phase sensitivity; a predeclared 3×3 latency/fee execution grid; explicit exclusion of sessions crossing an auction or halt. Unit and negative-case tests are executable without any private data.

## Reproduce (Python 3.11+, no dependencies or paid infrastructure)

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -v

# Known-null and deliberately predictive *synthetic* demonstrations
PYTHONPATH=src python -m queue_research --synthetic-null \
  --rows 16000 --seed 11 --output lab-output/null.json
PYTHONPATH=src python -m queue_research --synthetic-predictive \
  --rows 16000 --seed 11 --output lab-output/predictive.json

# Multi-seed controls: do not cherry-pick a successful random seed
PYTHONPATH=src:. python scripts/run_controls.py \
  --output lab-output/seed-panel.json

# **Real NASDAQ historical sample**, downloaded independently from LOBSTER
PYTHONPATH=src python -m queue_research \
  --lobster-zip /path/to/LOBSTER_SampleFile_AAPL_2012-06-21_1.zip \
  --output lab-output/aapl_2012-06-21.json
```

LOBSTER provides free AAPL/AMZN/MSFT etc. sample ZIPs at [its sample page](https://php.lobsterdata.com/info/DataSamples.php), with [official event and post-event book definitions](https://php.lobsterdata.com/info/DataStructure.php). **You download and run the real sample yourself**; the repository does not redistribute market data. As of this revision the real archive was **not available to the development environment**, so no result in this repository is falsely described as tested on real AAPL data. Only its official schema has been exercised through generated ZIP fixtures.

## Controlled findings (synthetic data only)

Using 12 predefined seeds, 4,000 generated events per seed and 49 circular shifts per holdout:

| Condition | Nominal p ≤ 0.05 detections | Interpretation |
|---|---:|---|
| **Null:** displayed imbalance does not control the next quote move | **0 / 12** | The null panel did not flag a result in this controlled panel |
| **Positive control:** deliberately injected dependence | **8 / 12** | The screen found a known signal in some, but **missed four** scenarios |

This is **not** a real-market alpha hit rate, a general false-positive guarantee, calibrated market impact, or a formal p-value under a proven null model. Per-seed outputs are committed at [`evidence/seed-panel.json`](evidence/seed-panel.json). Single-seed results can differ substantially.

The new integrity checks found no new market alpha: on the same 16,000-event **synthetic** positive control, 31/31 non-overlapping label phases had a positive mean, while the seeded **null** had 21/31 positive phases (an example of noisy apparent consistency). Phases share one underlying tape and are **not** independent observations. Queue-model sensitivity is reported at fixed signals for event latency 1/2/5 and hypothetical fees 0/1/3 bps; no parameter is chosen from the held-out outcomes. Sessions crossing a halt/auction are excluded from fill metrics, and circular-shift diagnostics abstain across multiple segments. [Full research-integrity rationale](docs/RESEARCH_INTEGRITY.md).

## Interpretation and limitations

A signal can predict a midprice change while still yielding **zero passive fills**. The naive-touch model deliberately assumes all eligible orders fill immediately; it is a comparison bound, not a viable execution strategy. Market-by-price (L2) data does not reveal the exact FIFO queue ahead of a new order, and a historical replay cannot model the market impact of adding our order. It reports **hypothetical order-level, fill-conditional markouts**, never compounded PnL, Sharpe or claimed HFT profitability. Event-count latency is not physical microseconds.

See [Methodology and invariants](docs/METHODOLOGY.md), [Data provenance and required real-data milestone](docs/DATA.md), [Evidence and regression status](docs/VALIDATION.md).

## Related work

- [LOBSTER official samples and schema](https://php.lobsterdata.com/info/DataSamples.php) — actual market data source and fixed-point convention.
- [HftBacktest queue-model limitations](https://hftbacktest.readthedocs.io/en/latest/order_fill.html) — motivation for treating queue positions and replay fills cautiously.
- [Cont, Kukanov, Stoikov, *The Price Impact of Order Book Events* (2014)](https://www.sashastoikov.com/finance/2015/3/12/the-price-impact-of-order-book-events) — an important **OFI** reference; OFI is *not* the displayed-depth imbalance implemented here.

No exchange connection, investment advice, employer/customer data, cloud compute or GitHub Actions. MIT licensed source; external datasets retain their own terms.
