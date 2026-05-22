#!/usr/bin/env python3
"""
U.S. Bureau of Economic Analysis (BEA) — **current-dollar GDP** by state (annual).

Requires a free **BEA API User ID** in the environment variable **`BEA_API_KEY`**
(sign up: https://apps.bea.gov/API/signup/index.cfm).

Uses Regional dataset **SAGDP2N** (Gross domestic product, NAICS, current dollars),
LineCode **1** (All industry total), GeoFIPS `SS000` (state SS FIPS padded to 5 digits + 000).

Docs: https://apps.bea.gov/API/signup/index.cfm and
https://www.bea.gov/resources/for-developers

Updates column `State GDP (2022) (in millions)` with the requested `GDP_YEAR`
(in millions, same units as the column name implies — verify the year you pass).
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BEA_URL = "https://apps.bea.gov/api/data"
GDP_YEAR_DEFAULT = "2023"
# Keep in sync with dashboard citation `GDP_DATA_YEAR` in app.py when you change this.
GDP_YEAR = os.environ.get("BEA_GDP_YEAR", GDP_YEAR_DEFAULT)


def _norm_state(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("_", " ").strip())


def census_state_fips() -> dict[str, str]:
    """Full state name -> 2-digit FIPS string (e.g. California -> 06)."""
    url = "https://api.census.gov/data/2024/acs/acs5?get=NAME&for=state:*"
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    header, *body = data
    ni, ns = header.index("NAME"), header.index("state")
    return {row[ni]: row[ns].zfill(2) for row in body}


def bea_state_gdp_millions(user_id: str, year: str) -> dict[str, float]:
    """State name -> GDP in millions of current dollars."""
    fips_map = census_state_fips()
    out: dict[str, float] = {}
    for name, sf in fips_map.items():
        geofips = sf + "000"
        q = urllib.parse.urlencode(
            {
                "UserID": user_id,
                "method": "GetData",
                "datasetname": "Regional",
                "TableName": "SAGDP2N",
                "LineCode": "1",
                "GeoFIPS": geofips,
                "Year": year,
                "ResultFormat": "json",
            }
        )
        url = f"{BEA_URL}?{q}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            payload = json.loads(resp.read().decode())
        err = payload.get("BEAAPI", {}).get("Results", {}).get("Error")
        if err:
            raise RuntimeError(str(err))
        rows = payload.get("BEAAPI", {}).get("Results", {}).get("Data") or []
        if not rows:
            continue
        # DataValue is in millions for this table in practice; BEA returns string number
        raw = rows[0].get("DataValue", "").replace(",", "")
        try:
            out[name] = float(raw)
        except ValueError:
            continue
    return out


def refresh_path(
    csv_path: Path,
    gdp_col: str = "State GDP (2022) (in millions)",
    year: str | None = None,
) -> int:
    uid = (os.environ.get("BEA_API_KEY") or "").strip()
    if not uid:
        raise RuntimeError("Set BEA_API_KEY (BEA API User ID) to refresh GDP; see refresh_bea_gdp.py docstring.")

    yr = year or GDP_YEAR
    gdp_by_state = bea_state_gdp_millions(uid, yr)

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if gdp_col not in fieldnames:
        raise ValueError(f"CSV missing {gdp_col}")

    n = 0
    for row in rows:
        st = _norm_state(row.get("State", ""))
        if st not in gdp_by_state:
            continue
        v = gdp_by_state[st]
        row[gdp_col] = f"{v:,.0f}"
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
    print(f"BEA GDP refresh: {n} states updated ({GDP_YEAR}), {path.name}")


if __name__ == "__main__":
    main()
