"""Counterfactual passive fill study. Not PnL; orders do not modify replayed depth."""
from __future__ import annotations
from dataclasses import dataclass
from statistics import mean
from .data import BookEvent


@dataclass(frozen=True)
class Fill:
    model: str
    side: int
    entry_index: int
    activation_index: int
    fill_index: int | None
    quantity: int
    filled: int
    limit_price: int
    markout_ticks: float | None
    status: str = "unknown"  # distinguish unobservable/invalid from genuine non-fill


def simulate_order(rows: list[BookEvent], index: int, direction: int, *,
                   model: str = 'conservative', latency_events: int = 2,
                   horizon_events: int = 40, quantity: int = 10,
                   fee_bps: float = 0) -> Fill:
    if model not in ('naive_touch', 'conservative', 'cancel_ahead'):
        raise ValueError('unknown queue model')
    if direction not in (-1, 1) or index < 0 or latency_events < 1 or horizon_events <= latency_events:
        raise ValueError('bad side, index, latency or horizon')
    if quantity <= 0 or quantity > 10000 or not -5 <= fee_bps <= 100:
        raise ValueError('invalid quantity or fee')
    finish = index + horizon_events
    active = index + latency_events
    if finish >= len(rows):
        raise ValueError('insufficient future events')
    # A fill before a halt is not permission to mark it to a post-halt
    # midprice. Exclude the entire probe rather than silently counting the
    # invalid cross-session markout as a trade outcome.
    if rows[finish].segment != rows[index].segment:
        price = rows[index].bid if direction == 1 else rows[index].ask
        return Fill(model, direction, index, active, None, quantity, 0,
                    price, None, 'ineligible_session_boundary')
    # Limit price is fixed at SIGNAL time, not picked from the future
    # activation snapshot. Repricing at arrival would leak future quotes.
    signal_snapshot = rows[index]
    limit_price = signal_snapshot.bid if direction == 1 else signal_snapshot.ask
    snapshot = rows[active]
    active_best = snapshot.bid if direction == 1 else snapshot.ask
    ahead = snapshot.bid_qty if direction == 1 else snapshot.ask_qty
    filled = 0
    first_fill = None
    if snapshot.segment != signal_snapshot.segment or active_best != limit_price:
        # Quote moved during latency. No retroactive adjustment or free fill.
        return Fill(model, direction, index, active, None, quantity, 0,
                    limit_price, None, 'no_fill_quote_changed_during_latency')
    if model == 'naive_touch':
        filled, first_fill = quantity, active
    else:
        for j in range(active+1, finish+1):
            ev = rows[j]
            if ev.segment != signal_snapshot.segment:
                break
            # LOBSTER book row is POST-event. A final visible execution can
            # consume the last displayed volume at our price and move best
            # quote away. Apply the same-row execution BEFORE retiring the
            # hypothetical order, otherwise the most important fill is lost.
            best = ev.bid if direction == 1 else ev.ask
            if ev.price == limit_price and ev.side == direction:
                if ev.kind == 4:  # execution of the resting order at price
                    flow = ev.quantity
                    passing = max(0, flow - ahead)
                    ahead = max(0, ahead - flow)
                    new_fill = min(quantity-filled, passing)
                    if new_fill and first_fill is None:
                        first_fill = j
                    filled += new_fill
                elif model == 'cancel_ahead' and ev.kind in (2, 3):
                    # Optimistic bound: all cancellations ahead, unknown in L2.
                    ahead = max(0, ahead - ev.quantity)
            if best != limit_price:
                break  # price left the top of book; no free touch-back fill
            if filled == quantity:
                break
    # Markout is hypothetical signed liquidation relative to mid at fixed horizon.
    # Fee is per filled unit; this is NOT executable spread PnL / strategy return.
    markout = (direction*(rows[finish].mid - limit_price)/100 -
               fee_bps * limit_price / 1_000_000) if filled else None
    return Fill(model, direction, index, active, first_fill, quantity, filled,
                limit_price, round(markout, 6) if markout is not None else None,
                'filled' if filled else 'no_fill_queue_or_quote_departure')


def comparison(rows: list[BookEvent], signals: list[tuple[int, int]], *,
               latency_events: int = 2, horizon_events: int = 40,
               quantity: int = 10, fee_bps: float = 0) -> dict:
    result = {}
    for model in ('naive_touch','cancel_ahead','conservative'):
        outcomes = [simulate_order(rows, i, s, model=model,
                                   latency_events=latency_events,
                                   horizon_events=horizon_events,
                                   quantity=quantity, fee_bps=fee_bps)
                    for i,s in signals]
        f = sum(x.filled for x in outcomes)
        filled = [x for x in outcomes if x.filled]
        eligible = [x for x in outcomes if x.status != 'ineligible_session_boundary']
        result[model] = {
            'hypothetical_orders': len(outcomes),
            'eligible_orders': len(eligible),
            'ineligible_session_boundary_orders': len(outcomes) - len(eligible),
            'quote_changed_during_latency': sum(x.status == 'no_fill_quote_changed_during_latency'
                                                for x in outcomes),
            'filled_orders': len(filled),
            'partially_filled_orders': sum(0 < x.filled < quantity for x in outcomes),
            'fill_quantity_fraction': round(f/(len(outcomes)*quantity), 6) if outcomes else None,
            'eligible_fill_quantity_fraction': round(f/(len(eligible)*quantity), 6) if eligible else None,
            'mean_fill_conditional_markout_ticks': round(
                sum(x.filled*x.markout_ticks for x in filled)/f, 6) if f else None,
            'interpretation': 'counterfactual standalone orders; not portfolio PnL'
        }
    return result
