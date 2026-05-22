#!/usr/bin/env python3
"""
Life expectancy at birth (overall, male, female) from the Wikipedia table
*List of U.S. states and territories by life expectancy* (multi-year columns;
primary sources cited on that page include **CDC NCHS**).

Default year column: **2021** (set `LE_TABLE_YEAR` below). Values overwrite
`Life Expectancy 2019`, `Life Expectancy 2019 Male`, `Life Expectancy 2019 Female`
— CSV headers remain legacy labels.

Source page: https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_life_expectancy
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
    "https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_life_expectancy"
)
LE_TABLE_YEAR = 2021
USER_AGENT = "GovernanceDashboardLERefresh/1.0 (educational)"


def _norm_state(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("_", " ").strip())


def fetch_le(year: int = LE_TABLE_YEAR) -> dict[str, tuple[float, float, float]]:
    """state_name -> (overall, male, female)."""
    req = urllib.request.Request(WIKI_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read()
    t = pd.read_html(BytesIO(html))[0]
    y = str(year)
    if (y, "overall") not in t.columns:
        raise ValueError(f"No ({y}, overall) column in Wikipedia table; columns={t.columns.tolist()[:6]}")

    out: dict[str, tuple[float, float, float]] = {}
    for _, row in t.iterrows():
        st = _norm_state(row[("state", "state")])
        if st in ("US on average", "United States"):
            continue
        try:
            o = float(row[(y, "overall")])
            m = float(row[(y, "male")])
            f = float(row[(y, "female")])
        except (TypeError, ValueError, KeyError):
            continue
        out[st] = (o, m, f)
    # Wikipedia disambiguation labels → Census-style names
    if "Washington (state)" in out and "Washington" not in out:
        out["Washington"] = out["Washington (state)"]
    return out


def refresh_path(
    csv_path: Path,
    year: int = LE_TABLE_YEAR,
    col_all: str = "Life Expectancy 2019",
    col_m: str = "Life Expectancy 2019 Male",
    col_f: str = "Life Expectancy 2019 Female",
) -> int:
    le = fetch_le(year)
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    n = 0
    for row in rows:
        st = _norm_state(row.get("State", ""))
        if st not in le:
            continue
        o, m, f = le[st]
        if col_all in row:
            row[col_all] = f"{o:.1f}"
        if col_m in row:
            row[col_m] = f"{m:.1f}"
        if col_f in row:
            row[col_f] = f"{f:.1f}"
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
    n = refresh_path(path)
    print(f"Life expectancy refresh: {n} states updated ({LE_TABLE_YEAR} column), {path.name}")


if __name__ == "__main__":
    main()
