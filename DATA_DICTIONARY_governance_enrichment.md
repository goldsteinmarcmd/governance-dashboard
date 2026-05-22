# Governance CSV — suggested columns (enrichment)

**Folder:** repository root (same directory as `enrich_governance_csv.py`)

**Files**

- Source sheet: `governence_data - Sheet1.csv` (place or update this file here).
- Enriched sheet (original columns + new): `governence_data_enriched_acs2022.csv` (same folder; filename is historical — contents use the ACS vintage set in `enrich_governance_csv.py`).
- Regenerate: `python3 enrich_governance_csv.py` (requires network for Census API).

**Vintage:** U.S. Census Bureau **ACS 5-year** product year is set by **`ACS_YEAR`** in `enrich_governance_csv.py` (currently **2024** → period **2020–2024**). ACS 5-year is a **period** estimate, not a single-year snapshot.

## Columns merged or overwritten from the Census API

On each `enrich_governance_csv.py` run, these **existing** sheet columns are **overwritten** with ACS estimates (same vintage as `ACS vintage (suggested metrics)`):

| Sheet column | Census variable(s) | Notes |
|--------------|-------------------|--------|
| `Median Income` | **B19013_001E** | Median household income in the past 12 months (inflation-adjusted dollars for that ACS year). |
| `Poverty Rate (%)` | **B17001_002E** ÷ **B17001_001E** × 100 | Population for whom poverty status determined; below poverty. |
| `Number in Poverty` | **B17001_002E** | Count below poverty. |
| `Population (2022)` | **B01003_001E** | Total population; **header still says 2022** — values track the ACS vintage in `ACS vintage (suggested metrics)`. |
| `Gini Coefficient 2019` | **B19083_001E** | Gini index of income inequality; **header still says 2019** — values are ACS 5-year, not a single calendar year. |
| `Gini Coefficient 2015-2019` | **B19083_001E** | Same as `Gini Coefficient 2019` after enrichment (legacy duplicate column in the template). |
| `Population over the age of 25` | **S1501_C01_006E** | Population 25 years and over (ACS subject **S1501**). |
| `With a High School Diploma or higher` | **S1501_C01_014E** | Count with high school graduate or higher (25+). |
| `With a Bachelor's Degree or higher` | **S1501_C01_015E** | Count with bachelor’s degree or higher (25+). |
| `With an Advanced Degree` | **S1501_C01_013E** | Count with graduate or professional degree (25+). |

## New columns appended by enrichment

