# Historical tape evaluation gate

Status 2026-11-17: **no independently verified real market sample run**.
The existing order-book reader and microstructure researcher support LOBSTER
ZIPs, but prior results are from synthetic controls only.

This addition supplies a no-download, standard-library command that accepts
one or more explicitly user-supplied ZIPs. Before computing research outputs,
it checks archive identity, refuses duplicate symbol/session/depth inputs,
preserves SHA-256, validates row alignment using the existing strict parser,
and records usable event count, quote spread, event kinds and session segments.

Download an official LOBSTER free sample independently from:
https://php.lobsterdata.com/info/DataSamples.php

From the repository root, with the ZIP outside version control:

    python3 scripts/validate_historical_tapes.py \
      --lobster-zip /local/path/LOBSTER_SampleFile_AAPL_2012-06-21_1.zip \
      --inspect-only --output lab-output/aapl-inspection.json

To run the existing research engine on that real, independently acquired ZIP,
remove --inspect-only. Repeat --lobster-zip for genuinely distinct sessions.
The per-archive engine fits the signal only on its own chronological training
partition; there is no cross-session result cherry-picking in this wrapper.

One date (even multiple symbols) is **not** multi-day validation.
The output explicitly says whether multiple distinct dates were supplied.
A filename and a hash do not prove vendor authenticity. Even multiple dates
do not turn counterfactual fills into executable strategy PnL. Never publish
sample results as a real alpha win or fitted exchange queue position without
new evidence. Raw vendor files are not committed by this workflow.

Run deterministic synthetic-format gate tests:

    PYTHONPATH=src python3 -m unittest discover -s tests -p test_historical_tapes.py -v

No GitHub Actions or paid market data or hosted compute is involved.
