# Security and privacy (public repo)

## What must never be committed

- **API keys** — especially `BEA_API_KEY` (BEA User ID). Use environment variables or `.env` (gitignored); see `.env.example`.
- **Streamlit secrets** — `.streamlit/secrets.toml` (gitignored).
- **Personal machine paths** — avoid `/Users/...` or private project folders in docs.

## APIs used by this project

| Source | Key required? | How to configure |
|--------|----------------|------------------|
| U.S. Census ACS | No (public API) | — |
| BEA regional GDP | Yes (free signup) | `BEA_API_KEY` env var |
| Wikipedia / public pages (scrapers) | No | — |

Census and refresh scripts do **not** embed keys in source code.

## Data in CSV files

Committed CSVs contain **aggregate state-level** statistics and **public officials** (governors, legislature counts). They do not include individual citizen records, emails, or account identifiers.

## Before publishing or after cloning

```bash
# From repo root — should print nothing sensitive
rg -i 'BEA_API_KEY\s*=\s*[^$\s]|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}' --glob '!.venv' --glob '!.git'
```

If you ever committed a key, rotate it at the provider and purge git history (e.g. `git filter-repo`).
