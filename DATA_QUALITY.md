# Data quality — `governence_data - Sheet1.csv`

**Path:** same folder as this file.  
**Pass date:** 2026-04-19 (automated checks + manual spot review).

---

## Fixes applied this pass

| Issue | Location | Action |
|--------|----------|--------|
| Spreadsheet formula in a cell | Nebraska, `State House Majority %` was `#DIV/0!` | Removed by fixing inputs (see Nebraska below). |
| Impossible / missing numeric | Nebraska, `Life Expectancy 2019 Female` was `0` | Set to **81.0** as a placeholder consistent with neighboring years; **replace with an official CDC/NCHS value** when you cite this publicly. |
| Wrong state in narrative | South Dakota, `Sick Leave Policy` cited **North Dakota** | Corrected to **South Dakota**. |
| Name typo | New York, `Governor` **Holuch** | Corrected to **Hochul**. |
| Header typo | `State House Repbulicans` | Renamed to **`State House Republicans`** (regenerate enriched CSV so the new header propagates). |
| Nebraska legislature shape | `State House` counts were `0` / `0` (unicameral state; template assumed two houses) | Filled **house** columns by mirroring **unicameral** membership **16 D / 33 R**, **67%** Republican majority, **Party Control** `Republican` — **verify** against your primary source (e.g. NELIS / Ballotpedia) for the exact session you care about. |
| Copy typos in long text | NJ sick leave **evert**; NY **40 hour a year**; WA **than can** | Corrected to **every**, **40 hours a year**, **that can**. |

The three comparative disclaimer lines you asked removed from the “spreadsheet” were **not present as rows in the CSV**; they only appeared in prior chat / docs. **`DATA_DICTIONARY_governance_enrichment.md`** was trimmed so it no longer carries the extra “not food insecurity / not KFF / not free internet” wording.

---

## Automated checks (re-run anytime)

```bash
arch -arm64 python3 -c "
import csv
from pathlib import Path
p = Path('governence_data - Sheet1.csv')
rows = list(csv.DictReader(p.open(encoding='utf-8')))
bad = []
for i, r in enumerate(rows, start=2):
    for k, v in r.items():
        if v and any(x in v for x in ('#DIV', '#VALUE', '#REF')):
            bad.append((i, r.get('State'), k, v[:60]))
    try:
        if float(r.get('Life Expectancy 2019 Female') or -1) == 0:
            bad.append((i, r.get('State'), 'LE female', '0'))
    except ValueError:
        pass
print('flags', len(bad))
for b in bad:
    print(b)
"
```

After this pass: **0 flags** on formula tokens and zero female LE.

---

## ACS refresh (enrichment)

After `enrich_governance_csv.py`, **median income**, **poverty rate**, **number in poverty**, **population** (`Population (2022)` header), and **Gini** columns in **`governence_data_enriched_acs2022.csv`** match the **ACS 5-year vintage** in `ACS vintage (suggested metrics)` (see `DATA_DICTIONARY_governance_enrichment.md`). Other columns may still be older manual imports until you replace them from primary sources.

The same command chain also runs, in order: **`refresh_violent_crime_ucr.py`** (FBI UCR via Wikipedia), **`refresh_vera_incarceration.py`** (Vera *Incarceration Trends*), **`refresh_life_expectancy.py`** (Wikipedia → CDC-cited table), **`refresh_bea_gdp.py`** (BEA **SAGDP2N** if `BEA_API_KEY` is set), and **`refresh_epa_aqi.py`** (placeholder; AQI fields remain manual unless you extend it). Re-verify FBI, BJS, CDC, and BEA figures before external publication.

## Manual review backlog (not auto-fixable without sources)

1. **Mixed years across columns** — e.g. GDP 2022, life expectancy 2019, violent crime 2020, while ACS-backed fields use the enrichment vintage. Fine for exploration; **label charts** with the correct vintage per column when publishing.
2. **Governor / party freshness** — several names and balances drift after elections (e.g. Louisiana row still shows a prior administration in your snapshot). **Refresh** from a single election-date cut.
3. **North Carolina** — sick-leave narrative may be **stale** relative to Medicaid expansion and local law changes; **re-verify** against current statutes.
4. **Nebraska female LE (81.0)** — placeholder until tied to **CDC WONDER** or another official series.
5. **New Hampshire House** — very large seat counts (197/198); may be correct for that chamber’s size — **sanity-check** against official roster.

---

## Enriched file

After changing the **header** (`Repbulicans` → `Republicans`), run:

```bash
arch -arm64 python3 enrich_governance_csv.py
```

so `governence_data_enriched_acs2022.csv` column names stay aligned with the source sheet.
