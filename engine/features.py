"""
Ganji Protocol - Feature Engineering Layer
Computes the seven detection features from raw rate data.
Every feature has a precise mathematical definition per SYSTEM.md Section 3.

Features:
  F1: KES/USD Z-Score Deviation          [VALIDATED]
  F2: Cross-Pair Inconsistency Index     [VALIDATED]
  F3: Ganji Volatility Compression Index [VALIDATED]
  F4: Reserve Stress Signal              [HYPOTHESIS - Phase 2]
  F5: CBK NLP Tone Classification        [IMPLEMENTED - placeholder]
  F6: Binance P2P Premium Signal         [IMPLEMENTED]
  F7: Seasonal Calendar Filter           [IMPLEMENTED]
"""

import logging
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.config import (
    ZSCORE_WINDOW, ZSCORE_THRESHOLD_LOW, ZSCORE_THRESHOLD_HIGH,
    CPII_WINDOW, CPII_THRESHOLD,
    GVCI_SHORT_WINDOW, GVCI_LONG_WINDOW, GVCI_SUPPRESSION_THRESHOLD,
    BPPS_CAPITAL_FLIGHT, BPPS_SUPPRESSION,
    CALENDAR_FLAGS, RAW_DATA_FILES,
)
from engine.data_layer import load_rates, load_p2p

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Feature Result Dataclass
# ─────────────────────────────────────────────

@dataclass
class FeatureResult:
    name: str
    fired: bool
    value: float = 0.0
    detail: dict = field(default_factory=dict)
    status: str = "VALIDATED"
    phase: int = 1


# ─────────────────────────────────────────────
# F1: KES/USD Z-Score Deviation
# ─────────────────────────────────────────────

def f1_zscore(rates: pd.DataFrame) -> FeatureResult:
    """
    Z = (P_t - mu_30) / sigma_30
    Fires when |Z| > 2.0 (composite trigger) or |Z| > 2.5 (standalone).
    Precision: 0.36 (threshold 2.0) | Recall: 1.00
    Reference: SYSTEM.md Section 3.2
    """
    kes = rates[rates["currency"] == "KES"].copy().sort_values("date")

    if len(kes) < ZSCORE_WINDOW + 1:
        log.warning("F1: insufficient KES data for Z-score computation")
        return FeatureResult("F1_ZSCORE", False, status="VALIDATED")

    kes["rolling_mean"] = kes["close"].rolling(ZSCORE_WINDOW).mean()
    kes["rolling_std"]  = kes["close"].rolling(ZSCORE_WINDOW).std()
    kes["zscore"]       = (kes["close"] - kes["rolling_mean"]) / kes["rolling_std"]

    latest = kes.iloc[-1]
    z      = float(latest["zscore"]) if pd.notna(latest["zscore"]) else 0.0
    fired  = abs(z) > ZSCORE_THRESHOLD_LOW

    log.info(f"F1 Z-Score: {z:.4f} | fired: {fired}")

    return FeatureResult(
        name="F1_ZSCORE",
        fired=fired,
        value=round(z, 4),
        detail={
            "z_score":              round(z, 4),
            "threshold_low_fired":  abs(z) > ZSCORE_THRESHOLD_LOW,
            "threshold_high_fired": abs(z) > ZSCORE_THRESHOLD_HIGH,
            "rolling_mean":         round(float(latest["rolling_mean"]), 4),
            "rolling_std":          round(float(latest["rolling_std"]), 4),
            "latest_rate":          round(float(latest["close"]), 4),
            "date":                 str(latest["date"].date()),
        },
        status="VALIDATED",
        phase=1,
    )


# ─────────────────────────────────────────────
# F2: Cross-Pair Inconsistency Index (CPII)
# ─────────────────────────────────────────────

