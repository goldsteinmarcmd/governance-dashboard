#!/usr/bin/env python3
"""
Refresh state violent-crime rate and estimated violent-crime counts from the
Wikipedia table *List of U.S. states and territories by violent crime rate*,
which reproduces FBI Uniform Crime Reporting (UCR) / Crime in the United States
figures (see the Wikipedia page's own citations).

This avoids the FBI CDE API key requirement while keeping a clear, reproducible
secondary source. Re-verify figures for publication against
https://cde.ucr.cjis.gov/ or published CIUS tables.

Usage:
  arch -arm64 python3 refresh_violent_crime_ucr.py
  arch -arm64 python3 refresh_violent_crime_ucr.py path/to/governence_data_enriched_acs2022.csv
"""
from __future__ import annotations

import csv
import re
import sys
import urllib.request
from io import BytesIO
from pathlib import Path

import pandas as pd

WIKI_URL = (
    "https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_violent_crime_rate"
)
# Keep in sync with `UCR_VIOLENT_YEAR` in `app.py` (dashboard citations).
DEFAULT_UCR_YEAR = 2024
USER_AGENT = "GovernanceDashboardUCRRefresh/1.0 (educational; contact: local)"


def _norm_state_key(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip())


def fetch_wikipedia_rates(year: int = DEFAULT_UCR_YEAR) -> dict[str, float]:
    """Return state_name -> violent crime rate per 100k for `year` column."""
    req = urllib.request.Request(WIKI_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read()
    tables = pd.read_html(BytesIO(html))
    t = tables[1]
    if str(year) not in t.columns:
        raise ValueError(f"Wikipedia table has no {year} column; got {list(t.columns)}")
    out: dict[str, float] = {}
    for _, row in t.iterrows():
        loc = _norm_state_key(row["Location"])
        if loc in ("United States", "Puerto Rico") or loc.startswith("Territories"):
            continue
        v = row[str(year)]
        try:
            rate = float(v)
        except (TypeError, ValueError):
            continue
        out[loc] = rate
    return out


def refresh_path(
    csv_path: Path,
    year: int = DEFAULT_UCR_YEAR,
    rate_col: str = "Total Violent Crimes Occurred per 100,000",
    count_col: str = "Total Violent Crimes (2020)",
    pop_col: str = "Population (2022)",
) -> int:
    """Update `csv_path` in place. Returns number of rows updated."""
    rates = fetch_wikipedia_rates(year)
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if rate_col not in fieldnames or count_col not in fieldnames:
        raise ValueError(f"CSV missing expected columns; have: {fieldnames[:8]}…")

    n = 0
    for row in rows:
        st = _norm_state_key(row.get("State", "").replace("_", " "))
        if st not in rates:
            continue
        rate = rates[st]
        row[rate_col] = f"{rate:.1f}"
        pop_raw = row.get(pop_col, "")
        pop_s = re.sub(r"[,$]", "", str(pop_raw).strip())
        try:
            pop = float(pop_s)
        except ValueError:
            pop = float("nan")
        if pop > 0 and rate == rate:
            est = int(round(rate * pop / 100_000))
            row[count_col] = str(est)
            n += 1

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return n


def main() -> None:
    root = Path(__file__).resolve().parent
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "governence_data_enriched_acs2022.csv"
    if not path.exists():
        print(f"Missing {path}", file=sys.stderr)
        sys.exit(1)
    y = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_UCR_YEAR
    n = refresh_path(path, year=y)
    print(f"Updated violent-crime fields for {n} states in {path} (UCR year column {y}, Wikipedia → FBI CIUS).")


if __name__ == "__main__":
    main()
