"""
Reasonable Future / governance — evidence dashboard (Streamlit + Plotly).

Run (from repo root):
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements-dashboard.txt
  streamlit run app.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import pearsonr

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "governence_data_enriched_acs2022.csv"
NATIONAL_TS_PATH = HERE / "us_national_timeseries.csv"

# --- Data citations (provenance) ---
ACS_YEAR_LABEL = "2024"
ACS_INTRO = (
    "U.S. Census Bureau, **American Community Survey (ACS) "
    + ACS_YEAR_LABEL
    + " 5-year** estimates (period **2020–2024**) via "
    "[Census API](https://api.census.gov/data/2024/acs/acs5.html)."
)
# Keep in sync with DEFAULT_UCR_YEAR in `refresh_violent_crime_ucr.py`.
UCR_VIOLENT_YEAR = "2024"
UCR_VIOLENT_CITATION = (
    "**FBI Uniform Crime Reporting (UCR)** state violent-crime **rate per 100,000** ("
    + UCR_VIOLENT_YEAR
    + " column) taken from the Wikipedia article "
    "[*List of U.S. states and territories by violent crime rate*]"
    "(https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_violent_crime_rate) "
    "(compiled from published CIUS / FBI figures — see that page’s citations). "
    "**Estimated violent-crime counts** = rate × **Population** ÷ 100,000, using the ACS population "
    "column in the same row. For publication, re-verify on the "
    "[FBI Crime Data Explorer](https://cde.ucr.cjis.gov/). "
    "Legacy CSV headers still say **(2020)**; values follow the UCR year above."
)
ACS_CITATION = (
    ACS_INTRO
    + " Tables: **B27001** (insurance), **B25070** (rent burden), **B22001** (SNAP), "
    "**B28002** (internet/broadband), **B17001** (poverty by age + overall poverty rate), "
    "**B19013** (median household income), **B01003** (population), **B19083** (Gini), "
    "**S1501** (educational attainment — population 25+, HS+, bachelor’s or higher, graduate). "
    "[ACS subject group S1501](https://api.census.gov/data/2024/acs/acs5/subject/groups/S1501.html). "
    "Merged by `enrich_governance_csv.py`; definitions in `DATA_DICTIONARY_governance_enrichment.md`."
)
KFF_MEDICAID_CITATION = (
    "**Medicaid expansion (Y/N):** derived in `enrich_governance_csv.py` using a KFF-style "
    "non-expansion state list — re-verify against "
    "[KFF — Status of State Medicaid Expansion Decisions](https://www.kff.org/medicaid/status-of-state-medicaid-expansion-decisions/)."
)
PEARSON_METHOD_CITATION = (
    "Correlations: **scipy.stats.pearsonr** (Pearson **r**); **R²** = **r²**; **p** = two-sided test of "
    "H₀: ρ = 0. Many pairwise tests → exploratory unless you adjust for multiplicity."
)
# --- Canonical portals (use in citations; keep refresh scripts aligned where noted) ---
LINK_CDC_NCHS_LE = "[CDC NCHS — life expectancy](https://www.cdc.gov/nchs/life-expectancy.htm)"
LINK_IHME = "[IHME — US health / GBD](https://www.healthdata.org/research-analysis/gbd)"
LINK_LE_WIKI = "[Wikipedia — life expectancy by state](https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_life_expectancy)"
# Keep in sync with `LE_TABLE_YEAR` in `refresh_life_expectancy.py`.
LE_DATA_YEAR = "2021"
LINK_HRSA_AHRF = "[HRSA — Area Health Resources Files](https://data.hrsa.gov/topics/health-workforce/ahrf)"
LINK_AAMC_STATE = "[AAMC — State physician workforce](https://www.aamc.org/data-reports/workforce/interactive-data/active-physicians-state-level-supply-and-specialty-data)"
LINK_BJS = "[BJS — Bureau of Justice Statistics](https://bjs.ojp.gov/)"
LINK_VERA_IT = "[Vera — Incarceration Trends](https://github.com/vera-institute/incarceration_trends)"
LINK_VERA_STATE_CSV = "[Vera — state-year CSV (raw)](https://raw.githubusercontent.com/vera-institute/incarceration_trends/main/incarceration_trends_state.csv)"
VERA_INCARCERATION_CITATION = (
    "**Incarceration totals and rates** from Vera Institute [*Incarceration Trends*](https://trends.vera.org/) "
    "state file (" + LINK_VERA_STATE_CSV + "), latest `year` row per state. **Rate** = incarcerated ÷ ACS "
    "**B01003** population × 100 (same as prior sheet semantics). Cross-check with " + LINK_BJS + "."
)
LINK_EPA_AQS = "[EPA — Air Quality System (AQS)](https://www.epa.gov/aqs)"
LINK_EPA_AIRNOW = "[EPA — AirNow](https://www.airnow.gov/)"
LINK_EPA_AIRDATA = "[EPA — outdoor air quality data](https://www.epa.gov/outdoor-air-quality-data)"
EPA_AQI_CITATION = (
    "**AQI summary fields** (median / max / day-type shares) are still **manually maintained** in the project CSV "
    "(no automated EPA pull in this repo — see `refresh_epa_aqi.py`). Compare against "
    + LINK_EPA_AIRDATA + ", " + LINK_EPA_AQS + ", and " + LINK_EPA_AIRNOW + "."
)
# Keep in sync with `GDP_YEAR_DEFAULT` / `BEA_GDP_YEAR` in `refresh_bea_gdp.py`.
GDP_DATA_YEAR = "2023"
LINK_BEA_GDP = "[BEA — GDP by state](https://www.bea.gov/data/gdp/gdp-state)"
LINK_BEA_API_SIGNUP = "[BEA — API User ID (free)](https://apps.bea.gov/API/signup/index.cfm)"
BEA_GDP_CITATION = (
    "**Current-dollar state GDP** (millions) from **BEA** Regional dataset **SAGDP2N** line 1 via `refresh_bea_gdp.py` "
    "(requires **`BEA_API_KEY`** User ID from " + LINK_BEA_API_SIGNUP + "). "
    "Concept: " + LINK_BEA_GDP + ". Default data year **" + GDP_DATA_YEAR + "** (override with `BEA_GDP_YEAR`). "
    "Legacy column title may still say 2022."
)
LINK_NCES = "[NCES — National Center for Education Statistics](https://nces.ed.gov/)"
LINK_NCES_REVEXP = "[NCES — revenues & expenditures](https://nces.ed.gov/programs/school_finance)"
LINK_NGA = "[NGA — governors](https://www.nga.org/governors/)"
LINK_BALLOTPEDIA = "[Ballotpedia](https://ballotpedia.org/Main_Page)"
LINK_OPENSTATES = "[Open States](https://openstates.org/)"
LINK_NCSL_LABOR = "[NCSL — labor & employment](https://www.ncsl.org/labor-and-employment)"
SPREADSHEET_BASE = (
    "Values from the project CSV (`governence_data - Sheet1.csv` → `governence_data_enriched_acs2022.csv`). "
    "Mixed vintages across columns — see **`DATA_QUALITY.md`** before citing externally."
)
LIFE_EXPECT_CITATION = (
    "**Life expectancy at birth** (" + LE_DATA_YEAR + " column) from " + LINK_LE_WIKI + " "
    "(page cites **CDC NCHS** and related official series). Verify with " + LINK_CDC_NCHS_LE + " or "
    + LINK_IHME + ". **CSV headers still say 2019** for template compatibility."
)
PHYSICIANS_CITATION = (
    "**Physicians per 100k** — still entered manually in the sheet; typical primary sources are "
    + LINK_HRSA_AHRF + " and " + LINK_AAMC_STATE + ". " + SPREADSHEET_BASE
)

INTERNAL_METRIC_CITATIONS: dict[str, str] = {
    "_median_income": (
        "**Median household income.** ACS **B19013_001E** (median in past 12 months). "
        + ACS_INTRO
        + " Overwritten on each `enrich_governance_csv.py` run."
    ),
    "_poverty_pct": (
        "**Poverty rate (%).** ACS **B17001** — `B17001_002E` ÷ `B17001_001E` (below poverty ÷ poverty universe). "
        + ACS_INTRO
        + " Overwritten on each enrich run."
    ),
    "_uninsured_pct": "**Uninsured rate (%).** " + ACS_CITATION + " Uses **B27001** uninsured leaf estimates ÷ `B27001_001E`.",
    "_child_pov_pct": "**Child poverty (% under 18).** " + ACS_CITATION + " From **B17001** below-poverty vs. child poverty universe.",
    "_rent30": "**Rent burden ≥30% (renter HH).** " + ACS_CITATION,
    "_rent50": "**Rent burden ≥50% (renter HH).** " + ACS_CITATION,
    "_snap": "**SNAP household rate.** " + ACS_CITATION,
    "_broadband": "**Households with broadband.** " + ACS_CITATION,
    "_no_internet": "**Households with no internet access.** " + ACS_CITATION,
    "_gini": (
        "**Gini index of income inequality.** ACS **B19083_001E** (stored in legacy column **Gini Coefficient 2019**). "
        + ACS_INTRO
        + " Column header is legacy; numeric values follow this ACS vintage."
    ),
    "_le": "**Life expectancy (all).** " + LIFE_EXPECT_CITATION + " Refreshed by `refresh_life_expectancy.py`.",
    "_le_m": "**Life expectancy (male).** " + LIFE_EXPECT_CITATION,
    "_le_f": "**Life expectancy (female).** " + LIFE_EXPECT_CITATION,
    "_md_per_100k": "**Physicians per 100k.** " + PHYSICIANS_CITATION,
    "_violent_per_100k": "**Violent crimes per 100k.** " + UCR_VIOLENT_CITATION,
    "_incarceration_pct": "**Incarceration rate (% of residents).** " + VERA_INCARCERATION_CITATION + " Refreshed by `refresh_vera_incarceration.py`.",
    "_median_aqi": "**Median AQI.** " + EPA_AQI_CITATION,
    "_sick_ordinal": (
        "**Sick-leave ordinal (derived).** Heuristic mapping of **Sick Leave Policy** text in the spreadsheet; "
        "verify statutes via " + LINK_NCSL_LABOR + " and state codes."
    ),
    "_medicaid_n": KFF_MEDICAID_CITATION + " Encoded as 1 = Y, 0 = N for plotting.",
}

# Citations for original CSV column names (full table / transparency)
SHEET_COLUMN_CITATIONS: dict[str, str] = {
    "State": "State name; join key (underscores normalized to spaces in the app).",
    "Governor": "Compiled in project spreadsheet; verify with " + LINK_NGA + " or each state’s official site.",
    "Party": "Governor party label. " + SPREADSHEET_BASE + " Cross-check " + LINK_BALLOTPEDIA + ".",
    "State Senate Democrats": "Legislative counts — " + SPREADSHEET_BASE + " Verify with " + LINK_OPENSTATES + " or state legislature sites.",
    "State Senate Republicans": "Legislative counts — " + SPREADSHEET_BASE + " Verify with " + LINK_OPENSTATES + " or state legislature sites.",
    "State Senate Majority": "Majority label — " + SPREADSHEET_BASE + " Verify with " + LINK_OPENSTATES + ".",
    "State Senate Majority %": "Share — " + SPREADSHEET_BASE + " Verify with " + LINK_OPENSTATES + ".",
    "State House Democrats": "Legislative counts — " + SPREADSHEET_BASE + " Nebraska unicameral: see `DATA_QUALITY.md`. Verify with " + LINK_OPENSTATES + ".",
    "State House Republicans": "Legislative counts — " + SPREADSHEET_BASE + " Verify with " + LINK_OPENSTATES + ".",
    "State House Majority": "Majority label — " + SPREADSHEET_BASE + " Verify with " + LINK_OPENSTATES + ".",
    "State House Majority %": "Share — " + SPREADSHEET_BASE + " Verify with " + LINK_OPENSTATES + ".",
    "Party Control": "Composite label — " + SPREADSHEET_BASE + " Confirm methodology with " + LINK_BALLOTPEDIA + " / " + LINK_OPENSTATES + ".",
    "Median Income": (
        "**Median household income** — ACS **B19013_001E**; overwritten by `enrich_governance_csv.py`. " + ACS_INTRO
    ),
    "State GDP (2022) (in millions)": BEA_GDP_CITATION,
    "Gini Coefficient 2019": "**Gini index** — ACS **B19083_001E**; legacy column name. " + ACS_INTRO,
    "Gini Coefficient 2015-2019": (
        "Mirrors **Gini Coefficient 2019** on enrich (ACS **B19083**); legacy dual column from the sheet template."
    ),
    "Population (2022)": (
        "**Resident population** — ACS **B01003_001E**; overwritten by enrich. "
        "Column title still says 2022; values match the ACS vintage in **ACS vintage (suggested metrics)**."
    ),
    "Life Expectancy 2019": LIFE_EXPECT_CITATION + " Refreshed by `refresh_life_expectancy.py`.",
    "Life Expectancy 2019 Male": LIFE_EXPECT_CITATION,
    "Life Expectancy 2019 Female": LIFE_EXPECT_CITATION,
    "Sick Leave Policy": "Manual narrative — verify with " + LINK_NCSL_LABOR + " and state statutes; drives `_sick_ordinal`.",
    "Number of Doctors per 100,000 resident population": PHYSICIANS_CITATION,
    "Total Education Funding (in thousands)": (
        "**K–12 / education funding** — still manual in the sheet. See " + LINK_NCES_REVEXP + " and " + LINK_NCES + ". " + SPREADSHEET_BASE
    ),
    "Population over the age of 25": "**Count — population 25+.** ACS **S1501_C01_006E**; overwritten by `enrich_governance_csv.py`. " + ACS_INTRO,
    "With a High School Diploma or higher": "**Count — HS graduate or higher (25+).** ACS **S1501_C01_014E**; overwritten by enrich. " + ACS_INTRO,
    "With a Bachelor's Degree or higher": "**Count — bachelor’s degree or higher (25+).** ACS **S1501_C01_015E**; overwritten by enrich. " + ACS_INTRO,
    "With an Advanced Degree": "**Count — graduate or professional degree (25+).** ACS **S1501_C01_013E**; overwritten by enrich. " + ACS_INTRO,
    "Number in Poverty": (
        "**Count below poverty** — ACS **B17001_002E**; overwritten by `enrich_governance_csv.py`. " + ACS_INTRO
    ),
    "Poverty Rate (%)": (
        "**Poverty rate** — 100 × **B17001_002E** ÷ **B17001_001E**; overwritten by enrich. " + ACS_INTRO
    ),
    "Incarcerated Total": "**Estimated incarcerated population** (Vera `total_incarceration`). " + VERA_INCARCERATION_CITATION,
    "Incarceration Rate": "**% of residents incarcerated** (Vera total ÷ ACS population). " + VERA_INCARCERATION_CITATION,
    "Total Violent Crimes (2020)": "**Estimated violent crimes** (rate × population ÷ 100k). " + UCR_VIOLENT_CITATION,
    "Total Violent Crimes Occurred per 100,000": "**Violent crime rate per 100k.** " + UCR_VIOLENT_CITATION,
    "Max AQI": "**Maximum AQI** — manual sheet field. " + EPA_AQI_CITATION,
    "90th Percentile AQI": "**90th percentile AQI** — manual sheet field. " + EPA_AQI_CITATION,
    "Median AQI": "**Median AQI** — manual sheet field. " + EPA_AQI_CITATION,
    "% Good Days": "**% good AQI days** — manual sheet field. " + EPA_AQI_CITATION,
    "% Moderate Days": "**% moderate AQI days** — manual sheet field. " + EPA_AQI_CITATION,
    "% Unhealthy for Sensitive Groups Days": "**% USG AQI days** — manual sheet field. " + EPA_AQI_CITATION,
    "% Unhealthy Days": "**% unhealthy AQI days** — manual sheet field. " + EPA_AQI_CITATION,
    "% Very Unhealthy Days": "**% very unhealthy AQI days** — manual sheet field. " + EPA_AQI_CITATION,
    "% Hazardous Days": "**% hazardous AQI days** — manual sheet field. " + EPA_AQI_CITATION,
    "ACS vintage (suggested metrics)": (
        "Literal ACS product label from `enrich_governance_csv.py` (currently **"
        + ACS_YEAR_LABEL
        + " ACS 5-year**)."
    ),
    "Uninsured population ACS (count)": "Uninsured count from **B27001** leaves. " + ACS_CITATION,
    "Uninsured rate ACS (% of pop in B27001 universe)": "Uninsured ÷ B27001 universe. " + ACS_CITATION,
    "Rent burden 30%+ ACS (% renter HH)": "From **B25070**. " + ACS_CITATION,
    "Rent burden 50%+ ACS (% renter HH)": "From **B25070**. " + ACS_CITATION,
    "Child poverty rate ACS (% under 18)": "From **B17001**. " + ACS_CITATION,
    "SNAP household rate ACS (% HH)": "From **B22001**. " + ACS_CITATION,
    "Broadband household rate ACS (% HH)": "From **B28002**. " + ACS_CITATION,
    "No internet access ACS (% HH)": "From **B28002**. " + ACS_CITATION,
    "Medicaid expansion adopted (Y/N)": KFF_MEDICAID_CITATION,
}

DERIVED_COLUMN_CITATIONS: dict[str, str] = {
    "state_name": "Normalized **State** field (underscores → spaces) for display.",
    "STUSPS": "Two-letter USPS code mapped from state name for Plotly **USA-states** choropleth.",
}

STUSPS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def norm_state(s: str) -> str:
    return str(s).replace("_", " ").strip()


def to_float_series(s: pd.Series) -> pd.Series:
    out = []
    for v in s.astype(str):
        v = v.strip().strip('"')
        if v in ("", "nan", "#DIV/0!", "#VALUE!", "N/A"):
            out.append(float("nan"))
            continue
        v = re.sub(r"[%$,]", "", v)
        try:
            out.append(float(v))
        except ValueError:
            out.append(float("nan"))
    return pd.Series(out, index=s.index)


def sick_leave_ordinal(text: str) -> float:
    """Rough 0/1/2 for map coloring; refine with a proper rubric later."""
    t = str(text).lower()
    if "does not require paid sick leave" in t or (
        "does not require" in t and "sick" in t
    ):
        return 0.0
    if "preempt" in t and "does not require" not in t:
        return 0.0
    if any(x in t for x in ("earn one hour", "entitled", "required to provide", "must provide")):
        return 2.0
    return 1.0


def medicaid_numeric(s: str) -> float:
    v = str(s).strip().upper()
    if v == "Y":
        return 1.0
    if v == "N":
        return 0.0
    return float("nan")


@st.cache_data
def load() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df["state_name"] = df["State"].map(norm_state)
    df["STUSPS"] = df["state_name"].map(STUSPS)

    pairs = [
        ("Median Income", "_median_income"),
        ("Poverty Rate (%)", "_poverty_pct"),
        ("Uninsured rate ACS (% of pop in B27001 universe)", "_uninsured_pct"),
        ("Child poverty rate ACS (% under 18)", "_child_pov_pct"),
        ("Rent burden 30%+ ACS (% renter HH)", "_rent30"),
        ("Rent burden 50%+ ACS (% renter HH)", "_rent50"),
        ("SNAP household rate ACS (% HH)", "_snap"),
        ("Broadband household rate ACS (% HH)", "_broadband"),
        ("No internet access ACS (% HH)", "_no_internet"),
        ("Gini Coefficient 2019", "_gini"),
        ("Life Expectancy 2019", "_le"),
        ("Life Expectancy 2019 Male", "_le_m"),
        ("Life Expectancy 2019 Female", "_le_f"),
        ("Number of Doctors per 100,000 resident population", "_md_per_100k"),
        ("Total Violent Crimes Occurred per 100,000", "_violent_per_100k"),
        ("Incarceration Rate", "_incarceration_pct"),
        ("Median AQI", "_median_aqi"),
    ]
    for src, dst in pairs:
        if src in df.columns:
            df[dst] = to_float_series(df[src])

    if "Sick Leave Policy" in df.columns:
        df["_sick_ordinal"] = df["Sick Leave Policy"].map(sick_leave_ordinal)
    if "Medicaid expansion adopted (Y/N)" in df.columns:
        df["_medicaid_n"] = df["Medicaid expansion adopted (Y/N)"].map(medicaid_numeric)

    return df


def correlation_matrices(
    df: pd.DataFrame, cols: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Pairwise Pearson r, R² (= r² for simple linear association), and two-sided p-values."""
    n = len(cols)
    r_arr = np.eye(n, dtype=float)
    p_arr = np.zeros((n, n), dtype=float)
    for i, ci in enumerate(cols):
        for j, cj in enumerate(cols):
            if i >= j:
                continue
            sub = df[[ci, cj]].dropna()
            if len(sub) < 3:
                r_arr[i, j] = r_arr[j, i] = np.nan
                p_arr[i, j] = p_arr[j, i] = np.nan
            else:
                r, p = pearsonr(sub[ci].astype(float), sub[cj].astype(float))
                r_arr[i, j] = r_arr[j, i] = r
                p_arr[i, j] = p_arr[j, i] = p
    np.fill_diagonal(p_arr, np.nan)
    r_df = pd.DataFrame(r_arr, index=cols, columns=cols)
    p_df = pd.DataFrame(p_arr, index=cols, columns=cols)
    r2_df = r_df.pow(2)
    return r_df, r2_df, p_df


