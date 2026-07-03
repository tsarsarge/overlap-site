#!/usr/bin/env python3
"""
Overlap — ETF data pipeline (v1)
================================
Pulls real ETF data (top holdings, sector weights, expense ratios) via
Yahoo Finance and writes data.json, which the Overlap site loads at startup.

Setup (once):     pip install yfinance
Run:              python etf_pipeline.py
Deploy:           put data.json in the same folder as index.html and redeploy.

v1 honesty notes:
- Top-10 holdings + sector weights come from Yahoo (free, no key, reliable).
- Full-holdings overlap % can't be computed from top-10 alone, so the site
  keeps its curated overlap table for famous pairs and estimates the rest.
  v2 (issuer CSVs / SEC N-PORT) upgrades that to exact overlap math.
- International/bond/commodity funds keep the site's asset-class model
  (their equity-sector split isn't what diversification math needs there).
"""

import json
import sys
import time
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    sys.exit("yfinance not installed. Run:  pip install yfinance")

# Tickers to fetch: everything the site knows, plus popular extras.
TICKERS = {
    # ticker: asset class label used by the site
    "VOO": "US Large Cap", "SPY": "US Large Cap", "IVV": "US Large Cap",
    "SPLG": "US Large Cap", "VTI": "US Total Market", "QQQ": "US Large Growth",
    "QQQM": "US Large Growth", "VUG": "US Large Growth", "VTV": "US Large Value",
    "SCHD": "US Dividend", "VIG": "US Dividend", "VYM": "US Dividend",
    "DGRO": "US Dividend", "IWM": "US Small Cap", "DIA": "US Large Cap",
    "XLK": "US Sector — Tech", "VGT": "US Sector — Tech", "SMH": "US Sector — Semis",
    "XLF": "US Sector — Financials", "XLE": "US Sector — Energy",
    "XLV": "US Sector — Healthcare", "VXUS": "International", "VEA": "International",
    "VWO": "International", "IEFA": "International", "BND": "Bonds", "AGG": "Bonds",
    "VNQ": "US Sector — REIT", "GLD": "Commodity", "ARKK": "US Thematic Growth",
    "JEPI": "US Covered Call", "JEPQ": "US Covered Call", "VT": "Global",
    "SCHB": "US Total Market", "SCHX": "US Large Cap",
}

# Funds where the site's asset-class model beats Yahoo's equity-sector split.
SKIP_SECTOR_WEIGHTS = {"VXUS", "VEA", "VWO", "IEFA", "BND", "AGG", "GLD", "VT"}

# Yahoo sector keys -> site sector labels
SECTOR_MAP = {
    "technology": "Technology",
    "financial_services": "Financials",
    "healthcare": "Healthcare",
    "consumer_cyclical": "Consumer Disc.",
    "communication_services": "Comm. Services",
    "industrials": "Industrials",
    "consumer_defensive": "Consumer Staples",
    "energy": "Energy",
    "utilities": "Utilities",
    "realestate": "Real Estate",
    "basic_materials": "Materials",
}


def get_expense_ratio(ticker_obj):
    """Try several fields; Yahoo reports it inconsistently. Returns % or None."""
    try:
        info = ticker_obj.info or {}
    except Exception:
        info = {}
    for key in ("netExpenseRatio", "annualReportExpenseRatio", "expenseRatio"):
        v = info.get(key)
        if v is None:
            continue
        v = float(v)
        # Some fields come as 0.0003, some as 0.03 (percent). Normalize to percent.
        if v < 0.005:
            v *= 100
        if 0 < v < 3:
            return round(v, 2)
    return None


def fetch_one(ticker, cls):
    t = yf.Ticker(ticker)
    out = {"cls": cls}

    try:
        name = (t.info or {}).get("longName") or (t.info or {}).get("shortName")
        if name:
            out["n"] = name.replace(" ETF", "").strip()
    except Exception:
        pass

    er = get_expense_ratio(t)
    if er is not None:
        out["er"] = er

    try:
        fd = t.funds_data

        # sector weights
        if ticker not in SKIP_SECTOR_WEIGHTS:
            sw_raw = fd.sector_weightings or {}
            sw = {}
            for k, v in sw_raw.items():
                label = SECTOR_MAP.get(k)
                if label and v and v > 0.001:
                    sw[label] = round(float(v) * 100, 1)
            if sw:
                out["sw"] = sw

        # top holdings (DataFrame: index=symbol, col 'Holding Percent' 0-1)
        th = fd.top_holdings
        if th is not None and len(th):
            h = {}
            for sym, row in th.iterrows():
                pct = float(row.get("Holding Percent", 0)) * 100
                if pct > 0.1:
                    h[str(sym).replace("-", ".")] = round(pct, 1)
            if h:
                out["h"] = h
    except Exception as e:
        print(f"  ! funds_data failed for {ticker}: {e}")

    return out


def main():
    result = {"generated": datetime.now(timezone.utc).isoformat(), "etfs": {}}
    ok, bad = 0, []
    for i, (ticker, cls) in enumerate(TICKERS.items(), 1):
        print(f"[{i}/{len(TICKERS)}] {ticker} ...", flush=True)
        try:
            data = fetch_one(ticker, cls)
            # only ship entries that actually carry real data
            if any(k in data for k in ("er", "sw", "h")):
                result["etfs"][ticker] = data
                ok += 1
            else:
                bad.append(ticker)
        except Exception as e:
            print(f"  ! {ticker} failed entirely: {e}")
            bad.append(ticker)
        time.sleep(1.0)  # be polite to Yahoo

    with open("data.json", "w") as f:
        json.dump(result, f, separators=(",", ":"))

    print(f"\nWrote data.json — {ok} funds with real data" +
          (f", skipped: {', '.join(bad)}" if bad else ""))
    print("Next: put data.json next to index.html and redeploy.")


if __name__ == "__main__":
    main()
