"""
Ganji Protocol - Historical Backtesting Engine
Runs the detection signals backwards over the 5-year historical dataset
and validates against the four ground truth CBK intervention events.

This is the Phase 2 validation defined in BACKTEST.md Part 5.

Usage:
  python engine/backtest.py

Output:
  data/backtest_results.csv   - signal firings per date
  data/backtest_summary.json  - precision, recall, and validation results
"""

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.data_layer import load_rates
from config.config import (
    ZSCORE_WINDOW, ZSCORE_THRESHOLD_LOW, ZSCORE_THRESHOLD_HIGH,
    CPII_WINDOW, CPII_THRESHOLD,
    GVCI_SHORT_WINDOW, GVCI_LONG_WINDOW, GVCI_SUPPRESSION_THRESHOLD,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Ground Truth Events (BACKTEST.md Part 2)
# ─────────────────────────────────────────────

GROUND_TRUTH_EVENTS = [
    {
        "id":         "GT-001",
        "label_date": date(2023, 9, 18),
        "type":       "KES_SUPPORT",
        "description": "September 2023 depreciation acceleration",
        "window_start": date(2023, 9, 8),
        "window_end":   date(2023, 9, 18),
    },
    {
        "id":         "GT-002",
        "label_date": date(2024, 2, 12),
        "type":       "KES_SUPPORT",
        "description": "January-February 2024 peak and sharp reversal",
        "window_start": date(2024, 1, 22),
        "window_end":   date(2024, 2, 12),
    },
    {
        "id":         "GT-003",
        "label_date": date(2024, 3, 11),
        "type":       "KES_SUPPORT",
        "description": "March 2024 continued stabilisation",
        "window_start": date(2024, 2, 26),
        "window_end":   date(2024, 3, 11),
    },
    {
        "id":         "GT-004",
        "label_date": date(2024, 4, 8),
        "type":       "KES_FLOOR_DEFENCE",
        "description": "April 2024 post-stabilisation floor defence",
        "window_start": date(2024, 3, 25),
        "window_end":   date(2024, 4, 8),
    },
]

DETECTION_WINDOW_DAYS = 10  # Extended window to capture pre-intervention signals


# ─────────────────────────────────────────────
# Signal Computation on Historical Slices
# ─────────────────────────────────────────────

def compute_f1_zscore(kes: pd.DataFrame, as_of: date) -> dict:
    """F1: Z-Score Deviation on KES/USD daily rate."""
    df = kes[kes["date"].dt.date <= as_of].copy()
    if len(df) < ZSCORE_WINDOW + 1:
        return {"fired": False, "value": 0.0, "detail": "insufficient_data"}

    df["rolling_mean"] = df["close"].rolling(ZSCORE_WINDOW).mean()
    df["rolling_std"]  = df["close"].rolling(ZSCORE_WINDOW).std()
    df["zscore"]       = (df["close"] - df["rolling_mean"]) / df["rolling_std"]

    latest = df.iloc[-1]
    z      = float(latest["zscore"]) if pd.notna(latest["zscore"]) else 0.0
    fired  = abs(z) > ZSCORE_THRESHOLD_LOW

    return {
        "fired":                fired,
        "value":                round(z, 4),
        "threshold_low_fired":  abs(z) > ZSCORE_THRESHOLD_LOW,
        "threshold_high_fired": abs(z) > ZSCORE_THRESHOLD_HIGH,
        "rolling_mean":         round(float(latest["rolling_mean"]), 4),
        "latest_rate":          round(float(latest["close"]), 4),
    }


def compute_f2_cpii(kes: pd.DataFrame, ugx: pd.DataFrame,
                    tzs: pd.DataFrame, as_of: date) -> dict:
    """F2: Cross-Pair Inconsistency Index."""
    def get_returns(df):
        d = df[df["date"].dt.date <= as_of].copy()
        if len(d) < CPII_WINDOW + 2:
            return None
        d["return"] = d["close"].pct_change()
        return d.set_index("date")["return"]

    r_kes = get_returns(kes)
    r_ugx = get_returns(ugx)
    r_tzs = get_returns(tzs)

    if r_kes is None or r_ugx is None or r_tzs is None:
        return {"fired": False, "value": 0.0, "detail": "insufficient_data"}

    combined = pd.DataFrame({"kes": r_kes, "ugx": r_ugx, "tzs": r_tzs}).dropna()
    if len(combined) < CPII_WINDOW + 1:
        return {"fired": False, "value": 0.0, "detail": "insufficient_data"}

    combined["basket"] = (combined["ugx"] + combined["tzs"]) / 2
    combined["cpii"]   = combined["kes"] - combined["basket"]
    combined["cpii_z"] = (
        (combined["cpii"] - combined["cpii"].rolling(CPII_WINDOW).mean())
        / combined["cpii"].rolling(CPII_WINDOW).std()
    )

    latest = combined.iloc[-1]
    cpii_z = float(latest["cpii_z"]) if pd.notna(latest["cpii_z"]) else 0.0
    fired  = abs(cpii_z) > CPII_THRESHOLD

    return {
        "fired":         fired,
        "value":         round(cpii_z, 4),
        "kes_return":    round(float(latest["kes"]), 6),
        "basket_return": round(float(latest["basket"]), 6),
    }


def compute_f3_gvci(kes: pd.DataFrame, as_of: date) -> dict:
    """F3: Ganji Volatility Compression Index."""
    df = kes[kes["date"].dt.date <= as_of].copy()
    if len(df) < GVCI_LONG_WINDOW + 1:
        return {"fired": False, "value": 1.0, "detail": "insufficient_data"}

    df["return"]      = df["close"].pct_change()
    df["sigma_short"] = df["return"].rolling(GVCI_SHORT_WINDOW).std()
    df["sigma_long"]  = df["return"].rolling(GVCI_LONG_WINDOW).std()
    df["gvci"]        = df["sigma_short"] / df["sigma_long"]

    latest = df.iloc[-1]
    gvci   = float(latest["gvci"]) if pd.notna(latest["gvci"]) else 1.0
    fired  = gvci < GVCI_SUPPRESSION_THRESHOLD

    recent_suppression = bool((df["gvci"].tail(5) < GVCI_SUPPRESSION_THRESHOLD).any())

    return {
        "fired":              fired,
        "value":              round(gvci, 4),
        "recent_suppression": recent_suppression,
    }


def compute_cips_score(f1: dict, f2: dict, f3: dict) -> dict:
    """Composite CIPS score from F1, F2, F3."""
    score = 0
    components = {}

    if f1.get("fired"):
        z = abs(f1.get("value", 0))
        if z > ZSCORE_THRESHOLD_LOW:
            score += 1
            components["z_score_low"] = 1
        if z > ZSCORE_THRESHOLD_HIGH:
            score += 1
            components["z_score_high"] = 1

    if f2.get("fired"):
        score += 3
        components["cpii"] = 3

    if f3.get("fired"):
        score += 2
        components["gvci"] = 2

    if score >= 5:
        confidence = "HIGH"
    elif score >= 3:
        confidence = "MEDIUM"
    elif score >= 1:
        confidence = "LOW"
    else:
        confidence = "NONE"

    return {
        "cips_score": score,
        "confidence": confidence,
        "components": components,
    }


# ─────────────────────────────────────────────
# Main Backtest Loop
# ─────────────────────────────────────────────

def run_backtest() -> dict:
    log.info("=" * 60)
    log.info("GANJI PROTOCOL HISTORICAL BACKTEST")
    log.info("Phase 2 validation: daily data, 5-year window")
    log.info("=" * 60)

    rates = load_rates()
    if rates.empty:
        log.error("No rate data. Run data_layer.py --historical first.")
        return {}

    # Deduplicate: keep one record per date per currency (prefer yahoo_finance)
    rates = rates.sort_values(["date", "currency", "source"])
    rates = rates.drop_duplicates(subset=["date", "currency"], keep="first")
    rates["date"] = pd.to_datetime(rates["date"])

    kes = rates[rates["currency"] == "KES"].sort_values("date").reset_index(drop=True)
    ugx = rates[rates["currency"] == "UGX"].sort_values("date").reset_index(drop=True)
    tzs = rates[rates["currency"] == "TZS"].sort_values("date").reset_index(drop=True)

    log.info(f"KES records: {len(kes)} | UGX: {len(ugx)} | TZS: {len(tzs)}")
    log.info(f"Date range: {kes['date'].min().date()} to {kes['date'].max().date()}")

    # Get all trading dates from KES series
    all_dates = sorted(kes["date"].dt.date.unique())

    # Only backtest from when we have enough data for all windows
    min_required = max(ZSCORE_WINDOW, CPII_WINDOW, GVCI_LONG_WINDOW) + 5
    backtest_dates = all_dates[min_required:]

    log.info(f"Backtesting {len(backtest_dates)} dates from {backtest_dates[0]} to {backtest_dates[-1]}")

    results = []

    for i, as_of in enumerate(backtest_dates):
        if i % 100 == 0:
            log.info(f"Progress: {i}/{len(backtest_dates)} ({as_of})")

        f1 = compute_f1_zscore(kes, as_of)
        f2 = compute_f2_cpii(kes, ugx, tzs, as_of)
        f3 = compute_f3_gvci(kes, as_of)
        cips = compute_cips_score(f1, f2, f3)

        results.append({
            "date":           str(as_of),
            "f1_fired":       f1["fired"],
            "f1_value":       f1.get("value", 0),
            "f2_fired":       f2["fired"],
            "f2_value":       f2.get("value", 0),
            "f3_fired":       f3["fired"],
            "f3_value":       f3.get("value", 1.0),
            "f3_recent_supp": f3.get("recent_suppression", False),
            "cips_score":     cips["cips_score"],
            "confidence":     cips["confidence"],
        })

    df_results = pd.DataFrame(results)

    # Save results
    results_path = _ROOT / "data" / "backtest_results.csv"
    df_results.to_csv(results_path, index=False)
    log.info(f"Saved {len(df_results)} daily results to {results_path}")

    # ─────────────────────────────────────────────
    # Validation Against Ground Truth Events
    # ─────────────────────────────────────────────

    log.info("")
    log.info("=" * 60)
    log.info("VALIDATION AGAINST GROUND TRUTH EVENTS")
    log.info("=" * 60)

    df_results["date"] = pd.to_datetime(df_results["date"]).dt.date

    validation = []

    for event in GROUND_TRUTH_EVENTS:
        window_dates = [
            d for d in df_results["date"]
            if event["window_start"] <= d <= event["window_end"]
        ]

        if not window_dates:
            log.warning(f"{event['id']}: no data in detection window")
            validation.append({
                "event_id":    event["id"],
                "description": event["description"],
                "label_date":  str(event["label_date"]),
                "f1_tp":       False,
                "f2_tp":       False,
                "f3_tp":       False,
                "high_tp":     False,
                "note":        "no_data_in_window",
            })
            continue

        window_data = df_results[df_results["date"].isin(window_dates)]

        f1_tp   = bool(window_data["f1_fired"].any())
        f2_tp   = bool(window_data["f2_fired"].any())
        f3_tp   = bool(window_data["f3_fired"].any())
        high_tp = bool((window_data["confidence"] == "HIGH").any())
        med_tp  = bool((window_data["confidence"].isin(["HIGH", "MEDIUM"])).any())

        max_score = int(window_data["cips_score"].max())
        max_conf  = window_data.loc[window_data["cips_score"].idxmax(), "confidence"]

        log.info(f"\n{event['id']}: {event['description']}")
        log.info(f"  Window: {event['window_start']} to {event['window_end']}")
        log.info(f"  F1 fired: {f1_tp} | F2 fired: {f2_tp} | F3 fired: {f3_tp}")
        log.info(f"  Max CIPS score: {max_score} ({max_conf})")
        log.info(f"  HIGH confidence: {high_tp} | MEDIUM+: {med_tp}")

        validation.append({
            "event_id":    event["id"],
            "description": event["description"],
            "label_date":  str(event["label_date"]),
            "window_start": str(event["window_start"]),
            "window_end":   str(event["window_end"]),
            "f1_tp":        f1_tp,
            "f2_tp":        f2_tp,
            "f3_tp":        f3_tp,
            "high_tp":      high_tp,
            "medium_plus_tp": med_tp,
            "max_cips_score": max_score,
            "max_confidence": max_conf,
        })

    # ─────────────────────────────────────────────
    # Precision and Recall
    # ─────────────────────────────────────────────

    n_events = len(GROUND_TRUTH_EVENTS)

    f1_recall   = sum(v["f1_tp"] for v in validation) / n_events
    f2_recall   = sum(v["f2_tp"] for v in validation) / n_events
    f3_recall   = sum(v["f3_tp"] for v in validation) / n_events
    high_recall = sum(v["high_tp"] for v in validation) / n_events

    # False positives: HIGH confidence signals outside all event windows
    all_event_dates = set()
    for event in GROUND_TRUTH_EVENTS:
        d = event["window_start"]
        while d <= event["window_end"]:
            all_event_dates.add(d)
            d += timedelta(days=1)

    non_event = df_results[~df_results["date"].isin(all_event_dates)]
    f1_fp_per_year   = round(non_event["f1_fired"].sum() / 5, 1)
    f2_fp_per_year   = round(non_event["f2_fired"].sum() / 5, 1)
    f3_fp_per_year   = round(non_event["f3_fired"].sum() / 5, 1)
    high_fp_per_year = round((non_event["confidence"] == "HIGH").sum() / 5, 1)

    f1_precision   = round(4 / (4 + f1_fp_per_year), 3) if f1_fp_per_year > 0 else 1.0
    f2_precision   = round(4 / (4 + f2_fp_per_year), 3) if f2_fp_per_year > 0 else 1.0
    f3_precision   = round(4 / (4 + f3_fp_per_year), 3) if f3_fp_per_year > 0 else 1.0
    high_precision = round(4 / (4 + high_fp_per_year), 3) if high_fp_per_year > 0 else 1.0

    log.info("")
    log.info("=" * 60)
    log.info("PRECISION AND RECALL SUMMARY")
    log.info("=" * 60)
    log.info(f"{'Signal':<12} {'Recall':>8} {'FP/year':>10} {'Precision':>12}")
    log.info(f"{'-'*44}")
    log.info(f"{'F1 Z-Score':<12} {f1_recall:>8.2f} {f1_fp_per_year:>10.1f} {f1_precision:>12.3f}")
    log.info(f"{'F2 CPII':<12} {f2_recall:>8.2f} {f2_fp_per_year:>10.1f} {f2_precision:>12.3f}")
    log.info(f"{'F3 GVCI':<12} {f3_recall:>8.2f} {f3_fp_per_year:>10.1f} {f3_precision:>12.3f}")
    log.info(f"{'HIGH CIPS':<12} {high_recall:>8.2f} {high_fp_per_year:>10.1f} {high_precision:>12.3f}")
    log.info("=" * 60)

    summary = {
        "backtest_date":    str(date.today()),
        "data_range":       f"{backtest_dates[0]} to {backtest_dates[-1]}",
        "total_dates":      len(backtest_dates),
        "ground_truth_events": n_events,
        "detection_window_days": DETECTION_WINDOW_DAYS,
        "validation":       validation,
        "precision_recall": {
            "f1_zscore":  {"recall": f1_recall,   "fp_per_year": f1_fp_per_year,   "precision": f1_precision},
            "f2_cpii":    {"recall": f2_recall,   "fp_per_year": f2_fp_per_year,   "precision": f2_precision},
            "f3_gvci":    {"recall": f3_recall,   "fp_per_year": f3_fp_per_year,   "precision": f3_precision},
            "high_cips":  {"recall": high_recall, "fp_per_year": high_fp_per_year, "precision": high_precision},
        },
    }

    summary_path = _ROOT / "data" / "backtest_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log.info(f"Summary saved to {summary_path}")

    return summary


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    result = run_backtest()
    if result:
        print(json.dumps(result.get("precision_recall", {}), indent=2))
