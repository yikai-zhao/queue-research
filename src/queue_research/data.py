"""LOBSTER public-sample reader: event-aligned best quotes, fixed point prices."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import csv
import io
import zipfile


@dataclass(frozen=True, slots=True)
class BookEvent:
    seq: int
    time_ns: int
    kind: int
    order_id: int
    quantity: int
    price: int  # USD * 10000; same as LOBSTER
    side: int  # +1 resting buy, -1 resting sell
    ask: int
    ask_qty: int
    bid: int
    bid_qty: int
    segment: int = 0  # incremented after auction / halt discontinuities

    @property
    def mid(self) -> float:
        return (self.ask + self.bid) / 2

    @property
    def imbalance(self) -> float:
        return (self.bid_qty - self.ask_qty) / (self.bid_qty + self.ask_qty)


def _read_pair(message_lines, book_lines, limit: int | None = None) -> list[BookEvent]:
    messages = csv.reader(message_lines)
    books = csv.reader(book_lines)
    result = []
    prev_time = -1
    segment = 0
    for idx, (m, b) in enumerate(zip(messages, books, strict=True)):
        if limit is not None and idx >= limit:
            break
        if len(m) != 6 or len(b) < 4 or len(b) % 4:
            raise ValueError(f'row {idx + 1}: expected 6 message and 4*N book columns')
        try:
            t = int(Decimal(m[0]) * 1_000_000_000)
            kind, oid, qty, price, side = (int(x) for x in m[1:])
            ask, aq, bid, bq = (int(x) for x in b[:4])
        except (ValueError, InvalidOperation) as exc:
            raise ValueError(f'row {idx + 1}: malformed field') from exc
        if t < prev_time or t < 0 or t >= 86_400_000_000_000:
            raise ValueError(f'row {idx + 1}: invalid or out-of-order timestamp')
        prev_time = t
        if kind not in (1, 2, 3, 4, 5, 6, 7) or qty < 0 or oid < 0:
            raise ValueError(f'row {idx + 1}: invalid event')
        if kind in (6, 7):
            segment += 1  # prevent labels and simulated orders crossing a halt
            continue
        if side not in (-1, 1) or qty <= 0 or price <= 0:
            raise ValueError(f'row {idx + 1}: invalid order side, size or price')
        if ask <= bid or bid <= 0 or aq <= 0 or bq <= 0:
            raise ValueError(f'row {idx + 1}: invalid best quote')
        result.append(BookEvent(idx, t, kind, oid, qty, price, side, ask, aq, bid, bq, segment))
    if not result:
        raise ValueError('no usable continuous-book events')
    return result


def from_lobster_zip(path: str | Path, limit: int | None = None) -> list[BookEvent]:
    """Read official sample zip without redistributing vendor-provided market data.

    A message row is paired with the same-numbered *post-event* book row.
    This is not an order-level queue snapshot; initial queue position is unknown.
    """
    with zipfile.ZipFile(path) as archive:
        names = [x for x in archive.namelist() if x.lower().endswith('.csv') and not x.startswith('__MACOSX/')]
        messages = [n for n in names if 'message' in Path(n).name.lower()]
        books = [n for n in names if 'orderbook' in Path(n).name.lower()]
        if len(messages) != 1 or len(books) != 1:
            raise ValueError('archive must contain exactly one message and one orderbook CSV')
        with archive.open(messages[0]) as m, archive.open(books[0]) as b:
            return _read_pair(io.TextIOWrapper(m, encoding='utf-8', newline=''),
                              io.TextIOWrapper(b, encoding='utf-8', newline=''), limit=limit)
