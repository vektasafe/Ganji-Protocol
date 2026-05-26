"""
Ganji Protocol - Detection Engine (Layer 3)
Computes the CBK Intervention Probability Score (CIPS) from feature results.
Classifies intervention direction and confidence tier.

Reference: SYSTEM.md Section 4
"""

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.config import (
    CIPS_WEIGHTS,
    CIPS_HIGH_THRESHOLD,
    CIPS_MEDIUM_THRESHOLD,
    CIPS_LOW_THRESHOLD,
    ZSCORE_THRESHOLD_LOW,
    ZSCORE_THRESHOLD_HIGH,
    BPPS_SUPPRESSION,
)
from engine.features import FeatureResult

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Detection Result Dataclass
# ─────────────────────────────────────────────

@dataclass
class DetectionResult:
    cips_score: int
    confidence: str
    confidence_raw: str
    direction: str
    sequence_pattern: bool
    cpii_contributed: bool
    calendar_flags: list = field(default_factory=list)
    components: dict = field(default_factory=dict)


# ─────────────────────────────────────────────
# CIPS Scoring Function
# ─────────────────────────────────────────────

def compute_cips(features: dict) -> DetectionResult:
    """
    Aggregates all feature results into the CBK Intervention
    Probability Score (CIPS) and returns a DetectionResult.

    Weights (SYSTEM.md Section 4.2):
      F1 Z-score low  (|Z| > 2.0): +1
      F1 Z-score high (|Z| > 2.5): +1
      F2 CPII fired:               +3
      F3 GVCI fired:               +2
      F4 RSS fired:                +2  (Phase 2)
      F5 NLP tone:                 -1 to +2
      F6 BPPS fired:               +1

    Confidence tiers:
      HIGH   >= 5
      MEDIUM >= 3
      LOW    >= 1
      NONE    = 0
    """
    score      = 0
    components = {}

    f1 = features.get("F1")
    f2 = features.get("F2")
    f3 = features.get("F3")
    f4 = features.get("F4")
    f5 = features.get("F5")
    f6 = features.get("F6")
    f7 = features.get("F7")

    # F1: Z-score
    if f1 and f1.fired:
        z = abs(f1.value)
        if z > ZSCORE_THRESHOLD_LOW:
            score += CIPS_WEIGHTS["z_score_low"]
            components["z_score_low"] = CIPS_WEIGHTS["z_score_low"]
        if z > ZSCORE_THRESHOLD_HIGH:
            score += CIPS_WEIGHTS["z_score_high"]
            components["z_score_high"] = CIPS_WEIGHTS["z_score_high"]

    # F2: CPII
    cpii_contributed = bool(f2 and f2.fired)
    if cpii_contributed:
        score += CIPS_WEIGHTS["cpii"]
        components["cpii"] = CIPS_WEIGHTS["cpii"]

    # F3: GVCI
    if f3 and f3.fired:
        score += CIPS_WEIGHTS["gvci"]
        components["gvci"] = CIPS_WEIGHTS["gvci"]

    # F4: RSS (Phase 2)
    if f4 and f4.fired:
        score += CIPS_WEIGHTS["rss"]
        components["rss"] = CIPS_WEIGHTS["rss"]

    # F5: NLP tone
    if f5:
        tone = f5.detail.get("tone", "NEUTRAL")
        nlp_weight_key = {
            "INTERVENTION_IMMINENT": "nlp_intervention_imminent",
            "HAWKISH":               "nlp_hawkish",
            "NEUTRAL":               "nlp_neutral",
            "DOVISH":                "nlp_dovish",
        }.get(tone, "nlp_neutral")
        nlp_contribution = CIPS_WEIGHTS.get(nlp_weight_key, 0)
        score += nlp_contribution
        components["nlp_tone"] = nlp_contribution

    # F6: BPPS
    if f6 and f6.fired:
        score += CIPS_WEIGHTS["bpps"]
        components["bpps"] = CIPS_WEIGHTS["bpps"]

    # Confidence tier (raw, before calendar adjustment)
    if score >= CIPS_HIGH_THRESHOLD:
        confidence_raw = "HIGH"
    elif score >= CIPS_MEDIUM_THRESHOLD:
        confidence_raw = "MEDIUM"
    elif score >= CIPS_LOW_THRESHOLD:
        confidence_raw = "LOW"
    else:
        confidence_raw = "NONE"

    # Calendar adjustment: downgrade one tier during high-impact events
    calendar_flags = f7.detail.get("flags", []) if f7 else []
    high_impact    = {"BUDGET_MONTH", "IMF_REVIEW_MONTH"}
    confidence     = confidence_raw

    if any(flag in high_impact for flag in calendar_flags):
        tier_map   = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "NONE", "NONE": "NONE"}
        confidence = tier_map[confidence_raw]
        log.info(f"Calendar adjustment: {confidence_raw} -> {confidence} ({calendar_flags})")

    # Direction classification
    direction = _classify_direction(f1, f6)

    # Sequence pattern: GVCI suppression preceded Z-score spike
    sequence_pattern = False
    if f3 and f1:
        recent_suppression = f3.detail.get("recent_suppression", False)
        z_spike            = abs(f1.value) > ZSCORE_THRESHOLD_LOW
        sequence_pattern   = bool(recent_suppression and z_spike)

    log.info(
        f"CIPS: score={score} | confidence={confidence} "
        f"(raw={confidence_raw}) | direction={direction} | "
        f"sequence={sequence_pattern} | cpii={cpii_contributed}"
    )

    return DetectionResult(
        cips_score=score,
        confidence=confidence,
        confidence_raw=confidence_raw,
        direction=direction,
        sequence_pattern=sequence_pattern,
        cpii_contributed=cpii_contributed,
        calendar_flags=calendar_flags,
        components=components,
    )


# ─────────────────────────────────────────────
# Direction Classification
# ─────────────────────────────────────────────

def _classify_direction(f1: FeatureResult, f6: FeatureResult) -> str:
    """
    KES_SUPPORT:       CBK selling USD to prevent KES depreciation.
    KES_FLOOR_DEFENCE: CBK buying USD to prevent excessive KES appreciation.
    INDETERMINATE:     Direction cannot be determined.
    Reference: SYSTEM.md Section 4.4
    """
    z               = f1.value if f1 else 0.0
    cbk_suppression = f6.detail.get("cbk_suppression", False) if f6 else False

    if z > ZSCORE_THRESHOLD_LOW and not cbk_suppression:
        return "KES_SUPPORT"
    elif z < -ZSCORE_THRESHOLD_LOW or cbk_suppression:
        return "KES_FLOOR_DEFENCE"
    else:
        return "INDETERMINATE"


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

    from engine.features import compute_all_features
    features = compute_all_features()

    if not features:
        print("No features computed. Run data_layer.py first.")
    else:
        result = compute_cips(features)
        output = {
            "cips_score":       result.cips_score,
            "confidence":       result.confidence,
            "confidence_raw":   result.confidence_raw,
            "direction":        result.direction,
            "sequence_pattern": result.sequence_pattern,
            "cpii_contributed": result.cpii_contributed,
            "calendar_flags":   result.calendar_flags,
            "components":       result.components,
        }
        print(json.dumps(output, indent=2))
