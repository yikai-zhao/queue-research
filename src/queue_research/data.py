"""LOBSTER public-sample reader: event-aligned best quotes, fixed point prices."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import csv
import io
import re
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


def _read_pair(message_lines, book_lines, limit: int | None = None,
               expected_levels: int | None = None) -> list[BookEvent]:
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
        if expected_levels is not None and len(b) != 4 * expected_levels:
            raise ValueError(f'row {idx + 1}: orderbook columns do not match declared depth {expected_levels}')
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


# A sample consists of two *matched* post-event streams. Equal row counts
# are necessary but not sufficient: mixing tickers, dates or depth levels can
# produce plausible but scientifically meaningless alpha estimates.
_LOBSTER_MEMBER = re.compile(
    r"(?P<identity>[A-Za-z0-9][A-Za-z0-9_.-]*)_"
    r"(?P<kind>message|orderbook)_(?P<levels>[1-9][0-9]*)\.csv", re.IGNORECASE)
_MAX_UNCOMPRESSED_CSV = 512 * 1024 * 1024  # bounded input, never unbounded ZIP inflation


def _identity(member: str, kind: str) -> tuple[str, int]:
    parsed = _LOBSTER_MEMBER.fullmatch(Path(member).name)
    if parsed is None or parsed.group('kind').lower() != kind:
        raise ValueError(f'LOBSTER {kind} filename does not declare an instrument/session/depth')
    return parsed.group('identity'), int(parsed.group('levels'))


def from_lobster_zip(path: str | Path, limit: int | None = None) -> list[BookEvent]:
    """Load matching LOBSTER post-event message/book rows, refusing mixed inputs.

    This is *not* a full-depth simulator: the output retains only top-of-book
    values. Equal filename identity does not certify a data vendor's provenance;
    the caller records a SHA-256 of the input archive.
    """
    with zipfile.ZipFile(path) as archive:
        names = [x for x in archive.namelist() if x.lower().endswith('.csv') and not x.startswith('__MACOSX/')]
        messages = [n for n in names if 'message' in Path(n).name.lower()]
        books = [n for n in names if 'orderbook' in Path(n).name.lower()]
        if len(messages) != 1 or len(books) != 1:
            raise ValueError('archive must contain exactly one message and one orderbook CSV')
        msg, book = messages[0], books[0]
        msg_id, msg_levels = _identity(msg, 'message')
        book_id, book_levels = _identity(book, 'orderbook')
        if msg_id != book_id or Path(msg).parent != Path(book).parent:
            raise ValueError('mismatched message/orderbook instruments or sessions')
        if msg_levels != book_levels:
            raise ValueError('mismatched message/orderbook depth')
        if msg_levels > 50:
            raise ValueError('unsupported orderbook depth above 50')
        if any(archive.getinfo(n).file_size > _MAX_UNCOMPRESSED_CSV for n in (msg, book)):
            raise ValueError('LOBSTER sample exceeds uncompressed CSV size limit')
        with archive.open(msg) as m, archive.open(book) as b:
            return _read_pair(io.TextIOWrapper(m, encoding='utf-8', newline=''),
                              io.TextIOWrapper(b, encoding='utf-8', newline=''),
                              limit=limit, expected_levels=msg_levels)