def metric_defs(df: pd.DataFrame) -> list[tuple[str, str]]:
    opts = [
        ("_median_income", "Median household income ($)"),
        ("_uninsured_pct", "Uninsured rate (ACS %)"),
        ("_poverty_pct", "Poverty rate (sheet %)"),
        ("_child_pov_pct", "Child poverty (ACS %)"),
        ("_rent30", "Rent burden 30%+ (ACS %)"),
        ("_rent50", "Rent burden 50%+ (ACS %)"),
        ("_snap", "SNAP household rate (ACS %)"),
        ("_broadband", "Broadband (ACS % HH)"),
        ("_no_internet", "No internet (ACS % HH)"),
        ("_gini", "Gini 2019"),
        ("_le", "Life expectancy 2019"),
        ("_le_m", "Life expectancy male 2019"),
        ("_le_f", "Life expectancy female 2019"),
        ("_md_per_100k", "MDs per 100k"),
        ("_violent_per_100k", f"Violent crime per 100k (UCR {UCR_VIOLENT_YEAR})"),
        ("_incarceration_pct", "Incarceration rate (%)"),
        ("_median_aqi", "Median AQI"),
        ("_sick_ordinal", "Sick leave strength (0 weak – 2 stronger)"),
        ("_medicaid_n", "Medicaid expansion (1=Y 0=N)"),
    ]
    return [(c, t) for c, t in opts if c in df.columns]


