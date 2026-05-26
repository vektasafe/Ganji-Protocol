"""
Ganji Protocol - Signal Output Layer (Layer 4)
Builds the structured JSON signal output from detection results.
Enforces the regulatory boundary: no recommended_action field.

Reference: SYSTEM.md Section 5
"""

import json
import logging
import sys
from datetime import datetime, date, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.config import RAW_DATA_FILES
from engine.features import FeatureResult, compute_all_features
from engine.detection import DetectionResult, compute_cips

log = logging.getLogger(__name__)

PIPELINE_VERSION = "1.0.0"

REGULATORY_NOTE = (
    "This output is signal intelligence based on statistical analysis "
    "of public data. It is not financial advice. No action is recommended "
    "or implied. The subscriber determines how to use this information."
)

PROHIBITED_FIELDS = {
    "recommended_action", "buy", "sell",
    "position_size", "stop_loss", "take_profit"
}


# ─────────────────────────────────────────────
# Signal ID Generator
# ─────────────────────────────────────────────

def generate_signal_id(signal_date: date, sequence: int = 1) -> str:
    return f"GP-{signal_date.strftime('%Y-%m-%d')}-{sequence:03d}"


# ─────────────────────────────────────────────
# Signal Context Builder
# ─────────────────────────────────────────────

def build_signal_context(features: dict, result: DetectionResult) -> str:
    """
    Builds the plain-language signal_context field.
    Describes what the data shows. Never instructs what to do.
    """
    parts = []

    f1 = features.get("F1")
    f2 = features.get("F2")
    f3 = features.get("F3")
    f6 = features.get("F6")
    f7 = features.get("F7")

    if result.confidence == "NONE":
        return (
            "No anomalous signals detected. KES/USD within normal volatility "
            "range. Cross-pair consistency normal. Volatility regime normal."
        )

    if f1 and f1.fired:
        parts.append(
            f"Z-score deviation of {abs(f1.value):.2f} sigma "
            f"({'above' if f1.value > 0 else 'below'} 30-day mean)."
        )

    if f2 and f2.fired:
        kes_ret    = f2.detail.get("kes_return", 0) * 100
        basket_ret = f2.detail.get("basket_return", 0) * 100
        parts.append(
            f"Cross-pair inconsistency: KES moved {kes_ret:.2f}% "
            f"while UGX/TZS basket moved {basket_ret:.2f}%."
        )

    if f3 and f3.fired:
        parts.append(
            f"Volatility suppression detected: GVCI {f3.value:.4f} "
            f"(threshold {f3.detail.get('threshold', 0.3)}). "
            f"Short-term volatility compressed to "
            f"{f3.value*100:.1f}% of 30-day norm."
        )
        if f3.detail.get("recent_suppression"):
            parts.append("Suppression pattern persistent over last 5 days.")

    if result.sequence_pattern:
        parts.append(
            "Sequence pattern detected: volatility suppression preceded "
            "price spike. Strongest intervention signature."
        )

    if result.cpii_contributed:
        parts.append(
            "Cross-pair signal contributed: KES-specific move confirmed, "
            "not a broad USD event."
        )

    if f6 and f6.fired:
        premium = f6.detail.get("premium", 0) * 100
        if f6.detail.get("capital_flight"):
            parts.append(
                f"Binance P2P premium {premium:.2f}% above official rate. "
                "Capital flight signal active."
            )
        elif f6.detail.get("cbk_suppression"):
            parts.append(
                f"Binance P2P {abs(premium):.2f}% below official rate. "
                "CBK rate suppression signal active."
            )

    if result.calendar_flags:
        parts.append(
            f"Calendar context: {', '.join(result.calendar_flags)}. "
            "Confidence adjusted accordingly."
        )

    if result.confidence != result.confidence_raw:
        parts.append(
            f"Confidence downgraded from {result.confidence_raw} to "
            f"{result.confidence} due to calendar context."
        )

    return " ".join(parts) if parts else "Signal active. See component breakdown."


# ─────────────────────────────────────────────
# Full Signal Output Builder
# ─────────────────────────────────────────────

