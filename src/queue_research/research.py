"""Out-of-sample order-book imbalance screening; no fitting on the test period."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from random import Random
from statistics import mean, median
from .data import BookEvent


@dataclass(frozen=True)
class Decision:
    threshold: float
    horizon: int
    train_end: int
    test_start: int
    train_samples: int
    test_samples: int
    train_mean_signed_ticks: float
    test_mean_signed_ticks: float | None
    test_positive_fraction: float | None
    shifted_null_p_value: float | None
    null_iterations: int
    null_diagnostic_status: str


def side(imbalance: float, threshold: float) -> int:
    return 1 if imbalance >= threshold else (-1 if imbalance <= -threshold else 0)


def _scores(rows: list[BookEvent], horizon: int, start: int, end: int,
            threshold: float, feature_shift: int = 0) -> list[float]:
    result = []
    # Only labels that mature inside the chosen period. Prediction uses book i,
    # never the book at i+1. Shift null preserves feature autocorrelation.
    n = end - start - horizon
    for k in range(max(n, 0)):
        i = start + k
        if rows[i+horizon].segment != rows[i].segment:
            continue  # no labels across auctions, halts or session discontinuities
        feature_i = start + ((k + feature_shift) % n) if feature_shift and n else i
        direction = side(rows[feature_i].imbalance, threshold)
        if direction:
            result.append(direction * (rows[i+horizon].mid - rows[i].mid) / 100)
    return result


def screen(rows: list[BookEvent], horizon: int = 30,
           thresholds: tuple[float, ...] = (0.15, 0.25, 0.35, 0.45),
           train_fraction: float = 0.6, null_iterations: int = 100, seed: int = 2026) -> Decision:
    if not (0 < train_fraction < 1) or not (5 <= horizon < len(rows)//5):
        raise ValueError('invalid horizon/split')
    if null_iterations < 0 or null_iterations > 1000:
        raise ValueError('invalid null iterations')
    if not thresholds or any(t <= 0 or t > 1 or not isfinite(t) for t in thresholds):
        raise ValueError('thresholds must be in (0,1]')
    cut = int(len(rows) * train_fraction)
    if cut <= 2*horizon or len(rows)-cut <= 2*horizon:
        raise ValueError('not enough observations on either side of split')
    # Training labels always mature strictly before the split. Test starts at
    # cut; no future test prices can leak into threshold selection.
    fitted = []
    for t in thresholds:
        values = _scores(rows, horizon, 0, cut, t)
        fitted.append((mean(values) if len(values) >= 20 else float('-inf'), len(values), t))
    best_score, n_train, chosen = max(fitted, key=lambda x: (x[0], -x[2]))
    if n_train < 20:
        raise ValueError('insufficient train signals for predeclared threshold grid')
    test = _scores(rows, horizon, cut, len(rows), chosen)
    test_avg = mean(test) if test else None
    null_p = None
    null_status = ('not_requested' if not null_iterations else
                   'no_test_signals' if not test else 'insufficient_shift_offsets')
    # Circularly shifting features across a halt/auction would stitch distinct
    # market regimes into a fictitious stationary sequence. It is preferable
    # to abstain from this diagnostic, not print a misleading p-value.
    segments = {r.segment for r in rows[cut:]}
    if test and null_iterations and len(segments) > 1:
        null_status = 'disabled_multiple_segments'
    elif test and null_iterations:
        n = len(rows) - cut - horizon
        rng = Random(seed)
        # Non-trivial circular shifts: at least horizon apart from alignment.
        offsets = [x for x in range(horizon+1, n-horizon)]
        if offsets:
            exceed = 0
            for _ in range(null_iterations):
                shift = rng.choice(offsets)
                surrogate = _scores(rows, horizon, cut, len(rows), chosen, shift)
                if surrogate and mean(surrogate) >= test_avg:
                    exceed += 1
            null_p = (1 + exceed)/(null_iterations+1)
            null_status = 'exploratory_single_segment_circular_shift'
    return Decision(chosen, horizon, cut, cut, n_train, len(test),
                    best_score, test_avg,
                    sum(x>0 for x in test)/len(test) if test else None,
                    null_p, null_iterations, null_status)