def f2_cpii(rates: pd.DataFrame) -> FeatureResult:
    """
    CPII   = r_KES - r_basket  (basket = equal-weighted UGX + TZS)
    CPII_Z = (CPII - mu_30) / sigma_30
    Fires when |CPII_Z| > 1.5.
    Precision: 0.87 | Recall: 0.90
    Reference: SYSTEM.md Section 3.3
    """
    def get_returns(currency: str) -> Optional[pd.Series]:
        df = rates[rates["currency"] == currency].copy().sort_values("date")
        if len(df) < CPII_WINDOW + 2:
            log.warning(f"F2: insufficient {currency} data")
            return None
        df["return"] = df["close"].pct_change()
        return df.set_index("date")["return"]

    r_kes = get_returns("KES")
    r_ugx = get_returns("UGX")
    r_tzs = get_returns("TZS")

    if r_kes is None or r_ugx is None or r_tzs is None:
        return FeatureResult("F2_CPII", False, status="VALIDATED", phase=2)

    combined = pd.DataFrame({"kes": r_kes, "ugx": r_ugx, "tzs": r_tzs}).dropna()

    if len(combined) < CPII_WINDOW + 1:
        log.warning("F2: insufficient aligned data for CPII")
        return FeatureResult("F2_CPII", False, status="VALIDATED", phase=2)

    combined["basket"] = (combined["ugx"] + combined["tzs"]) / 2
    combined["cpii"]   = combined["kes"] - combined["basket"]
    combined["cpii_z"] = (
        (combined["cpii"] - combined["cpii"].rolling(CPII_WINDOW).mean())
        / combined["cpii"].rolling(CPII_WINDOW).std()
    )

    latest = combined.iloc[-1]
    cpii_z = float(latest["cpii_z"]) if pd.notna(latest["cpii_z"]) else 0.0
    fired  = abs(cpii_z) > CPII_THRESHOLD

    log.info(f"F2 CPII Z-Score: {cpii_z:.4f} | fired: {fired}")

    return FeatureResult(
        name="F2_CPII",
        fired=fired,
        value=round(cpii_z, 4),
        detail={
            "cpii_z_value":  round(cpii_z, 4),
            "kes_return":    round(float(latest["kes"]), 6),
            "basket_return": round(float(latest["basket"]), 6),
            "divergence":    round(float(latest["cpii"]), 6),
            "threshold":     CPII_THRESHOLD,
        },
        status="VALIDATED",
        phase=2,
    )


# ─────────────────────────────────────────────
# F3: Ganji Volatility Compression Index (GVCI)
# ─────────────────────────────────────────────

def f3_gvci(rates: pd.DataFrame) -> FeatureResult:
    """
    GVCI = sigma_5 / sigma_30
    Fires when GVCI < 0.3 (suppression threshold).
    Precision: 0.70 | Recall: 0.90
    Reference: SYSTEM.md Section 3.4
    """
    kes = rates[rates["currency"] == "KES"].copy().sort_values("date")

    if len(kes) < GVCI_LONG_WINDOW + 1:
        log.warning("F3: insufficient KES data for GVCI computation")
        return FeatureResult("F3_GVCI", False, status="VALIDATED")

    kes["return"]      = kes["close"].pct_change()
    kes["sigma_short"] = kes["return"].rolling(GVCI_SHORT_WINDOW).std()
    kes["sigma_long"]  = kes["return"].rolling(GVCI_LONG_WINDOW).std()
    kes["gvci"]        = kes["sigma_short"] / kes["sigma_long"]

    latest = kes.iloc[-1]
    gvci   = float(latest["gvci"]) if pd.notna(latest["gvci"]) else 1.0
    fired  = gvci < GVCI_SUPPRESSION_THRESHOLD

    recent_suppression = bool((kes["gvci"].tail(5) < GVCI_SUPPRESSION_THRESHOLD).any())

    log.info(f"F3 GVCI: {gvci:.4f} | fired: {fired}")

    return FeatureResult(
        name="F3_GVCI",
        fired=fired,
        value=round(gvci, 4),
        detail={
            "gvci_value":         round(gvci, 4),
            "threshold":          GVCI_SUPPRESSION_THRESHOLD,
            "sigma_short":        round(float(latest["sigma_short"]), 6),
            "sigma_long":         round(float(latest["sigma_long"]), 6),
            "recent_suppression": recent_suppression,
        },
        status="VALIDATED",
        phase=1,
    )


# ─────────────────────────────────────────────
# F4: Reserve Stress Signal (Phase 2 placeholder)
# ─────────────────────────────────────────────

def f4_rss() -> FeatureResult:
    """
    RSS = R_(t-1) - R_t
    Fires when RSS > $200M and no scheduled debt payment.
    Status: HYPOTHESIS - Phase 2. Requires CBK weekly bulletin PDF parser.
    Reference: SYSTEM.md Section 3.5
    """
    log.debug("F4 RSS: Phase 2 placeholder. Returning not fired.")
    return FeatureResult(
        name="F4_RSS",
        fired=False,
        value=0.0,
        detail={"note": "Phase 2: requires CBK weekly bulletin PDF parser"},
        status="HYPOTHESIS",
        phase=2,
    )


# ─────────────────────────────────────────────
# F5: CBK NLP Tone Classification (placeholder)
# ─────────────────────────────────────────────

def f5_nlp(tone: str = "NEUTRAL") -> FeatureResult:
    """
    Classifies CBK MPC press statement tone using Gemma 4.
    Score contributions:
      INTERVENTION_IMMINENT: +2 | HAWKISH: +1 | NEUTRAL: 0 | DOVISH: -1
    Status: IMPLEMENTED - prompt defined, empirical validation pending.
    Reference: SYSTEM.md Section 3.6
    """
    tone_scores = {
        "INTERVENTION_IMMINENT": 2,
        "HAWKISH":               1,
        "NEUTRAL":               0,
        "DOVISH":               -1,
    }
    score = tone_scores.get(tone.upper(), 0)
    fired = score > 0

    log.info(f"F5 NLP Tone: {tone} | score contribution: {score} | fired: {fired}")

    return FeatureResult(
        name="F5_NLP",
        fired=fired,
        value=float(score),
        detail={
            "tone":               tone.upper(),
            "score_contribution": score,
            "key_phrases":        [],
        },
        status="IMPLEMENTED",
        phase=1,
    )


