# Overlap — Real ETF Data Setup

Three steps to real fund data on your live site.

## 1. Run the pipeline (on your computer)

You need Python 3 (macOS has it built in). In Terminal:

```
pip install yfinance
python etf_pipeline.py
```

Takes about a minute (it pauses politely between funds). It prints progress
and finishes with a `data.json` file: real top-10 holdings, sector weights,
and expense ratios for ~35 popular ETFs, pulled from Yahoo Finance.

## 2. Deploy it

Put `data.json` in the same folder as `index.html` and re-drop the folder on
Netlify. That's it. The site detects the file automatically:

- Fund data (holdings, sectors, fees) switches from built-in samples to real.
- The black masthead strip changes from "Fund data is sample data..." to
  **"Fund data updated July 2, 2026"** — your visitors can see it's fresh.
- New funds in data.json (VYM, VGT, JEPQ, etc.) appear in the Compare dropdowns.
- If data.json is ever missing or broken, the site quietly falls back to
  built-in data. Nothing breaks.

## 3. Optional: automate with GitHub Actions (free)

Once the site lives in a GitHub repo (connect Netlify to the repo instead of
drag-and-drop), add this file as `.github/workflows/data.yml` and the data
refreshes itself every night:

```yaml
name: Refresh ETF data
on:
  schedule:
    - cron: "30 9 * * 1-5"   # 9:30 UTC, weekdays
  workflow_dispatch:          # manual run button
jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install yfinance
      - run: python etf_pipeline.py
      - name: Commit updated data
        run: |
          git config user.name "data-bot"
          git config user.email "bot@users.noreply.github.com"
          git add data.json
          git diff --cached --quiet || git commit -m "Nightly ETF data refresh"
          git push
```

Netlify redeploys automatically on every commit, so the site updates itself.

## What's real vs. still curated (v1)

| Data | Source | Status |
|------|--------|--------|
| Expense ratios | Yahoo Finance | **Real** |
| Sector weights | Yahoo Finance | **Real** |
| Top-10 holdings | Yahoo Finance | **Real** |
| Fund overlap % | Curated table + estimates | Famous pairs hand-verified; exact math needs full holdings |
| Market Pulse volume/chatter | Simulated | Needs its own feed (v2) |

**v2 upgrade path:** issuer CSVs (Vanguard/iShares/State Street publish full
daily holdings) or SEC N-PORT filings give complete holdings, which makes
every overlap percentage exactly computable. That's the moat — build it when
the site has users.

## To add more ETFs

Edit the `TICKERS` dictionary at the top of `etf_pipeline.py` — add the
ticker and an asset-class label (copy the style of an existing similar fund).
Re-run, redeploy.
