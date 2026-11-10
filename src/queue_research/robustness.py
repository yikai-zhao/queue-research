"""Predeclared holdout and execution sensitivity diagnostics (not new strategies).

Phase summaries use h+1 event spacing to avoid overlapping *label windows*
within each phase. Different phases reuse the same tape and are NOT
independent confirmations or confidence intervals.
"""
from __future__ import annotations

from statistics import mean, median
from .data import BookEvent
from .execution import comparison
from .research import Decision, side


def phase_sensitivity(rows: list[BookEvent], decision: Decision) -> dict:
    """Inspect sensitivity to the arbitrary phase of non-overlap sampling."""
    h = decision.horizon
    start, end = decision.test_start, len(rows) - h
    phases = []
    if end <= start:
        return {'phases_evaluated': 0, 'warning': 'no eligible holdout horizon'}
    stride = h + 1
    for offset in range(min(stride, end - start)):
        signed = []
        for i in range(start + offset, end, stride):
            if rows[i].segment != rows[i + h].segment:
                continue
            d = side(rows[i].imbalance, decision.threshold)
            if d:
                signed.append(d * (rows[i + h].mid - rows[i].mid) / 100)
        phases.append({'offset': offset, 'signals': len(signed),
                       'mean_signed_ticks': round(mean(signed), 6) if signed else None,
                       'positive_fraction': round(sum(x > 0 for x in signed) / len(signed), 6)
                       if signed else None})
    informative = [x for x in phases if x['mean_signed_ticks'] is not None]
    if not informative:
        return {'phases_evaluated': len(phases), 'phases_with_signals': 0,
                'phases': phases, 'warning': 'no non-overlapping directional signals'}
    means = sorted(x['mean_signed_ticks'] for x in informative)
    return {'phases_evaluated': len(phases),
            'phases_with_signals': len(informative),
            'positive_mean_phases': sum(x['mean_signed_ticks'] > 0 for x in informative),
            'signals_min_per_phase': min(x['signals'] for x in informative),
            'signals_median_per_phase': median(x['signals'] for x in informative),
            'mean_signed_ticks_min': means[0],
            'mean_signed_ticks_median': median(means),
            'mean_signed_ticks_max': means[-1],
            'phases': phases,
            'interpretation': 'Overlapping phases share the same tape and are not independent; no p-value or CI.'}


def execution_sensitivity(rows: list[BookEvent], signals: list[tuple[int, int]], *,
                          horizon: int, latencies: tuple[int, ...] = (1, 2, 5),
                          fees_bps: tuple[float, ...] = (0.0, 1.0, 3.0),
                          quantity: int = 10) -> dict:
    """Freeze the signal decisions; vary execution assumptions only.

    This grid is not optimized against the holdout and does not select the
    best-performing configuration. It reports all predeclared combinations.
    """
    if (not latencies or len(set(latencies)) != len(latencies) or
            any(type(x) is not int or x < 1 or x >= horizon for x in latencies)):
        raise ValueError('invalid predeclared event latency grid')
    if (not fees_bps or len(set(fees_bps)) != len(fees_bps) or
            any(type(x) not in (int, float) or not -5 <= x <= 100 for x in fees_bps)):
        raise ValueError('invalid fee grid')
    runs = []
    for latency in latencies:
        for fee in fees_bps:
            results = comparison(rows, signals, latency_events=latency,
                                 horizon_events=horizon, quantity=quantity, fee_bps=fee)
            # Same market events and same signal decisions across every cell.
            # Event latency is NOT wall-clock latency; fee is illustrative.
            runs.append({'latency_events': latency, 'fee_bps_per_filled_share': fee,
                         'models': results})
    return {'hypothetical_signals': len(signals),
            'predeclared_latencies_events': list(latencies),
            'predeclared_fees_bps': list(fees_bps),
            'grid': runs,
            'interpretation': 'Fixed signals; no tuning against test, no realistic exchange fee claim.'}
