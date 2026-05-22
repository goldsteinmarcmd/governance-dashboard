#!/usr/bin/env python3
"""
Merge U.S. Census ACS 5-year state estimates into governance CSV.

Uses the latest ACS 5-year vintage available in this script (see ACS_YEAR).
Sources documented in DATA_DICTIONARY_governance_enrichment.md (same folder).

Overwrites several previously spreadsheet-only columns with Census API values:
median household income (B19013), poverty rate & count (B17001), population (B01003),
Gini (B19083), and educational attainment counts (ACS subject **S1501**).
"""
from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

ACS_YEAR = "2024"
ACS_PRODUCT = "acs/acs5"
BASE = f"https://api.census.gov/data/{ACS_YEAR}/{ACS_PRODUCT}"

# KFF-style: states that have NOT adopted ACA Medicaid expansion as commonly cited (~2025).
# North Carolina expanded 2024 — excluded here. Verify periodically at kff.org.
NOT_MEDICAID_EXPANDED = {
    "Alabama",
    "Florida",
    "Georgia",
    "Kansas",
    "Mississippi",
    "South Carolina",
    "Tennessee",
    "Texas",
    "Wisconsin",
    "Wyoming",
}

B27001_UNINSURED = [
    "B27001_005E",
    "B27001_008E",
    "B27001_011E",
    "B27001_014E",
    "B27001_017E",
    "B27001_020E",
    "B27001_023E",
    "B27001_026E",
    "B27001_029E",
    "B27001_033E",
    "B27001_036E",
    "B27001_039E",
    "B27001_042E",
    "B27001_045E",
    "B27001_048E",
    "B27001_051E",
    "B27001_054E",
    "B27001_057E",
]

B17001_CHILD_BELOW = [
    "B17001_004E",
    "B17001_005E",
    "B17001_006E",
    "B17001_007E",
    "B17001_008E",
    "B17001_009E",
    "B17001_018E",
    "B17001_019E",
    "B17001_020E",
    "B17001_021E",
    "B17001_022E",
    "B17001_023E",
]
B17001_CHILD_ABOVE = [
    "B17001_033E",
    "B17001_034E",
    "B17001_035E",
    "B17001_036E",
    "B17001_037E",
    "B17001_038E",
    "B17001_047E",
    "B17001_048E",
    "B17001_049E",
    "B17001_050E",
    "B17001_051E",
    "B17001_052E",
]


def census_get(var_list: list[str]) -> list[list]:
    vars_csv = ",".join(["NAME"] + var_list)
    url = f"{BASE}?get={vars_csv}&for=state:*"
    with urllib.request.urlopen(url, timeout=120) as resp:
        return json.loads(resp.read().decode())


def census_get_subject(var_list: list[str]) -> list[list]:
    vars_csv = ",".join(["NAME"] + var_list)
    surl = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5/subject?get={vars_csv}&for=state:*"
    with urllib.request.urlopen(surl, timeout=120) as resp:
        return json.loads(resp.read().decode())


def rows_to_dict(data: list[list]) -> dict[str, dict[str, float | int]]:
    """ACS estimates as numbers; suppressed / missing codes → 0 (callers use totals that tolerate 0)."""
    header, *body = data
    idx = {h: i for i, h in enumerate(header)}
    out: dict[str, dict[str, float | int]] = {}
    for row in body:
        name = row[idx["NAME"]]
        d: dict[str, float | int] = {}
        for h in header:
            if h in ("NAME", "state"):
                continue
            v = row[idx[h]]
            if v is None or str(v).strip() in ("-666666666", "-666666666.0", ""):
                d[h] = 0
            else:
                s = str(v).strip()
                d[h] = float(s) if "." in s else int(s)
        out[name] = d
    return out


def patch_acs_floats(raw: list[list], target: dict[str, dict[str, float | int]], fields: list[str]) -> None:
    """Overwrite selected keys with float parsing (avoids truncating Gini, etc.)."""
    header, *body = raw
    idx = {h: i for i, h in enumerate(header)}
    for row in body:
        name = row[idx["NAME"]]
        d = target[name]
        for f in fields:
            if f not in idx:
                continue
            v = row[idx[f]]
            if v is None or str(v).strip() in ("-666666666", "-666666666.0", ""):
                continue
            d[f] = float(str(v).strip())


def safe_pct(num: float, den: float) -> str:
    if den <= 0:
        return ""
    return f"{100.0 * num / den:.2f}"