def build_signal_output(
    features: dict,
    result: DetectionResult,
    signal_date: date = None,
    sequence: int = 1,
    data_quality: dict = None,
) -> dict:
    """
    Builds the full signal output JSON per SYSTEM.md Section 5.2.
    Enforces prohibited fields. Returns a dict ready for storage and delivery.
    """
    if signal_date is None:
        signal_date = date.today()

    signal_id = generate_signal_id(signal_date, sequence)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    f1 = features.get("F1")
    f2 = features.get("F2")
    f3 = features.get("F3")
    f5 = features.get("F5")
    f6 = features.get("F6")

    output = {
        "signal_id":        signal_id,
        "pair":             "KES/USD",
        "timestamp":        timestamp,
        "data_date":        signal_date.isoformat(),
        "pipeline_version": PIPELINE_VERSION,

        "detection": {
            "cips_score":       result.cips_score,
            "confidence":       result.confidence,
            "direction":        result.direction,
            "sequence_pattern": result.sequence_pattern,
            "cpii_contributed": result.cpii_contributed,
        },

        "components": {
            "z_score": {
                "value":                f1.value if f1 else None,
                "threshold_low_fired":  f1.detail.get("threshold_low_fired") if f1 else False,
                "threshold_high_fired": f1.detail.get("threshold_high_fired") if f1 else False,
                "points":               result.components.get("z_score_low", 0)
                                        + result.components.get("z_score_high", 0),
            },
            "cpii": {
                "fired":         f2.fired if f2 else False,
                "cpii_z_value":  f2.value if f2 else None,
                "kes_return":    f2.detail.get("kes_return") if f2 else None,
                "basket_return": f2.detail.get("basket_return") if f2 else None,
                "divergence":    f2.detail.get("divergence") if f2 else None,
                "points":        result.components.get("cpii", 0),
            },
            "gvci": {
                "fired":              f3.fired if f3 else False,
                "gvci_value":         f3.value if f3 else None,
                "threshold":          f3.detail.get("threshold") if f3 else None,
                "recent_suppression": f3.detail.get("recent_suppression") if f3 else False,
                "points":             result.components.get("gvci", 0),
            },
            "rss": {
                "available": False,
                "phase":     2,
                "points":    0,
            },
            "nlp_tone": {
                "tone":        f5.detail.get("tone", "NEUTRAL") if f5 else "NEUTRAL",
                "key_phrases": f5.detail.get("key_phrases", []) if f5 else [],
                "points":      result.components.get("nlp_tone", 0),
            },
            "bpps": {
                "p2p_mean":        f6.detail.get("p2p_mean") if f6 else None,
                "cbk_rate":        f6.detail.get("cbk_rate") if f6 else None,
                "premium":         f6.detail.get("premium") if f6 else None,
                "capital_flight":  f6.detail.get("capital_flight", False) if f6 else False,
                "cbk_suppression": f6.detail.get("cbk_suppression", False) if f6 else False,
                "points":          result.components.get("bpps", 0),
            },
        },

        "context": {
            "calendar_flags":               result.calendar_flags,
            "confidence_before_adjustment": result.confidence_raw,
            "confidence_after_adjustment":  result.confidence,
            "data_quality":                 data_quality or {},
            "spike_detected":               False,
        },

        "signal_context":  build_signal_context(features, result),
        "regulatory_note": REGULATORY_NOTE,
    }

    # Enforce prohibited fields
    for field in PROHIBITED_FIELDS:
        output.pop(field, None)

    return output


# ─────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────

def save_signal(signal: dict) -> None:
    """
    Appends signal to the JSONL archive and updates the index CSV.
    Append-only: no signal is ever modified.
    """
    archive_path = RAW_DATA_FILES["signal_archive"]
    index_path   = RAW_DATA_FILES["signal_index"]

    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with open(archive_path, "a") as f:
        f.write(json.dumps(signal) + "\n")

    index_exists = index_path.exists()
    with open(index_path, "a") as f:
        if not index_exists:
            f.write("signal_id,date,confidence,direction\n")
        f.write(
            f"{signal['signal_id']},"
            f"{signal['data_date']},"
            f"{signal['detection']['confidence']},"
            f"{signal['detection']['direction']}\n"
        )

    log.info(f"Signal saved: {signal['signal_id']} | {signal['detection']['confidence']}")


def load_latest_signal() -> dict:
    """Returns the most recently saved signal or empty dict."""
    path = RAW_DATA_FILES["signal_archive"]
    if not path.exists():
        return {}
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    return json.loads(lines[-1]) if lines else {}


def load_signal_history(days: int = 30) -> list:
    """Returns the last N days of signals from the archive."""
    path = RAW_DATA_FILES["signal_archive"]
    if not path.exists():
        return []
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    signals = [json.loads(l) for l in lines]
    return signals[-days:] if len(signals) > days else signals


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    features = compute_all_features()
    if not features:
        print("No features computed. Run data_layer.py first.")
        sys.exit(1)

    result = compute_cips(features)
    signal = build_signal_output(features, result)
    save_signal(signal)

    print(json.dumps(signal, indent=2))
