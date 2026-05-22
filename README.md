# Governence dashboard

State-level **governance + outcomes** data for Reasonable Future–style arguments, plus a **Streamlit** explorer and a **Marp** vision deck.

## Evidence app (Streamlit)

```bash
git clone https://github.com/goldsteinmarcmd/governance-dashboard.git
cd governance-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dashboard.txt
streamlit run app.py
```

Tabs: **Overview** (medians, including **median income**) · **US map** · **Rank states** · **Compare metrics** · **Correlation** (heatmaps of **Pearson r**, **R²**, **p-values** across metrics) · **Policy vs outcomes** · **Trends** · **Full table** · **About**.

After editing `governence_data - Sheet1.csv`:

```bash
python3 enrich_governance_csv.py
```

## Vision deck (Marp)

```bash
npx --yes @marp-team/marp-cli RFRF_VISION_DECK.md -o RFRF_VISION_DECK.pdf
# or HTML
npx --yes @marp-team/marp-cli RFRF_VISION_DECK.md -o RFRF_VISION_DECK.html
```

Or use the **Marp for VS Code** extension for preview.

## Files

| File | Role |
|------|------|
| `governence_data - Sheet1.csv` | Editable source |
| `governence_data_enriched_acs2022.csv` | Source + ACS columns |
| `enrich_governance_csv.py` | Regenerate enriched CSV (Census API) |
| `DATA_DICTIONARY_governance_enrichment.md` | ACS column definitions |
| `DATA_QUALITY.md` | Validation notes |
| `RFRF_VISION_DECK.md` | Marp slides |
| `us_national_timeseries.csv` | Add `year` rows for Trends tab |

## Secrets (local only)

- **Never commit** `.env`, `.streamlit/secrets.toml`, or API keys.
- Optional **BEA GDP refresh**: copy `.env.example` → `.env` and set `BEA_API_KEY` (free [BEA API signup](https://apps.bea.gov/API/signup/index.cfm)). The dashboard runs without it; GDP refresh scripts need it.
- See [SECURITY.md](SECURITY.md) for the full checklist.

## Longer written vision

See `RFRF_VISION_DECK.md` (and exported PDF/HTML if you generate them locally).
