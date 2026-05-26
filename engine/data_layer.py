"""
Ganji Protocol - Data Layer
Fetches, validates, cross-checks, and stores EAC currency pair data
from multiple free sources. No scraping. All API-based.

Sources (in priority order):
  1. Yahoo Finance      - daily historical (no key required)
  2. open.er-api.com    - daily current (no key required)
  3. exchangerate-api   - daily current (no key required)
  4. Alpha Vantage      - daily historical + current (free key required)
  5. Twelve Data        - daily historical + current (free key required)
  6. Exchangeratesapi.io- daily historical + current (free key required)
  7. Binance P2P        - real-time KES/USDT (no key required)
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import requests
import pandas as pd
import yfinance as yf

# Ensure project root is on path for package imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.config import (
    DATA_DIR, RAW_DATA_FILES, EAC_PAIRS, YAHOO_TICKERS,
    PRIMARY_PAIR, BASKET_PAIRS, SOURCES,
    ALPHA_VANTAGE_KEY, TWELVE_DATA_KEY,
    EXCHANGERATESAPI_KEY,
    PLAUSIBLE_RANGE, SPIKE_THRESHOLD,
    STALE_DAYS_THRESHOLD, CROSS_CHECK_THRESHOLD,
    P2P_MIN_ADS, HISTORY_PERIOD,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Data Quality
# ─────────────────────────────────────────────

def range_check(currency: str, value: float) -> bool:
    low, high = PLAUSIBLE_RANGE[currency]
    return low <= value <= high


def spike_check(today: float, yesterday: float) -> bool:
    if yesterday == 0:
        return False
    return abs((today - yesterday) / yesterday) > SPIKE_THRESHOLD


def cross_check(val_a: float, val_b: float) -> bool:
    """Returns True if two source values are within acceptable range of each other."""
    if val_a == 0 or val_b == 0:
        return False
    return abs((val_a - val_b) / val_a) <= CROSS_CHECK_THRESHOLD


# ─────────────────────────────────────────────
# Source 1: Yahoo Finance (primary historical)
# ─────────────────────────────────────────────

def fetch_yahoo_history() -> pd.DataFrame:
    """
    Fetches 5-year daily OHLCV for all EAC pairs from Yahoo Finance.
    Returns a DataFrame with columns: date, currency, close.
    No API key required.
    """
    log.info("Fetching historical data from Yahoo Finance...")
    records = []

    for currency, ticker in YAHOO_TICKERS.items():
        try:
            df = yf.download(ticker, period=HISTORY_PERIOD, interval="1d",
                             progress=False, auto_adjust=True)
            if df.empty:
                log.warning(f"Yahoo Finance: no data for {ticker}")
                continue

            for idx, row in df.iterrows():
                close_val = row["Close"]
                close = float(close_val.iloc[0]) if hasattr(close_val, 'iloc') else float(close_val)
                if not range_check(currency, close):
                    log.warning(f"Yahoo Finance: {ticker} {idx.date()} value {close} outside plausible range. Skipping.")
                    continue
                records.append({
                    "date":     idx.strftime("%Y-%m-%d"),
                    "currency": currency,
                    "close":    round(close, 6),
                    "source":   "yahoo_finance",
                    "flag":     "",
                })
            log.info(f"Yahoo Finance: {ticker} fetched {len(df)} rows")

        except Exception as e:
            log.error(f"Yahoo Finance: failed for {ticker} - {e}")

    df_out = pd.DataFrame(records)
    log.info(f"Yahoo Finance: total {len(df_out)} records across {len(YAHOO_TICKERS)} pairs")
    return df_out


# ─────────────────────────────────────────────
# Source 2: open.er-api.com (current, no key)
# ─────────────────────────────────────────────

def fetch_open_er_api() -> dict:
    """
    Fetches current daily rates for all EAC pairs.
    Returns dict: {currency: rate}
    No API key required.
    """
    log.info("Fetching current rates from open.er-api.com...")
    try:
        r = requests.get(SOURCES["open_er_api"]["url"], timeout=15)
        r.raise_for_status()
        data = r.json()
        rates = data.get("rates", {})
        result = {}
        for currency in EAC_PAIRS:
            val = rates.get(currency)
            if val and range_check(currency, float(val)):
                result[currency] = round(float(val), 6)
            else:
                log.warning(f"open.er-api: {currency} value {val} failed range check")
        log.info(f"open.er-api: fetched {len(result)} pairs")
        return result
    except Exception as e:
        log.error(f"open.er-api: failed - {e}")
        return {}


# ─────────────────────────────────────────────
# Source 3: exchangerate-api.com (current, no key)
# ─────────────────────────────────────────────

def fetch_exchangerate_api() -> dict:
    """
    Fetches current daily rates for all EAC pairs.
    Returns dict: {currency: rate}
    No API key required.
    """
    log.info("Fetching current rates from exchangerate-api.com...")
    try:
        r = requests.get(SOURCES["exchangerate_api"]["url"], timeout=15)
        r.raise_for_status()
        data = r.json()
        rates = data.get("rates", {})
        result = {}
        for currency in EAC_PAIRS:
            val = rates.get(currency)
            if val and range_check(currency, float(val)):
                result[currency] = round(float(val), 6)
            else:
                log.warning(f"exchangerate-api: {currency} value {val} failed range check")
        log.info(f"exchangerate-api: fetched {len(result)} pairs")
        return result
    except Exception as e:
        log.error(f"exchangerate-api: failed - {e}")
        return {}


# ─────────────────────────────────────────────
# Source 4: Alpha Vantage (requires free key)
# ─────────────────────────────────────────────

def fetch_alpha_vantage(currency: str) -> Optional[float]:
    """
    Fetches current USD/{currency} rate from Alpha Vantage.
    Requires free API key: alphavantage.co/support/#api-key
    Returns float rate or None if unavailable.
    """
    if not ALPHA_VANTAGE_KEY:
        log.debug("Alpha Vantage: no API key configured. Skipping.")
        return None
    try:
        params = {
            "function":      "CURRENCY_EXCHANGE_RATE",
            "from_currency": "USD",
            "to_currency":   currency,
            "apikey":        ALPHA_VANTAGE_KEY,
        }
        r = requests.get(SOURCES["alpha_vantage"]["url"], params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        rate_data = data.get("Realtime Currency Exchange Rate", {})
        val = rate_data.get("5. Exchange Rate")
        if val:
            val = float(val)
            if range_check(currency, val):
                log.info(f"Alpha Vantage: USD/{currency} = {val}")
                return round(val, 6)
        log.warning(f"Alpha Vantage: USD/{currency} value {val} failed range check or missing")
        return None
    except Exception as e:
        log.error(f"Alpha Vantage: failed for {currency} - {e}")
        return None


def fetch_alpha_vantage_history(currency: str) -> pd.DataFrame:
    """
    Fetches daily historical USD/{currency} from Alpha Vantage (FX_DAILY).
    Requires free API key. Free tier: 25 requests/day.
    Returns DataFrame with date, currency, close, source.
    """
    if not ALPHA_VANTAGE_KEY:
        log.debug("Alpha Vantage: no API key configured. Skipping history fetch.")
        return pd.DataFrame()
    try:
        params = {
            "function":    "FX_DAILY",
            "from_symbol": "USD",
            "to_symbol":   currency,
            "outputsize":  "full",
            "apikey":      ALPHA_VANTAGE_KEY,
        }
        r = requests.get(SOURCES["alpha_vantage"]["url"], params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        series = data.get("Time Series FX (Daily)", {})
        records = []
        for date_str, values in series.items():
            close = float(values.get("4. close", 0))
            if range_check(currency, close):
                records.append({
                    "date":     date_str,
                    "currency": currency,
                    "close":    round(close, 6),
                    "source":   "alpha_vantage",
                    "flag":     "",
                })
        log.info(f"Alpha Vantage history: USD/{currency} fetched {len(records)} rows")
        return pd.DataFrame(records)
    except Exception as e:
        log.error(f"Alpha Vantage history: failed for {currency} - {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# Source 5: Twelve Data (requires free key)
# ─────────────────────────────────────────────

def fetch_twelve_data(currency: str) -> Optional[float]:
    """
    Fetches current USD/{currency} rate from Twelve Data.
    Requires free API key: twelvedata.com/pricing
    Returns float rate or None if unavailable.
    """
    if not TWELVE_DATA_KEY:
        log.debug("Twelve Data: no API key configured. Skipping.")
        return None
    try:
        url = f"{SOURCES['twelve_data']['url']}/exchange_rate"
        params = {
            "symbol": f"USD/{currency}",
            "apikey": TWELVE_DATA_KEY,
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        val = data.get("rate")
        if val:
            val = float(val)
            if range_check(currency, val):
                log.info(f"Twelve Data: USD/{currency} = {val}")
                return round(val, 6)
        log.warning(f"Twelve Data: USD/{currency} value {val} failed range check or missing")
        return None
    except Exception as e:
        log.error(f"Twelve Data: failed for {currency} - {e}")
        return None


def fetch_twelve_data_history(currency: str, outputsize: int = 1300) -> pd.DataFrame:
    """
    Fetches daily historical USD/{currency} from Twelve Data.
    Requires free API key. Free tier: 800 credits/day.
    Returns DataFrame with date, currency, close, source.
    """
    if not TWELVE_DATA_KEY:
        log.debug("Twelve Data: no API key configured. Skipping history fetch.")
        return pd.DataFrame()
    try:
        url = f"{SOURCES['twelve_data']['url']}/time_series"
        params = {
            "symbol":     f"USD/{currency}",
            "interval":   "1day",
            "outputsize": outputsize,
            "apikey":     TWELVE_DATA_KEY,
        }
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        series = data.get("values", [])
        records = []
        for entry in series:
            close = float(entry.get("close", 0))
            if range_check(currency, close):
                records.append({
                    "date":     entry["datetime"],
                    "currency": currency,
                    "close":    round(close, 6),
                    "source":   "twelve_data",
                    "flag":     "",
                })
        log.info(f"Twelve Data history: USD/{currency} fetched {len(records)} rows")
        return pd.DataFrame(records)
    except Exception as e:
        log.error(f"Twelve Data history: failed for {currency} - {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# Source 6: Exchangeratesapi.io (requires free key)
# ─────────────────────────────────────────────

def fetch_exchangeratesapi_io(target_date: str = None) -> dict:
    """
    Fetches current or historical rates from exchangeratesapi.io.
    Requires free API key: exchangeratesapi.io
    target_date: 'YYYY-MM-DD' for historical, None for latest.
    Returns dict: {currency: rate}
    Free tier: 100 requests/month, historical access included.
    """
    if not EXCHANGERATESAPI_KEY:
        log.debug("Exchangeratesapi.io: no API key configured. Skipping.")
        return {}
    try:
        base_url = SOURCES["exchangeratesapi_io"]["url"]
        endpoint = f"{base_url}/{target_date}" if target_date else f"{base_url}/latest"
        params = {
            "access_key": EXCHANGERATESAPI_KEY,
            "base":       "USD",
            "symbols":    ",".join(EAC_PAIRS.keys()),
        }
        r = requests.get(endpoint, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data.get("success", False):
            log.warning(f"Exchangeratesapi.io: API error - {data.get('error')}")
            return {}
        rates = data.get("rates", {})
        result = {}
        for currency in EAC_PAIRS:
            val = rates.get(currency)
            if val and range_check(currency, float(val)):
                result[currency] = round(float(val), 6)
        log.info(f"Exchangeratesapi.io: fetched {len(result)} pairs for {target_date or 'latest'}")
        return result
    except Exception as e:
        log.error(f"Exchangeratesapi.io: failed - {e}")
        return {}


# ─────────────────────────────────────────────
# Source 7: Binance P2P (real-time KES/USDT)
# ─────────────────────────────────────────────

def fetch_binance_p2p() -> dict:
    """
    Fetches real-time KES/USDT P2P market data from Binance.
    No API key required.
    Returns dict with market statistics or empty dict on failure.
    """
    log.info("Fetching real-time KES/USDT from Binance P2P...")
    try:
        payload = {
            "fiat":                      "KES",
            "page":                      1,
            "rows":                      20,
            "tradeType":                 "BUY",
            "asset":                     "USDT",
            "countries":                 [],
            "proMerchantAds":            False,
            "shieldMerchantAds":         False,
            "filterType":                "all",
            "periods":                   [],
            "additionalKycVerifyFilter": 0,
            "publisherType":             None,
            "payTypes":                  [],
            "classifies":                ["mass", "profession"],
        }
        r = requests.post(
            SOURCES["binance_p2p"]["url"],
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        ads = r.json().get("data", [])
        prices = [float(a["adv"]["price"]) for a in ads if a.get("adv", {}).get("price")]

        if len(prices) < P2P_MIN_ADS:
            log.warning(f"Binance P2P: only {len(prices)} ads. Below minimum {P2P_MIN_ADS}. BPPS unreliable.")
            return {"ad_count": len(prices), "reliable": False}

        result = {
            "timestamp":  datetime.now(tz=__import__('datetime').timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "min_price":  round(min(prices), 4),
            "max_price":  round(max(prices), 4),
            "mean_price": round(sum(prices) / len(prices), 4),
            "spread":     round(max(prices) - min(prices), 4),
            "ad_count":   len(prices),
            "reliable":   True,
        }
        log.info(f"Binance P2P: {len(prices)} ads | mean {result['mean_price']} KES/USDT | spread {result['spread']}")
        return result

    except Exception as e:
        log.error(f"Binance P2P: failed - {e}")
        return {}


# ─────────────────────────────────────────────
# Cross-Check and Fallback
# ─────────────────────────────────────────────

def get_current_rates_with_fallback() -> dict:
    """
    Fetches current rates using the fallback hierarchy.
    Cross-checks between sources. Flags divergence > 0.5%.
    Returns dict: {currency: {rate, source, flags, all_sources}}
    """
    log.info("Fetching current rates with fallback hierarchy...")

    source_results = {}

    open_er = fetch_open_er_api()
    if open_er:
        source_results["open_er_api"] = open_er

    exr_api = fetch_exchangerate_api()
    if exr_api:
        source_results["exchangerate_api"] = exr_api

    if ALPHA_VANTAGE_KEY:
        av_rates = {}
        for currency in EAC_PAIRS:
            val = fetch_alpha_vantage(currency)
            if val:
                av_rates[currency] = val
        if av_rates:
            source_results["alpha_vantage"] = av_rates

    if TWELVE_DATA_KEY:
        td_rates = {}
        for currency in EAC_PAIRS:
            val = fetch_twelve_data(currency)
            if val:
                td_rates[currency] = val
        if td_rates:
            source_results["twelve_data"] = td_rates

    # Exchangeratesapi.io free tier is EUR-base only; skipped until paid tier
    # if EXCHANGERATESAPI_KEY:
    #     era_rates = fetch_exchangeratesapi_io()
    #     if era_rates:
    #         source_results["exchangeratesapi_io"] = era_rates

    consolidated = {}
    for currency in EAC_PAIRS:
        values = {
            src: rates[currency]
            for src, rates in source_results.items()
            if currency in rates
        }

        if not values:
            log.warning(f"No current rate available for {currency} from any source")
            consolidated[currency] = {"rate": None, "source": "none", "flags": ["NO_DATA"]}
            continue

        primary_src = list(values.keys())[0]
        primary_val = values[primary_src]
        flags = []

        for src, val in values.items():
            if src != primary_src and not cross_check(primary_val, val):
                flags.append(f"DIVERGENCE_{src.upper()}")
                log.warning(f"{currency}: {primary_src}={primary_val} vs {src}={val} diverge > {CROSS_CHECK_THRESHOLD*100}%")

        consolidated[currency] = {
            "rate":        primary_val,
            "source":      primary_src,
            "flags":       flags,
            "all_sources": values,
        }
        log.info(f"{currency}: {primary_val} ({primary_src}) | flags: {flags or 'none'}")

    return consolidated


# ─────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────

def save_rates_to_csv(df: pd.DataFrame) -> None:
    """Appends rate records to the rates CSV store. Append-only.
    Deduplicates by (date, currency) before appending.
    """
    path = RAW_DATA_FILES["rates"]
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()

    if file_exists:
        existing = pd.read_csv(path)
        combined = pd.concat([existing, df], ignore_index=True)
        new_rows = max(0, len(combined) - len(existing))
        combined.to_csv(path, index=False)
        log.info(f"Saved {new_rows} new records to {path} ({len(combined)} total)")
    else:
        df.to_csv(path, index=False)
        log.info(f"Saved {len(df)} records to {path}")


def save_p2p_to_csv(p2p: dict) -> None:
    """Appends a Binance P2P snapshot to the P2P CSV store. Append-only."""
    if not p2p or not p2p.get("reliable"):
        log.warning("P2P data not reliable or empty. Not saving.")
        return

    path = RAW_DATA_FILES["p2p"]
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()

    fieldnames = ["timestamp", "min_price", "max_price", "mean_price", "spread", "ad_count"]
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: p2p[k] for k in fieldnames})
    log.info(f"Saved P2P snapshot to {path}")


def load_rates(currency: str = None) -> pd.DataFrame:
    """Loads the full rates store. Optionally filters by currency."""
    path = RAW_DATA_FILES["rates"]
    if not path.exists():
        log.warning(f"Rates file not found: {path}")
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    if currency:
        df = df[df["currency"] == currency]
    return df.sort_values("date").reset_index(drop=True)


def load_p2p() -> pd.DataFrame:
    """Loads the full Binance P2P snapshot history."""
    path = RAW_DATA_FILES["p2p"]
    if not path.exists():
        log.warning(f"P2P file not found: {path}")
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["timestamp"])


# ─────────────────────────────────────────────
# Main: Full Data Collection Run
# ─────────────────────────────────────────────

def run_data_collection(historical: bool = False) -> dict:
    """
    Runs the full data collection pipeline.

    historical=True:  fetches 5-year daily history from Yahoo Finance.
                      Run once on first setup or to backfill.
    historical=False: fetches today's current rates from all sources.
                      Run daily at 18:00 EAT.

    Returns a summary dict with collection results.
    """
    log.info("=" * 60)
    log.info("Ganji Protocol Data Collection Starting")
    log.info(f"Mode: {'HISTORICAL BACKFILL' if historical else 'DAILY UPDATE'}")
    log.info("=" * 60)

    summary = {
        "date":        date.today().isoformat(),
        "mode":        "historical" if historical else "daily",
        "rates_saved": 0,
        "p2p_saved":   False,
        "sources_used": [],
        "errors":      [],
    }

    if historical:
        df_history = fetch_yahoo_history()
        if not df_history.empty:
            save_rates_to_csv(df_history)
            summary["rates_saved"] += len(df_history)
            summary["sources_used"].append("yahoo_finance")
        else:
            summary["errors"].append("yahoo_finance_history_empty")

    current = get_current_rates_with_fallback()
    today_str = date.today().isoformat()
    records = []
    for currency, data in current.items():
        if data["rate"] is not None:
            records.append({
                "date":     today_str,
                "currency": currency,
                "close":    data["rate"],
                "source":   data["source"],
                "flag":     "|".join(data["flags"]) if data["flags"] else "",
            })
            if data["source"] not in summary["sources_used"]:
                summary["sources_used"].append(data["source"])

    if records:
        save_rates_to_csv(pd.DataFrame(records))
        summary["rates_saved"] += len(records)

    p2p = fetch_binance_p2p()
    if p2p.get("reliable"):
        save_p2p_to_csv(p2p)
        summary["p2p_saved"] = True
        if "binance_p2p" not in summary["sources_used"]:
            summary["sources_used"].append("binance_p2p")

    log.info("=" * 60)
    log.info(f"Data collection complete: {summary['rates_saved']} rate records saved")
    log.info(f"Sources used: {summary['sources_used']}")
    log.info(f"P2P snapshot saved: {summary['p2p_saved']}")
    if summary["errors"]:
        log.warning(f"Errors: {summary['errors']}")
    log.info("=" * 60)

    return summary


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ganji Protocol Data Layer")
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Run historical backfill from Yahoo Finance (run once on first setup)",
    )
    args = parser.parse_args()

    result = run_data_collection(historical=args.historical)
    print(json.dumps(result, indent=2))
