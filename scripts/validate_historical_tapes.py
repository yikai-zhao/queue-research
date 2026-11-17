#!/usr/bin/env python3
"""Local, provenance-preserving cohort evaluation of supplied LOBSTER ZIPs.

No download, network access, exchange connection, credentials, live trading,
automatic strategy deployment, or financial performance promise.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import re
from statistics import median
import sys
from zipfile import ZipFile, BadZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from queue_research.data import from_lobster_zip
from queue_research.experiment import study

OFFICIAL_MEMBER = re.compile(
    r"(?P<symbol>[A-Za-z0-9]+)_(?P<day>[0-9]{4}-[0-9]{2}-[0-9]{2})_"
    r"(?P<start>[0-9]+)_(?P<end>[0-9]+)_message_(?P<depth>[0-9]+)\.csv",
    re.IGNORECASE,
)


def identity(path: Path) -> dict:
    with ZipFile(path) as archive:
        matches = [OFFICIAL_MEMBER.fullmatch(Path(name).name)
                   for name in archive.namelist()]
    matches = [m for m in matches if m is not None]
    if len(matches) != 1:
        raise ValueError("expected one official-style LOBSTER message filename")
    fields = matches[0].groupdict()
    day = date.fromisoformat(fields["day"]).isoformat()
    if int(fields["start"]) >= int(fields["end"]):
        raise ValueError("invalid session time window")
    return {"symbol": fields["symbol"].upper(), "day": day,
            "start": int(fields["start"]), "end": int(fields["end"]),
            "depth": int(fields["depth"])}


def inspect(rows) -> dict:
    if not rows:
        raise ValueError("no continuous-book rows")
    spreads = sorted((r.ask - r.bid) / 100 for r in rows)
    kinds = Counter(str(r.kind) for r in rows)
    return {
        "usable_events": len(rows),
        "event_kind_counts": dict(sorted(kinds.items())),
        "first_event_ns": min(r.time_ns for r in rows),
        "last_event_ns": max(r.time_ns for r in rows),
        "segment_count": len({r.segment for r in rows}),
        "spread_ticks_min": spreads[0],
        "spread_ticks_median": median(spreads),
        "spread_ticks_p95_nearest_rank": spreads[(95 * len(spreads) + 99) // 100 - 1],
        "interpretation": "post-event best-level quotes; no order-level FIFO visibility",
    }


def evaluate(paths: list[Path], *, research: bool, max_events: int | None,
             horizon: int = 30) -> dict:
    if not paths:
        raise ValueError("at least one explicit local ZIP required")
    sessions = set()
    dates = set()
    digests = set()
    results = []
    for path in paths:
        meta = identity(path)
        key = (meta["symbol"], meta["day"], meta["start"], meta["end"], meta["depth"])
        if key in sessions:
            raise ValueError("duplicate symbol/session/depth: not an independent sample")
        sessions.add(key)
        dates.add(meta["day"])
        digest = sha256(path.read_bytes()).hexdigest()
        if digest in digests:
            raise ValueError("duplicate input archive digest")
        digests.add(digest)
        rows = from_lobster_zip(path, limit=max_events)
        report = {"input_name": path.name, "sha256": digest,
                  "declared_file_identity": meta, "data_quality": inspect(rows)}
        if research:
            # Each archive is fit/evaluated separately, with no cross-archive
            # parameter selection. Holding out part of one day remains weak.
            report["research"] = study(
                rows, source="LOBSTER provided: " + path.name,
                source_hash=digest, horizon=horizon)
        results.append(report)
    return {
        "schema_version": 1, "source_type": "user_supplied_lobster_style_zips",
        "archive_count": len(results), "distinct_dates": len(dates),
        "independent_day_validation": len(dates) > 1,
        "reports": results,
        "limitations": [
            "Archive filenames and hashes do not authenticate Nasdaq or vendor provenance.",
            "Different symbols on one day are not independent trading dates.",
            "A one-day chronological split is not robust out-of-day validation.",
            "Hypothetical fills and conditional markouts are not strategy PnL.",
            "Event-count latency is not physical execution latency.",
        ],
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lobster-zip", type=Path, action="append", required=True)
    p.add_argument("--output", type=Path, default=Path("lab-output/historical-cohort.json"))
    p.add_argument("--max-events", type=int)
    p.add_argument("--horizon", type=int, default=30)
    p.add_argument("--inspect-only", action="store_true",
                   help="validate and summarize input without fitting a signal")
    a = p.parse_args(argv)
    if a.max_events is not None and a.max_events < 1:
        p.error("--max-events must be positive")
    try:
        report = evaluate(a.lobster_zip, research=not a.inspect_only,
                          max_events=a.max_events, horizon=a.horizon)
    except (OSError, ValueError, BadZipFile, UnicodeError) as exc:
        p.error(str(exc))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(a.output),
                      "archives": report["archive_count"],
                      "distinct_dates": report["distinct_dates"],
                      "independent_day_validation": report["independent_day_validation"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