| New column | Definition | Census / source |
|------------|------------|-----------------|
| `ACS vintage (suggested metrics)` | Label for the row’s ACS product | Literal from script, e.g. `2024 ACS 5-year` |
| `Uninsured population ACS (count)` | People with no health insurance coverage | `B27001` — sum of all “No health insurance coverage” leaf estimates |
| `Uninsured rate ACS (% of pop in B27001 universe)` | Uninsured ÷ `B27001_001E` total | Same table |
| `Rent burden 30%+ ACS (% renter HH)` | Renter households paying ≥30% of income on gross rent | `B25070_007E`–`010E` ÷ `B25070_001E` |
| `Rent burden 50%+ ACS (% renter HH)` | Renter households paying ≥50% of income on gross rent | `B25070_010E` ÷ `B25070_001E` |
| `Child poverty rate ACS (% under 18)` | Under-18 in poverty ÷ under-18 population in poverty universe | `B17001` — sum below-poverty under-18 ÷ (below + at/above under-18) |
| `SNAP household rate ACS (% HH)` | Households receiving SNAP ÷ all households | `B22001_002E` ÷ `B22001_001E` |
| `Broadband household rate ACS (% HH)` | Households with any broadband subscription | `B28002_004E` ÷ `B28002_001E` |
| `No internet access ACS (% HH)` | Households with no internet access | `B28002_013E` ÷ `B28002_001E` |
| `Medicaid expansion adopted (Y/N)` | ACA Medicaid expansion adopted | **Manual rule:** `N` for Alabama, Florida, Georgia, Kansas, Mississippi, South Carolina, Tennessee, Texas, Wisconsin, Wyoming; `Y` otherwise. **Re-verify** at [KFF Medicaid expansion](https://www.kff.org/medicaid/status-of-state-medicaid-expansion-decisions/) when politics change (e.g. new state adoptions). |

## Violent crime (FBI UCR)

| Column | Definition | Source |
|--------|------------|--------|
| `Total Violent Crimes Occurred per 100,000` | Violent crimes per 100,000 residents | **FBI UCR** rate for the configured year (default **2024**), taken from the Wikipedia article [*List of U.S. states and territories by violent crime rate*](https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_violent_crime_rate) (which cites published CIUS / FBI tables). |
| `Total Violent Crimes (2020)` | **Estimated** violent-crime count | `rate ÷ 100,000 ×` **Population** (ACS **B01003** after enrichment). The header still says **(2020)** for template compatibility; the numeric rate year is set in `refresh_violent_crime_ucr.py` (`DEFAULT_UCR_YEAR`). |

Refreshed by **`refresh_violent_crime_ucr.py`** (also run automatically at the end of **`enrich_governance_csv.py`**). For authoritative numbers, cross-check the [FBI Crime Data Explorer](https://cde.ucr.cjis.gov/).

## Incarceration (Vera Institute)

| Column | Definition | Source |
|--------|------------|--------|
| `Incarcerated Total` | Latest-year `total_incarceration` from Vera | [Incarceration Trends — state CSV](https://raw.githubusercontent.com/vera-institute/incarceration_trends/main/incarceration_trends_state.csv) ([repo](https://github.com/vera-institute/incarceration_trends), [site](https://trends.vera.org/)). |
| `Incarceration Rate` | `total_incarceration` ÷ ACS **B01003** population × 100 (% of residents) | Same; compare with [BJS](https://bjs.ojp.gov/). |

Refreshed by **`refresh_vera_incarceration.py`** (chained after `enrich_governance_csv.py`).

## Life expectancy (Wikipedia → CDC citations)

| Column | Definition | Source |
|--------|------------|--------|
| `Life Expectancy 2019`, `… Male`, `… Female` | **2021** column (default) from Wikipedia [*life expectancy by state*](https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_life_expectancy) | Page cites **CDC NCHS**; verify with [CDC life expectancy](https://www.cdc.gov/nchs/life-expectancy.htm) and [IHME](https://www.healthdata.org/research-analysis/gbd). Headers remain “2019” for template compatibility. |

Refreshed by **`refresh_life_expectancy.py`**. Keep **`LE_TABLE_YEAR`** in that script aligned with **`LE_DATA_YEAR`** in `app.py`.

## State GDP (BEA)

| Column | Definition | Source |
|--------|------------|--------|
| `State GDP (2022) (in millions)` | BEA Regional **SAGDP2N**, LineCode **1**, current dollars (millions) | [BEA — GDP by state](https://www.bea.gov/data/gdp/gdp-state); API User ID: [signup](https://apps.bea.gov/API/signup/index.cfm). Set **`BEA_API_KEY`**; optional **`BEA_GDP_YEAR`** (default **2023** in `refresh_bea_gdp.py`, synced with **`GDP_DATA_YEAR`** in `app.py`). |

Refreshed by **`refresh_bea_gdp.py`** when the API key is present (otherwise skipped).

## EPA AQI columns

`Median AQI`, `Max AQI`, `90th Percentile AQI`, and `% … Days` fields are **not** overwritten automatically (`refresh_epa_aqi.py` is a placeholder). Use [EPA AirData](https://www.epa.gov/outdoor-air-quality-data), [AQS](https://www.epa.gov/aqs), and [AirNow](https://www.airnow.gov/) to update the sheet or extend the script.

## End-to-end refresh

```bash
arch -arm64 python3 enrich_governance_csv.py
```

runs ACS merge, then (in order): **`refresh_violent_crime_ucr`**, **`refresh_vera_incarceration`**, **`refresh_life_expectancy`**, **`refresh_bea_gdp`** (if `BEA_API_KEY` set), **`refresh_epa_aqi`** (no-op unless extended).

**Join key**

- Original `State` uses underscores (`New_York`). The script maps to Census `NAME` by replacing `_` with a space.
