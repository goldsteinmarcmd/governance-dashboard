#!/usr/bin/env python3
"""
Vera Institute — *Incarceration Trends* state file (jail + prison + related totals).

Source: [incarceration_trends_state.csv](https://raw.githubusercontent.com/vera-institute/incarceration_trends/main/incarceration_trends_state.csv)
in [vera-institute/incarceration_trends](https://github.com/vera-institute/incarceration_trends).

Updates `Incarcerated Total` and `Incarceration Rate` (% of total resident population, matching prior
sheet semantics: incarcerated ÷ ACS population × 100).
"""
from __future__ import annotations

import csv
import re
import sys
import urllib.request
from io import StringIO
from pathlib import Path

VERA_CSV = (
    "https://raw.githubusercontent.com/vera-institute/incarceration_trends/main/"
    "incarceration_trends_state.csv"
)


def _norm_state(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("_", " ").strip())


def _latest_rows_by_state(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Pick the chronologically latest `year` row per `state_name` with a usable total."""
    best: dict[str, tuple[int, dict[str, str]]] = {}
    for row in rows:
        st = row.get("state_name", "").strip()
        if not st or not str(row.get("total_incarceration", "")).strip():
            continue
        try:
            y = int(float(row.get("year", "0")))
        except ValueError:
            continue
        cur = best.get(st)
        if cur is None or y > cur[0]:
            best[st] = (y, row)
    return {st: pair[1] for st, pair in best.items()}


def refresh_path(
    csv_path: Path,
    pop_col: str = "Population (2022)",
    total_col: str = "Incarcerated Total",
    rate_col: str = "Incarceration Rate",
) -> int:
    with urllib.request.urlopen(VERA_CSV, timeout=120) as resp:
        text = resp.read().decode()

    vera_rows = list(csv.DictReader(StringIO(text)))
    vera_by_state = _latest_rows_by_state(vera_rows)

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if total_col not in fieldnames or rate_col not in fieldnames:
        raise ValueError(f"CSV missing {total_col} or {rate_col}")

    n = 0
    for row in rows:
        st = _norm_state(row.get("State", ""))
        vr = vera_by_state.get(st)
        if not vr:
            continue
        try:
            ti = float(vr.get("total_incarceration") or 0)
        except ValueError:
            continue
        if ti <= 0:
            continue
        pop_raw = re.sub(r"[,$]", "", str(row.get(pop_col, "")).strip())
        try:
            pop = float(pop_raw)
        except ValueError:
            pop = 0.0
        total_int = int(round(ti))
        row[total_col] = f"{total_int:,}"
        if pop > 0:
            pct = 100.0 * ti / pop
            row[rate_col] = f"{pct:.2f}%"
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
    print(f"Vera incarceration refresh: {n} states updated in {path.name}")


if __name__ == "__main__":
    main()