# ─────────────────────────────────────────────
# F6: Binance P2P Premium Signal (BPPS)
# ─────────────────────────────────────────────

def f6_bpps(rates: pd.DataFrame) -> FeatureResult:
    """
    BPPS = (P_P2P - P_CBK) / P_CBK
    Fires when BPPS > +0.5% (capital flight) or BPPS < -0.5% (CBK suppression).
    Status: IMPLEMENTED - live data confirmed May 2026.
    Reference: SYSTEM.md Section 3.7
    """
    p2p_df = load_p2p()

    if p2p_df.empty:
        log.warning("F6: no P2P data available")
        return FeatureResult("F6_BPPS", False, status="IMPLEMENTED")

    kes = rates[rates["currency"] == "KES"].sort_values("date")
    if kes.empty:
        log.warning("F6: no KES rate data available")
        return FeatureResult("F6_BPPS", False, status="IMPLEMENTED")

    cbk_rate        = float(kes.iloc[-1]["close"])
    p2p_latest      = p2p_df.sort_values("timestamp").iloc[-1]
    p2p_mean        = float(p2p_latest["mean_price"])
    ad_count        = int(p2p_latest["ad_count"])
    premium         = (p2p_mean - cbk_rate) / cbk_rate
    capital_flight  = premium > BPPS_CAPITAL_FLIGHT
    cbk_suppression = premium < BPPS_SUPPRESSION
    fired           = capital_flight or cbk_suppression

    log.info(f"F6 BPPS: premium={premium:.4f} | capital_flight={capital_flight} | cbk_suppression={cbk_suppression}")

    return FeatureResult(
        name="F6_BPPS",
        fired=fired,
        value=round(premium, 6),
        detail={
            "p2p_mean":        round(p2p_mean, 4),
            "cbk_rate":        round(cbk_rate, 4),
            "premium":         round(premium, 6),
            "capital_flight":  capital_flight,
            "cbk_suppression": cbk_suppression,
            "ad_count":        ad_count,
        },
        status="IMPLEMENTED",
        phase=1,
    )


# ─────────────────────────────────────────────
# F7: Seasonal Calendar Filter
# ─────────────────────────────────────────────

def f7_calendar(target_date: date = None) -> FeatureResult:
    """
    Flags known high-volatility calendar events.
    Flags annotate signals; they do not suppress them.
    Reference: SYSTEM.md Section 3.8
    """
    if target_date is None:
        target_date = date.today()

    flags = []
    if target_date.month in CALENDAR_FLAGS.get("budget_month", []):
        flags.append("BUDGET_MONTH")
    if target_date.month in CALENDAR_FLAGS.get("imf_review_months", []):
        flags.append("IMF_REVIEW_MONTH")
    if target_date.month in CALENDAR_FLAGS.get("diaspora_peak_months", []):
        flags.append("DIASPORA_PEAK")
    if target_date.month in CALENDAR_FLAGS.get("debt_service_months", []):
        flags.append("DEBT_SERVICE_MONTH")
    if target_date.day >= 28:
        flags.append("END_OF_MONTH")

    fired = len(flags) > 0
    log.info(f"F7 Calendar: {target_date} | flags: {flags or 'none'}")

    return FeatureResult(
        name="F7_CALENDAR",
        fired=fired,
        value=float(len(flags)),
        detail={"flags": flags, "date": str(target_date)},
        status="IMPLEMENTED",
        phase=1,
    )


# ─────────────────────────────────────────────
# Run All Features
# ─────────────────────────────────────────────

def compute_all_features(nlp_tone: str = "NEUTRAL",
                         target_date: date = None) -> dict:
    """
    Loads data and computes all seven features.
    Returns a dict of feature name to FeatureResult.
    """
    log.info("Computing all features...")
    rates = load_rates()

    if rates.empty:
        log.error("No rate data available. Run data_layer.py first.")
        return {}

    results = {
        "F1": f1_zscore(rates),
        "F2": f2_cpii(rates),
        "F3": f3_gvci(rates),
        "F4": f4_rss(),
        "F5": f5_nlp(nlp_tone),
        "F6": f6_bpps(rates),
        "F7": f7_calendar(target_date),
    }

    log.info("Feature computation complete:")
    for key, result in results.items():
        log.info(f"  {key} {result.name}: fired={result.fired} | value={result.value} | status={result.status}")

    return results


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import json
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    results = compute_all_features()
    output = {
        k: {
            "fired":  v.fired,
            "value":  v.value,
            "detail": v.detail,
            "status": v.status,
            "phase":  v.phase,
        }
        for k, v in results.items()
    }
    print(json.dumps(output, indent=2))
