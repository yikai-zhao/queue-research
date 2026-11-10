# Data provenance and reproducibility

**Current committed evidence:** locally generated, seeded synthetic market-like events. No real market tape is included, downloaded or claimed as processed.

**Optional historical validation:** LOBSTER provides publicly accessible sample ZIP archives for a small number of tickers, all from 2012-06-21, including AAPL best-level sample. Each archive contains an event `message` CSV and a matching `orderbook` CSV. The event line describes the change leading to its same-index post-event book snapshot. More depth levels in the archive do not change this code's deliberately top-level-only execution assumptions.

- Samples: https://php.lobsterdata.com/info/DataSamples.php
- Schema and event interpretation: https://php.lobsterdata.com/info/DataStructure.php
- Suggested file: `LOBSTER_SampleFile_AAPL_2012-06-21_1.zip`

The development runtime could browse the provider documentation but could **not download the ZIP** because external binary access/DNS was unavailable. Tests therefore construct their own schema-compatible small ZIPs and exercise strict alignment, precision, row corruption, halt filtering and missing-file errors. That is only **format compatibility testing**, not real NASDAQ empirical validation.

To reproduce real-data analysis, download ZIP yourself from the provider's site, keep it outside the repository, and run:

```
PYTHONPATH=src python -m queue_research --lobster-zip /your/path/LOBSTER_SampleFile_AAPL_2012-06-21_1.zip --output lab-output/lobster-aapl.json
```

The JSON report includes SHA-256 of the input ZIP. Do not copy or commit the vendor dataset into this project without confirming its licence. Do not infer market profit from the result: a one-day intraday sample has a severely limited train/test diversity and replay cannot model own-order impact.
