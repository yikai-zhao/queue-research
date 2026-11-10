"""Expanding chronological re-fits and strictly out-of-fold event-time markouts.

Adjacent test blocks belong to the same tape: this is a stability diagnostic,
not independent-day validation or evidence of tradable returns.
"""
from __future__ import annotations

from math import isfinite
from statistics import mean, median

from .data import BookEvent
from .research import _scores, side


def expanding_folds(rows: list[BookEvent], *, horizon: int = 30,
                    thresholds: tuple[float, ...] = (.15, .25, .35, .45),
                    initial_train_fraction: float = .4,
                    fold_fraction: float = .15,
                    min_training_signals: int = 20) -> dict:
    """Select threshold on history only; evaluate disjoint future windows.

    Label interval [i, i+horizon] must remain *entirely* in its own fold.
    Holdout positions are separated by horizon+1 events; different folds
    never reuse holdout positions. The underlying market path is still shared.
    """
    if (type(horizon) is not int or horizon < 1 or len(rows) < 5*horizon):
        raise ValueError('insufficient data or invalid horizon')
    if not (isfinite(initial_train_fraction) and isfinite(fold_fraction) and
            0 < initial_train_fraction < 1 and 0 < fold_fraction <= 1-initial_train_fraction):
        raise ValueError('invalid predeclared split fractions')
    if (not thresholds or any(not isfinite(t) or not 0 < t <= 1 for t in thresholds)
            or len(set(thresholds)) != len(thresholds)):
        raise ValueError('invalid threshold grid')
    if type(min_training_signals) is not int or min_training_signals < 1:
        raise ValueError('invalid min_training_signals')
    n = len(rows)
    first = int(n*initial_train_fraction)
    step = int(n*fold_fraction)
    if first <= horizon or step <= horizon:
        raise ValueError('folds too short for horizon')
    folds, all_scores = [], []
    start = first
    while start + horizon < n:
        stop = min(start + step, n)
        if stop - start <= horizon:
            break
        fitted = []
        for threshold in thresholds:
            # _scores excludes labels maturing at/after training cutoff.
            train = _scores(rows, horizon, 0, start, threshold)
            if len(train) >= min_training_signals:
                fitted.append((mean(train), -threshold, threshold, len(train)))
        if not fitted:
            folds.append({'train_end_exclusive': start,
                          'test_start': start, 'test_end_exclusive': stop,
                          'status': 'insufficient_training_signals',
                          'test_count': 0})
            start = stop
            continue
        _, _, chosen, train_count = max(fitted)
        tests = []
        for i in range(start, stop-horizon, horizon+1):
            if rows[i].segment != rows[i+horizon].segment:
                continue
            direction = side(rows[i].imbalance, chosen)
            if direction:
                tests.append(direction*(rows[i+horizon].mid-rows[i].mid)/100)
        all_scores.extend(tests)
        folds.append({'train_end_exclusive': start,
                      'test_start': start, 'test_end_exclusive': stop,
                      'status': 'evaluated' if tests else 'no_eligible_test_signals',
                      'chosen_threshold': chosen, 'train_signals': train_count,
                      'test_count': len(tests),
                      'test_mean_signed_ticks': round(mean(tests), 6) if tests else None,
                      'test_positive_fraction': round(sum(x>0 for x in tests)/len(tests), 6)
                      if tests else None})
        start = stop
    values = [x['test_mean_signed_ticks'] for x in folds if x.get('test_mean_signed_ticks') is not None]
    return {'method':'expanding_train_reselection_disjoint_nonoverlapping_event_holdouts',
            'horizon_events': horizon,
            'thresholds_predeclared': list(thresholds),
            'folds': folds, 'fold_count': len(folds),
            'folds_with_test_signals': len(values),
            'total_disjoint_test_signals': len(all_scores),
            'pooled_nonoverlap_mean_signed_ticks':round(mean(all_scores),6) if all_scores else None,
            'median_fold_mean_signed_ticks':round(median(values),6) if values else None,
            'positive_fold_count':sum(x>0 for x in values),
            'limitations':[
                'Within-tape chronological folds share market regimes and expanding training sets; they are NOT independent days or independent p-value replicates.',
                'Training selects among predeclared thresholds; test folds are used only for evaluation, not post-hoc configuration selection.',
                'Midprice markouts are not executable order returns and ignore fees, fills, and portfolio risk.',
                'Event-count horizon is not physical time; crossing a halt/auction removes a label.',
            ]}
