#!/usr/bin/env python3
"""
EPA Air Quality Index (AQI) — **state-level summaries are not exposed here** through a
single stable, keyless bulk API suitable for this repo (EPA sites often use CloudFront
restrictions for scripted access).

**What to do instead**
- Export state summaries from the [Air Quality System (AQS)](https://www.epa.gov/aqs)
  or [AirNow](https://www.airnow.gov/) / [AirData](https://www.epa.gov/outdoor-air-quality-data),
  then merge manually, **or**
- Add a small CSV in this folder (e.g. `data/epa_aqi_by_state.csv`) with columns
  `State`, `Median AQI`, `Max AQI`, … and extend this script to read it.

`refresh_path` is a no-op so the enrichment pipeline can import it safely.
"""
from __future__ import annotations

import sys
from pathlib import Path


def refresh_path(csv_path: Path) -> int:
    return 0


def main() -> None:
    root = Path(__file__).resolve().parent
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "governence_data_enriched_acs2022.csv"
    refresh_path(path)


if __name__ == "__main__":
    main()