def main() -> None:
    root = Path(__file__).resolve().parent
    src = root / "governence_data - Sheet1.csv"
    dst = root / "governence_data_enriched_acs2022.csv"

    # --- Fetch Census (3 requests) ---
    d1 = rows_to_dict(census_get(["B27001_001E"] + B27001_UNINSURED))
    raw2 = census_get(
        [
            "B25070_001E",
            "B25070_007E",
            "B25070_008E",
            "B25070_009E",
            "B25070_010E",
            "B22001_001E",
            "B22001_002E",
            "B28002_001E",
            "B28002_004E",
            "B28002_013E",
            "B19013_001E",
            "B01003_001E",
            "B19083_001E",
        ]
    )
    d2 = rows_to_dict(raw2)
    patch_acs_floats(raw2, d2, ["B19083_001E"])
    raw3 = census_get(["B17001_001E", "B17001_002E"] + B17001_CHILD_BELOW + B17001_CHILD_ABOVE)
    d3 = rows_to_dict(raw3)
    d_ed = rows_to_dict(
        census_get_subject(
            [
                "S1501_C01_006E",
                "S1501_C01_014E",
                "S1501_C01_015E",
                "S1501_C01_013E",
            ]
        )
    )

    metrics: dict[str, dict[str, str]] = {}
    for name in d1:
        u = d1[name]
        tot = float(u["B27001_001E"])
        unins = sum(float(u[k]) for k in B27001_UNINSURED)
        r2 = d2.get(name, {})
        r3 = d3.get(name, {})
        ed = d_ed.get(name, {})

        rent_tot = float(r2.get("B25070_001E", 0))
        rent_burden_30p = sum(float(r2.get(k, 0)) for k in ("B25070_007E", "B25070_008E", "B25070_009E", "B25070_010E"))
        rent_severe_50p = float(r2.get("B25070_010E", 0))

        snap_hh = float(r2.get("B22001_002E", 0))
        snap_tot = float(r2.get("B22001_001E", 0))

        inet_tot = float(r2.get("B28002_001E", 0))
        bb = float(r2.get("B28002_004E", 0))
        no_inet = float(r2.get("B28002_013E", 0))

        ch_below = sum(float(r3.get(k, 0)) for k in B17001_CHILD_BELOW)
        ch_above = sum(float(r3.get(k, 0)) for k in B17001_CHILD_ABOVE)
        ch_tot = ch_below + ch_above

        pov_tot = float(r3.get("B17001_001E", 0))
        pov_below = float(r3.get("B17001_002E", 0))
        med_hh = float(r2.get("B19013_001E", 0))
        pop_acs = float(r2.get("B01003_001E", 0))
        gini_acs = float(r2.get("B19083_001E", 0))

        pop25 = int(float(ed.get("S1501_C01_006E", 0)))
        hs_plus = int(float(ed.get("S1501_C01_014E", 0)))
        bach_plus = int(float(ed.get("S1501_C01_015E", 0)))
        grad_deg = int(float(ed.get("S1501_C01_013E", 0)))

        st_plain = name
        metrics[st_plain] = {
            "ACS vintage": f"{ACS_YEAR} ACS 5-year",
            "Uninsured population (count)": str(int(unins)),
            "Uninsured rate (% of civilian noninstitutional population)": safe_pct(unins, tot),
            "Renter households paying 30%+ of income on gross rent (% of renter households)": safe_pct(
                rent_burden_30p, rent_tot
            ),
            "Renter households paying 50%+ of income on gross rent (% of renter households)": safe_pct(
                rent_severe_50p, rent_tot
            ),
            "Child poverty rate (% under 18 in poverty / children counted)": safe_pct(ch_below, ch_tot),
            "SNAP household participation rate (% of households)": safe_pct(snap_hh, snap_tot),
            "Households with broadband subscription (% of households)": safe_pct(bb, inet_tot),
            "Households with no internet access (% of households)": safe_pct(no_inet, inet_tot),
            "Medicaid expansion adopted (Y/N; KFF-style non-expansion list)": (
                "N" if st_plain in NOT_MEDICAID_EXPANDED else "Y"
            ),
            # Overwrite key spreadsheet columns with same-vintage ACS (see DATA_DICTIONARY)
            "Median Income (B19013)": f"{int(med_hh)}" if med_hh > 0 else "",
            "Poverty Rate (B17001) %": safe_pct(pov_below, pov_tot),
            "Number in Poverty (B17001)": str(int(pov_below)) if pov_tot > 0 else "",
            "Population ACS (B01003)": str(int(pop_acs)) if pop_acs > 0 else "",
            "Gini ACS (B19083)": f"{gini_acs:.4f}" if 0 < gini_acs < 1.0 else "",
            "Pop 25+ (S1501)": f"{pop25:,}" if pop25 else "",
            "HS+ (S1501)": f"{hs_plus:,}" if hs_plus else "",
            "Bachelor+ (S1501)": f"{bach_plus:,}" if bach_plus else "",
            "Graduate (S1501)": f"{grad_deg:,}" if grad_deg else "",
        }

    # --- Read original CSV and append columns ---
    with src.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    new_cols = [
        "ACS vintage (suggested metrics)",
        "Uninsured population ACS (count)",
        "Uninsured rate ACS (% of pop in B27001 universe)",
        "Rent burden 30%+ ACS (% renter HH)",
        "Rent burden 50%+ ACS (% renter HH)",
        "Child poverty rate ACS (% under 18)",
        "SNAP household rate ACS (% HH)",
        "Broadband household rate ACS (% HH)",
        "No internet access ACS (% HH)",
        "Medicaid expansion adopted (Y/N)",
    ]
    out_fields = fieldnames + new_cols

    def norm_state(s: str) -> str:
        return s.replace("_", " ").strip()

    for row in rows:
        st = norm_state(row.get("State", ""))
        m = metrics.get(st, {})
        row["ACS vintage (suggested metrics)"] = m.get("ACS vintage", "")
        row["Uninsured population ACS (count)"] = m.get("Uninsured population (count)", "")
        row["Uninsured rate ACS (% of pop in B27001 universe)"] = m.get(
            "Uninsured rate (% of civilian noninstitutional population)", ""
        )
        row["Rent burden 30%+ ACS (% renter HH)"] = m.get(
            "Renter households paying 30%+ of income on gross rent (% of renter households)", ""
        )
        row["Rent burden 50%+ ACS (% renter HH)"] = m.get(
            "Renter households paying 50%+ of income on gross rent (% of renter households)", ""
        )
        row["Child poverty rate ACS (% under 18)"] = m.get(
            "Child poverty rate (% under 18 in poverty / children counted)", ""
        )
        row["SNAP household rate ACS (% HH)"] = m.get(
            "SNAP household participation rate (% of households)", ""
        )
        row["Broadband household rate ACS (% HH)"] = m.get(
            "Households with broadband subscription (% of households)", ""
        )
        row["No internet access ACS (% HH)"] = m.get(
            "Households with no internet access (% of households)", ""
        )
        row["Medicaid expansion adopted (Y/N)"] = m.get(
            "Medicaid expansion adopted (Y/N; KFF-style non-expansion list)", ""
        )

        if m.get("Median Income (B19013)"):
            row["Median Income"] = m["Median Income (B19013)"]
        if m.get("Poverty Rate (B17001) %"):
            row["Poverty Rate (%)"] = m["Poverty Rate (B17001) %"]
        if m.get("Number in Poverty (B17001)"):
            row["Number in Poverty"] = m["Number in Poverty (B17001)"]
        if m.get("Population ACS (B01003)"):
            if "Population (2022)" in row:
                row["Population (2022)"] = m["Population ACS (B01003)"]
        if m.get("Gini ACS (B19083)"):
            row["Gini Coefficient 2019"] = m["Gini ACS (B19083)"]
            if "Gini Coefficient 2015-2019" in row:
                row["Gini Coefficient 2015-2019"] = m["Gini ACS (B19083)"]

        if m.get("Pop 25+ (S1501)") and "Population over the age of 25" in row:
            row["Population over the age of 25"] = m["Pop 25+ (S1501)"]
        if m.get("HS+ (S1501)") and "With a High School Diploma or higher" in row:
            row["With a High School Diploma or higher"] = m["HS+ (S1501)"]
        if m.get("Bachelor+ (S1501)") and "With a Bachelor's Degree or higher" in row:
            row["With a Bachelor's Degree or higher"] = m["Bachelor+ (S1501)"]
        if m.get("Graduate (S1501)") and "With an Advanced Degree" in row:
            row["With an Advanced Degree"] = m["Graduate (S1501)"]

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {dst}")

    for mod_name, label in (
        ("refresh_violent_crime_ucr", "Violent crime (UCR)"),
        ("refresh_vera_incarceration", "Vera incarceration"),
        ("refresh_life_expectancy", "Life expectancy (Wikipedia)"),
        ("refresh_bea_gdp", "BEA GDP"),
        ("refresh_epa_aqi", "EPA AQI"),
    ):
        try:
            mod = __import__(mod_name, fromlist=["refresh_path"])
            n = mod.refresh_path(dst)
            print(f"{label}: completed (n={n}), {dst.name}")
        except Exception as exc:
            print(f"{label} skipped ({exc})")


if __name__ == "__main__":
    main()
