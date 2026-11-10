# Methodology and anti-leakage invariants

## Study question

A limit-order-book state can be predictive without granting us the execution price. This project measures two *separate* quantities:

1. **Midprice predictability:** can the current displayed best-level quantity imbalance predict a future midprice move?
2. **Execution sensitivity:** how do assumptions about queue ahead, cancellations, latency and fees change *hypothetical* passive fills and subsequent midprice markouts?

Combining the two is diagnostic. It does **not** produce a risk-managed strategy PnL.

## Input semantics

LOBSTER event row k changes order book row k-1 into row k. Every row of the orderbook CSV is a **post-event snapshot**. Prices are integers in units of USD × 10,000; the research module's tick is 100 raw units (one cent). Quantity is shares. Event side +1 means **resting buy**, -1 **resting sell**, including visible executions. Halt and auction messages are not used for continuous-book signals; crossing them increments a session segment, so forward labels and hypothetical fills cannot bridge the discontinuity. The adapter reads the first best bid/ask even when a ZIP contains more levels; do not advertise it as a multi-level model.

## Predictive signal

Displayed best-level imbalance: `I[t] = (bid_size[t] - ask_size[t]) / (bid_size[t] + ask_size[t])`.

Decision `s[t] = 1` if `I[t] >= threshold`, `-1` if `I[t] <= -threshold`, otherwise no decision. The research label at t is `s[t] * (mid[t+h] - mid[t]) / 100` **ticks**, evaluated only once event `t+h` has occurred.

- Predeclared threshold candidates: 0.15, 0.25, 0.35, 0.45.
- First 60% of input events train. Every training label **must mature before** the test boundary; a horizon-sized tail at the boundary is unused. Remaining 40% held out chronologically.
- Choose highest mean signed TRAIN forward tick move among candidates with at least 20 train signals. Compare on TEST without refitting.
- Report train/test sample counts, train/test mean signed ticks, fraction strictly positive, and 100 random circular-shift surrogate means when enough offset room exists and the holdout stays within one continuous trading segment. Circular shifts preserve local feature autocorrelation but may not preserve all time-series dependence or seasonality; the resulting empirical tail probability is a **sensitivity diagnostic**, not proof of statistical significance.
- Many event labels overlap in time. This is *not* 10,000 independent trials. A single intraday time split on the LOBSTER free sample cannot validate a stable live-market edge.

## Passive order counterfactuals

At event t, the order's limit price is fixed at the **observed quote at t**: buy at bid, sell at ask. No look-ahead repricing. Activate at `t + latency_events`, where the default is 2 **events**, not microseconds. If the best price on activation is no longer equal to the intended price, the conservative exercise records **no fill**, rather than retroactively choosing a different price.

- `naive_touch`: fictitious immediate complete fill at the activation best, provided price is unchanged. Included only to quantify optimistic backtest assumptions.
- `conservative`: assumed queue ahead equals displayed best-level size when the order becomes active; only **visible executions** of same resting side at our price consume the queue ahead. Cancels do not advance our queue position.
- `cancel_ahead`: optimistic bound: all same-price cancellation/deletion size occurs ahead of us. Exact cancellation position is NOT observable from L2 data.

Visible execution of the **final resting order** is processed before looking at the post-event changed best quote; the sequence matters. Partial fills are supported, with share-weighted summary. A quote moving away without a qualifying trade causes expiry; never assign a free fill on mere touch. Other crossing/hidden-order/impact/mid-spread behaviours are deliberately not modeled.

If the signal-to-horizon period crosses a halt/auction, the entire hypothetical order is labeled `ineligible_session_boundary`. A fill before the halt is **not** marked to an unrelated post-halt midprice or silently categorized as an ordinary unfilled order. Denominators disclose both all probes and eligible probes.

At fixed t+h, a filled share's markout is `side * (mid[t+h] - placed_limit) / 100 - fee_bps * placed_limit / 1,000,000`. Default 1 bp is a **hypothetical flat cost**, not an actual Nasdaq/Tower fee schedule. These are **fill-conditional** markouts; unfilled orders do not get fabricated PnL. The test-only order probes are spaced h+1 events apart, but consecutive market observations remain serially correlated.

## Critical omissions

- No known order-level market-by-order queue snapshot, so FIFO ahead is **modeled** and can be wrong.
- No own-order impact, queue replenishment attribution, reject/cancel latency, modification precedence, volume-impact calibration or exchange-specific rules.
- Fixed event-count horizon and latency do not approximate wall-clock nanoseconds, execution gateway latency or market access.
- No multi-day walk-forward, fee/rebate schedule calibration, multiple-testing correction, inventory, hedging or capacity limits.
- No significant Sharpe, live strategy, production HFT or realistic profit claims.

The next justified milestone is actual LOBSTER free-sample ingestion, sanity plots of event distribution/depth regimes, and **multi-session licensed data** before robust finance claims. A further legitimate development would be an event-time fill model calibrated to observed executions and cancellation rates, **without claiming exact FIFO position**.

## Additional integrity diagnostics (predeclared, descriptive)

- **Holdout phase sensitivity:** use 31 different phase offsets for horizon 30. Within each phase, labels are spaced `h+1` events so their forward windows do not overlap. Compare phase means, sample counts and how many are positive. The phases still share the same market tape: 31 positive phases is not 31 independent replications.
- **Execution sensitivity:** hold the exact same test-only, spaced directional probes fixed and vary event latency 1/2/5 and hypothetical fees 0/1/3 bps. Record every queue model under all settings, do not pick the best output after the fact. This does not fit exchange fees or physical message latency.
- **Halt handling:** no cross-segment forward price markout, no fill assumption across a halt. Do not calculate circular-shift diagnostics by rotating features between two market segments.

See [`RESEARCH_INTEGRITY.md`](RESEARCH_INTEGRITY.md) for controlled outcomes and exclusions.