def cite_internal(key: str) -> str:
    return INTERNAL_METRIC_CITATIONS.get(
        key,
        "No dedicated citation string; see `DATA_QUALITY.md` and `governence_data_enriched_acs2022.csv`.",
    )


def cite_column(name: str) -> str:
    if name in DERIVED_COLUMN_CITATIONS:
        return DERIVED_COLUMN_CITATIONS[name]
    if name in SHEET_COLUMN_CITATIONS:
        return SHEET_COLUMN_CITATIONS[name]
    if name.startswith("_"):
        return cite_internal(name)
    return SPREADSHEET_BASE


def citations_table_for_df(df: pd.DataFrame) -> pd.DataFrame:
    rows = [{"Column": c, "Citation / source": cite_column(c)} for c in sorted(df.columns)]
    return pd.DataFrame(rows)


def main() -> None:
    st.set_page_config(page_title="Governance dashboard", layout="wide", initial_sidebar_state="expanded")
    st.title("Governance dashboard")
    st.caption(
        "Reasonable Future · state outcomes + ACS enrichment · filters in sidebar · **Every tab includes source notes** "
        "(expanders and the **About** bibliography)."
    )

    if not CSV_PATH.exists():
        st.error(f"Missing CSV: {CSV_PATH}")
        st.stop()

    df_full = load()
    st.session_state.setdefault("f_party", sorted(df_full["Party Control"].dropna().unique().tolist()) if "Party Control" in df_full.columns else [])
    st.session_state.setdefault("f_mcd", ["Y", "N"])

    with st.sidebar:
        st.header("Filters")
        if "Party Control" in df_full.columns:
            parties = sorted(df_full["Party Control"].dropna().unique().tolist())
            st.session_state["f_party"] = st.multiselect("Party control", parties, default=parties)
        if "Medicaid expansion adopted (Y/N)" in df_full.columns:
            st.session_state["f_mcd"] = st.multiselect(
                "Medicaid expansion",
                ["Y", "N"],
                default=["Y", "N"],
            )
        st.divider()
        with st.expander("Data sources (quick reference)", expanded=False):
            st.markdown(
                "- **State panel:** `governence_data_enriched_acs2022.csv` (sheet + enrichment).\n"
                "- **ACS metrics:** " + ACS_CITATION + "\n"
                "- **Medicaid flag:** " + KFF_MEDICAID_CITATION + "\n"
                "- **Trends:** `us_national_timeseries.csv` (optional `source` / `note` columns per row).\n"
                "- **Violent crime (UCR):** FBI state rates (**"
                + UCR_VIOLENT_YEAR
                + "**) via [Wikipedia UCR table](https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_violent_crime_rate) "
                "(CIUS/FBI citations on that page); counts = rate × ACS population. Full wording in **About** and per-metric expanders.\n"
                "- **Incarceration:** Vera [*Incarceration Trends*](https://trends.vera.org/) state CSV — see **About**.\n"
                "- **Life expectancy:** " + LINK_LE_WIKI + " (" + LE_DATA_YEAR + " column) — see **About**.\n"
                "- **GDP (BEA):** requires `BEA_API_KEY` — " + LINK_BEA_API_SIGNUP + "\n"
                "- **AQI (EPA):** manual unless you extend `refresh_epa_aqi.py` — " + LINK_EPA_AIRDATA + "\n"
                "- **Quality / vintages:** `DATA_QUALITY.md`"
            )
        st.markdown("**Vision deck (static):** `RFRF_VISION_DECK.md` → export PDF/HTML with Marp.")
        st.markdown("**Data quality:** `DATA_QUALITY.md`")

    df = df_full.copy()
    if "Party Control" in df.columns and st.session_state.get("f_party"):
        df = df[df["Party Control"].isin(st.session_state["f_party"])]
    if "Medicaid expansion adopted (Y/N)" in df.columns and st.session_state.get("f_mcd"):
        df = df[df["Medicaid expansion adopted (Y/N)"].isin(st.session_state["f_mcd"])]

    st.subheader(f"Showing {len(df)} / {len(df_full)} states")

    metric_options = metric_defs(df)

    tab_ov, tab_map, tab_rank, tab_scatter, tab_corr, tab_pol, tab_tr, tab_tbl, tab_ab = st.tabs(
        [
            "Overview",
            "US map",
            "Rank states",
            "Compare metrics",
            "Correlation",
            "Policy vs outcomes",
            "Trends",
            "Full table",
            "About",
        ]
    )

    with tab_ov:
        c1, c2, c3, c4, c5 = st.columns(5)
        if "_poverty_pct" in df.columns:
            c1.metric("Median poverty % (states shown)", f"{df['_poverty_pct'].median():.2f}")
        if "_uninsured_pct" in df.columns:
            c2.metric("Median uninsured % (ACS)", f"{df['_uninsured_pct'].median():.2f}")
        if "_child_pov_pct" in df.columns:
            c3.metric("Median child poverty % (ACS)", f"{df['_child_pov_pct'].median():.2f}")
        if "_rent30" in df.columns:
            c4.metric("Median rent burden 30%+ %", f"{df['_rent30'].median():.2f}")
        if "_median_income" in df.columns:
            c5.metric("Median median income ($)", f"{df['_median_income'].median():,.0f}")
        st.info(
            "Overview uses **medians across filtered states**. Adjust sidebar filters to compare party or Medicaid groups."
        )
        with st.expander("Sources — overview metrics", expanded=False):
            parts = []
            if "_poverty_pct" in df.columns:
                parts.append(cite_internal("_poverty_pct"))
            if "_uninsured_pct" in df.columns:
                parts.append(cite_internal("_uninsured_pct"))
            if "_child_pov_pct" in df.columns:
                parts.append(cite_internal("_child_pov_pct"))
            if "_rent30" in df.columns:
                parts.append(cite_internal("_rent30"))
            if "_median_income" in df.columns:
                parts.append(cite_internal("_median_income"))
            st.markdown("\n\n---\n\n".join(parts))

    with tab_map:
        col = st.selectbox("Metric (map)", metric_options, format_func=lambda x: x[1], key="mapm")
        good_higher = ("_sick_ordinal", "_medicaid_n", "_broadband", "_le", "_le_f", "_le_m", "_median_income")
        color_seq = "Viridis" if col[0] in good_higher else "RdYlGn_r"
        sub = df.dropna(subset=["STUSPS", col[0]])
        if len(sub) == 0:
            st.info("No numeric data for this metric with current filters.")
        else:
            fig = px.choropleth(
                sub,
                locations="STUSPS",
                locationmode="USA-states",
                color=col[0],
                scope="usa",
                color_continuous_scale=color_seq,
                labels={col[0]: col[1]},
                title=f"{col[1]} by state",
            )
            fig.update_layout(height=520, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with st.expander(f"Source — {col[1]}", expanded=False):
            st.markdown(cite_internal(col[0]))

    with tab_rank:
        col = st.selectbox("Metric (bars)", metric_options, format_func=lambda x: x[1], key="barm")
        n = st.slider("Top / bottom N", 5, 25, 10)
        s = df.dropna(subset=[col[0]]).sort_values(col[0])
        low, high = s.head(n), s.tail(n)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"Lowest {n}")
            st.plotly_chart(
                px.bar(low, x=col[0], y="state_name", orientation="h", title=col[1]),
                use_container_width=True,
            )
        with c2:
            st.subheader(f"Highest {n}")
            st.plotly_chart(
                px.bar(high, x=col[0], y="state_name", orientation="h", title=col[1]),
                use_container_width=True,
            )
        with st.expander(f"Source — {col[1]}", expanded=False):
            st.markdown(cite_internal(col[0]))

    with tab_scatter:
        c1 = st.selectbox("X axis", metric_options, format_func=lambda x: x[1], key="sx")
        c2 = st.selectbox(
            "Y axis",
            metric_options,
            index=min(1, len(metric_options) - 1),
            format_func=lambda x: x[1],
            key="sy",
        )
        hue = "Party Control" if "Party Control" in df.columns else None
        sub = df.dropna(subset=[c1[0], c2[0]])
        st.plotly_chart(
            px.scatter(
                sub,
                x=c1[0],
                y=c2[0],
                hover_name="state_name",
                color=hue,
                labels={c1[0]: c1[1], c2[0]: c2[1]},
                title=f"{c1[1]} vs {c2[1]}",
            ),
            use_container_width=True,
        )
        with st.expander("Sources — scatter axes", expanded=False):
            st.markdown("**X:** " + cite_internal(c1[0]) + "\n\n---\n\n**Y:** " + cite_internal(c2[0]))
        if hue:
            with st.expander(f"Source — {hue}", expanded=False):
                st.markdown(cite_column(hue))

    with tab_corr:
        st.markdown(
            "### Which metrics move together? (Pearson **r**, **R²**, **p**)\n"
            "State-level cross-section (**n = number of states after filters**). "
            "**R²** here is **r²** (share of variance explained by linear fit of one variable on the other, symmetric). "
            "**p** is two-sided for **H₀: ρ = 0**. Many tests run at once → treat **p** as exploratory unless you adjust for multiplicity.\n\n"
            + PEARSON_METHOD_CITATION
        )
        corr_candidates = [
            "_median_income",
            "_poverty_pct",
            "_uninsured_pct",
            "_child_pov_pct",
            "_rent30",
            "_rent50",
            "_snap",
            "_broadband",
            "_no_internet",
            "_gini",
            "_le",
            "_md_per_100k",
            "_violent_per_100k",
            "_incarceration_pct",
            "_median_aqi",
            "_sick_ordinal",
            "_medicaid_n",
        ]
        corr_cols = [c for c in corr_candidates if c in df.columns]
        labels = {c: t for c, t in metric_defs(df)}
        short = []
        for c in corr_cols:
            lab = labels.get(c, c)
            if len(lab) > 28:
                lab = lab[:26] + "…"
            short.append(lab)
        if len(corr_cols) < 2:
            st.warning("Need at least two numeric columns for correlation.")
        else:
            r_df, r2_df, p_df = correlation_matrices(df, corr_cols)
            r_disp = r_df.copy()
            r2_disp = r2_df.copy()
            p_disp = p_df.copy()
            r_disp.index = r_disp.columns = short
            r2_disp.index = r2_disp.columns = short
            p_disp.index = p_disp.columns = short

            which = st.radio("Heatmap", ["Pearson r", "R² (r²)", "p-value"], horizontal=True, key="corrwhich")
            if which == "Pearson r":
                z = r_disp
                zmin, zmax = -1.0, 1.0
                colorscale = "RdBu_r"
                fmt = ".2f"
            elif which == "R² (r²)":
                z = r2_disp
                zmin, zmax = 0.0, 1.0
                colorscale = "YlOrRd"
                fmt = ".2f"
            else:
                z = p_disp
                zmin, zmax = 0.0, 1.0
                colorscale = "Reds"
                fmt = ".3f"
            fig = go.Figure(
                data=go.Heatmap(
                    z=z.values,
                    x=z.columns.tolist(),
                    y=z.index.tolist(),
                    zmin=zmin,
                    zmax=zmax,
                    colorscale=colorscale,
                    text=np.vectorize(lambda v: f"{v:{fmt}}" if np.isfinite(v) else "")(z.values),
                    texttemplate="%{text}",
                    hoverongaps=False,
                )
            )
            fig.update_layout(
                title=which + " (states shown)",
                height=max(520, 40 * len(corr_cols)),
                xaxis_tickangle=-45,
                margin=dict(l=120, r=40, t=60, b=160),
            )
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("Sources — variables in correlation matrix", expanded=False):
                seen: set[str] = set()
                blocks = []
                for c in corr_cols:
                    if c in seen:
                        continue
                    seen.add(c)
                    blocks.append(f"**{labels.get(c, c)}** — {cite_internal(c)}")
                st.markdown("\n\n---\n\n".join(blocks))

    with tab_pol:
        st.markdown(
            "**Policy vs outcomes** — compare distributions by Medicaid expansion (**Y/N** column merged from enrichment)."
        )
        with st.expander("Citation — Medicaid expansion (Y/N)", expanded=False):
            st.markdown(KFF_MEDICAID_CITATION)
        ycol = st.selectbox("Outcome metric", metric_options, format_func=lambda x: x[1], key="pol_y")
        if "Medicaid expansion adopted (Y/N)" not in df.columns or ycol[0] not in df.columns:
            st.warning("Need Medicaid column and outcome column.")
        else:
            sub = df.dropna(subset=[ycol[0]])
            fig = px.box(
                sub,
                x="Medicaid expansion adopted (Y/N)",
                y=ycol[0],
                color="Medicaid expansion adopted (Y/N)",
                points="all",
                hover_name="state_name",
                title=f"{ycol[1]} by Medicaid expansion status",
            )
            st.plotly_chart(fig, use_container_width=True)
        with st.expander(f"Source — outcome: {ycol[1]}", expanded=False):
            st.markdown(cite_internal(ycol[0]))

        if "_sick_ordinal" in df.columns and "_uninsured_pct" in df.columns:
            st.markdown(
                "**Sick-leave strength (ordinal)** vs uninsured — heuristic from policy text; refine in CSV if needed."
            )
            sub2 = df.dropna(subset=["_sick_ordinal", "_uninsured_pct"])
            st.plotly_chart(
                px.scatter(
                    sub2,
                    x="_sick_ordinal",
                    y="_uninsured_pct",
                    hover_name="state_name",
                    color="Party Control" if "Party Control" in sub2.columns else None,
                    labels={"_sick_ordinal": "Sick leave ordinal", "_uninsured_pct": "Uninsured %"},
                ),
                use_container_width=True,
            )
            with st.expander("Sources — sick leave plot", expanded=False):
                st.markdown(
                    "**Ordinal:** "
                    + cite_internal("_sick_ordinal")
                    + "\n\n---\n\n**Uninsured %:** "
                    + cite_internal("_uninsured_pct")
                )

    with tab_tr:
        st.markdown(
            "### National / longitudinal\n"
            "Edit **`us_national_timeseries.csv`** (year + median columns) as you add historical exports. "
            "Or upload a CSV with at least `year` and one numeric column.\n\n"
            "**Citation:** each row may include **`source`** and **`note`** columns — shown below the table when present. "
            "National medians shipped with the repo were computed from the enriched state panel (see `source` column in that file)."
        )
        up = st.file_uploader("Upload timeseries CSV", type=["csv"])
        ts = None
        if up is not None:
            ts = pd.read_csv(up)
        elif NATIONAL_TS_PATH.exists():
            ts = pd.read_csv(NATIONAL_TS_PATH)
        if ts is None or ts.empty:
            st.info("No timeseries file yet. Copy `us_national_timeseries.csv` and add more `year` rows.")
        else:
            st.dataframe(ts, use_container_width=True)
            meta_cols = [c for c in ("year", "source", "note") if c in ts.columns]
            if meta_cols and ({"source", "note"} & set(ts.columns)):
                st.markdown("##### Row attribution (`year`, `source`, `note`)")
                st.dataframe(ts[meta_cols], use_container_width=True)
            skip = {"year", "source", "note"}
            num_cols = []
            for c in ts.columns:
                if c in skip:
                    continue
                if pd.to_numeric(ts[c], errors="coerce").notna().any():
                    num_cols.append(c)
            if "year" in ts.columns and len(num_cols) >= 1:
                yc = st.selectbox("Plot column", num_cols, key="tscol")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=ts["year"], y=ts[yc], mode="lines+markers", name=yc))
                fig.update_layout(title=f"US-level: {yc}", xaxis_title="Year", height=400)
                st.plotly_chart(fig, use_container_width=True)
                with st.expander(f"Source — plotted series `{yc}`", expanded=False):
                    st.markdown(
                        "Plotted values come from the uploaded file or **`us_national_timeseries.csv`**. "
                        "Check the **`source`** column in that CSV for the authoritative provenance of each `year` row "
                        "(e.g. state-panel medians vs. external series)."
                    )
            else:
                st.warning("Need a `year` column and at least one numeric column.")

    with tab_tbl:
        q = st.text_input("Filter state name contains")
        show = df
        if q.strip():
            show = df[df["state_name"].str.contains(q.strip(), case=False, na=False)]
        st.dataframe(show, use_container_width=True, height=520)
        with st.expander("Column-by-column citations (all fields in table)", expanded=False):
            st.markdown(
                "Provenance for **every** column in the filtered dataframe (including derived `_` fields used in charts)."
            )
            st.dataframe(citations_table_for_df(show), use_container_width=True, height=420)

    with tab_ab:
        st.markdown(
            """
### Bundles in this folder

| Artifact | Purpose |
|----------|---------|
| `governence_data_enriched_acs2022.csv` | State panel + ACS columns |
| `governence_data - Sheet1.csv` | Editable source (re-run `enrich_governance_csv.py` after edits) |
| `RFRF_VISION_DECK.md` | Marp slides: manifesto + flywheel — export to PDF/HTML |
| `DATA_QUALITY.md` | Known fixes and validation backlog |
| `DATA_DICTIONARY_governance_enrichment.md` | Column definitions for ACS merge |
| `refresh_violent_crime_ucr.py` | FBI **UCR** violent-crime rates (Wikipedia CIUS table) + estimated counts |
| `refresh_vera_incarceration.py` | Vera **Incarceration Trends** state totals + rate (% of residents) |
| `refresh_life_expectancy.py` | Wikipedia life-expectancy table (**2021** column → legacy `Life Expectancy 2019*` headers) |
| `refresh_bea_gdp.py` | **BEA** state GDP (needs `BEA_API_KEY`) |
| `refresh_epa_aqi.py` | EPA AQI — placeholder / documentation (no keyless feed) |
| `us_national_timeseries.csv` | Add rows per year for the **Trends** tab |

### Bibliography / how to cite this dashboard

**American Community Survey (ACS)** — U.S. Census Bureau. *ACS 2024 5-year estimates* (2020–2024) via [Census API](https://api.census.gov/data/2024/acs/acs5.html). Detail tables **B27001**, **B25070**, **B22001**, **B28002**, **B17001**, **B19013**, **B01003**, **B19083** and subject table **S1501** (educational attainment) as implemented in `enrich_governance_csv.py`. [S1501 group definition](https://api.census.gov/data/2024/acs/acs5/subject/groups/S1501.html).

**Medicaid expansion status** — verify against [KFF — Status of State Medicaid Expansion Decisions](https://www.kff.org/medicaid/status-of-state-medicaid-expansion-decisions/); app uses a rule-based merge documented in `enrich_governance_csv.py`.

**Violent crime (state rate and estimated count)** — FBI **UCR** figures as compiled in Wikipedia’s [*List of U.S. states and territories by violent crime rate*](https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_violent_crime_rate) (**2024** column when available); counts use ACS population in the same row. Refreshed by `refresh_violent_crime_ucr.py` (also invoked at the end of `enrich_governance_csv.py`). Re-verify on the [FBI Crime Data Explorer](https://cde.ucr.cjis.gov/) before publication.

**Incarceration** — [Vera Institute of Justice — Incarceration Trends](https://trends.vera.org/) state file ([CSV](https://raw.githubusercontent.com/vera-institute/incarceration_trends/main/incarceration_trends_state.csv)); compare with [BJS](https://bjs.ojp.gov/).

**Life expectancy** — Wikipedia [*List of U.S. states and territories by life expectancy*](https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_life_expectancy) (**2021** column in this build); verify with [CDC NCHS](https://www.cdc.gov/nchs/life-expectancy.htm) and [IHME](https://www.healthdata.org/research-analysis/gbd).

**State GDP** — [BEA GDP by state](https://www.bea.gov/data/gdp/gdp-state); refresh script needs a free [BEA API User ID](https://apps.bea.gov/API/signup/index.cfm) (`BEA_API_KEY`).

**Correlations** — `scipy.stats.pearsonr`; interpret **R²** as **r²**; **p-values** are exploratory across many pairs unless multiplicity-adjusted.

**Still mostly manual in the CSV** (see citations + `DATA_QUALITY.md`): **physicians per 100k** ([HRSA AHRF](https://data.hrsa.gov/topics/health-workforce/ahrf), [AAMC](https://www.aamc.org/data-reports/workforce/interactive-data/active-physicians-state-level-supply-and-specialty-data)), **K–12 education funding** ([NCES](https://nces.ed.gov/programs/school_finance)), **EPA AQI day-type summaries** ([EPA AirData](https://www.epa.gov/outdoor-air-quality-data)), and **political / legislature** fields ([NGA](https://www.nga.org/governors/), [Open States](https://openstates.org/), [Ballotpedia](https://ballotpedia.org/Main_Page)).

**National trends file** — `us_national_timeseries.csv`; use **`source`** / **`note`** columns per row for attribution.

### Portfolio vision (longer memo)

See `RFRF_VISION_DECK.md` in this repo for the narrative north-star and flywheel.
            """
        )


if __name__ == "__main__":
    main()
