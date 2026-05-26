"""
Ganji Protocol - Unit Tests
Tests for feature engineering and detection engine.
Run: .venv/bin/python -m pytest tests/ -v
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.features import (
    f1_zscore, f2_cpii, f3_gvci, f4_rss,
    f5_nlp, f6_bpps, f7_calendar, FeatureResult,
)
from engine.detection import compute_cips, DetectionResult


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

def make_rates(currency: str, values: list, start: str = "2024-01-01") -> pd.DataFrame:
    """Creates a minimal rates DataFrame for testing."""
    dates = pd.date_range(start=start, periods=len(values), freq="B")
    return pd.DataFrame({
        "date":     dates,
        "currency": currency,
        "close":    values,
        "source":   "test",
        "flag":     "",
    })


def make_multi_rates(kes: list, ugx: list, tzs: list) -> pd.DataFrame:
    """Creates a multi-currency rates DataFrame."""
    frames = [
        make_rates("KES", kes),
        make_rates("UGX", ugx),
        make_rates("TZS", tzs),
    ]
    return pd.concat(frames, ignore_index=True)


# ─────────────────────────────────────────────
# F1: Z-Score Tests
# ─────────────────────────────────────────────

class TestF1ZScore:

    def test_fires_when_zscore_above_threshold(self):
        # 30 normal values then a spike
        values = [129.0] * 30 + [135.0]
        rates  = make_rates("KES", values)
        result = f1_zscore(rates)
        assert result.fired is True
        assert result.value > 2.0

    def test_does_not_fire_on_normal_values(self):
        values = [129.0 + i * 0.01 for i in range(35)]
        rates  = make_rates("KES", values)
        result = f1_zscore(rates)
        assert result.fired is False

    def test_insufficient_data_returns_not_fired(self):
        rates  = make_rates("KES", [129.0] * 10)
        result = f1_zscore(rates)
        assert result.fired is False

    def test_negative_zscore_fires_on_sharp_drop(self):
        values = [129.0] * 30 + [120.0]
        rates  = make_rates("KES", values)
        result = f1_zscore(rates)
        assert result.fired is True
        assert result.value < -2.0

    def test_status_is_validated(self):
        rates  = make_rates("KES", [129.0] * 35)
        result = f1_zscore(rates)
        assert result.status == "VALIDATED"


# ─────────────────────────────────────────────
# F2: CPII Tests
# ─────────────────────────────────────────────

class TestF2CPII:

    def test_fires_when_kes_diverges_from_basket(self):
        # KES spikes while UGX and TZS stay flat
        kes = [129.0] * 32 + [135.0]
        ugx = [3700.0] * 33
        tzs = [2500.0] * 33
        rates  = make_multi_rates(kes, ugx, tzs)
        result = f2_cpii(rates)
        assert result.fired is True

    def test_does_not_fire_when_all_pairs_move_together(self):
        # All pairs move proportionally (global USD event)
        kes = [129.0 + i * 0.1 for i in range(35)]
        ugx = [3700.0 + i * 3.0 for i in range(35)]
        tzs = [2500.0 + i * 2.0 for i in range(35)]
        rates  = make_multi_rates(kes, ugx, tzs)
        result = f2_cpii(rates)
        assert result.status == "VALIDATED"

    def test_insufficient_data_returns_not_fired(self):
        kes = [129.0] * 10
        ugx = [3700.0] * 10
        tzs = [2500.0] * 10
        rates  = make_multi_rates(kes, ugx, tzs)
        result = f2_cpii(rates)
        assert result.fired is False


# ─────────────────────────────────────────────
# F3: GVCI Tests
# ─────────────────────────────────────────────

class TestF3GVCI:

    def test_fires_when_volatility_suppressed(self):
        # High volatility for 30 days then flat (suppressed)
        import random
        random.seed(42)
        volatile = [129.0 + random.uniform(-2, 2) for _ in range(30)]
        flat     = [129.0] * 6
        rates    = make_rates("KES", volatile + flat)
        result   = f3_gvci(rates)
        assert result.fired is True
        assert result.value < 0.3

    def test_does_not_fire_on_normal_volatility(self):
        import random
        random.seed(42)
        values = [129.0 + random.uniform(-0.5, 0.5) for _ in range(40)]
        rates  = make_rates("KES", values)
        result = f3_gvci(rates)
        assert result.status == "VALIDATED"

    def test_insufficient_data_returns_not_fired(self):
        rates  = make_rates("KES", [129.0] * 20)
        result = f3_gvci(rates)
        assert result.fired is False


# ─────────────────────────────────────────────
# F4: RSS Tests
# ─────────────────────────────────────────────

class TestF4RSS:

    def test_always_returns_not_fired_in_phase1(self):
        result = f4_rss()
        assert result.fired is False
        assert result.status == "HYPOTHESIS"
        assert result.phase == 2


# ─────────────────────────────────────────────
# F5: NLP Tests
# ─────────────────────────────────────────────

class TestF5NLP:

    def test_intervention_imminent_fires(self):
        result = f5_nlp("INTERVENTION_IMMINENT")
        assert result.fired is True
        assert result.value == 2.0

    def test_hawkish_fires(self):
        result = f5_nlp("HAWKISH")
        assert result.fired is True
        assert result.value == 1.0

    def test_neutral_does_not_fire(self):
        result = f5_nlp("NEUTRAL")
        assert result.fired is False
        assert result.value == 0.0

    def test_dovish_does_not_fire_and_is_negative(self):
        result = f5_nlp("DOVISH")
        assert result.fired is False
        assert result.value == -1.0

    def test_case_insensitive(self):
        result = f5_nlp("hawkish")
        assert result.fired is True


# ─────────────────────────────────────────────
# F7: Calendar Tests
# ─────────────────────────────────────────────

class TestF7Calendar:

    def test_budget_month_flagged(self):
        result = f7_calendar(date(2026, 6, 15))
        assert "BUDGET_MONTH" in result.detail["flags"]

    def test_imf_review_month_flagged(self):
        result = f7_calendar(date(2026, 3, 10))
        assert "IMF_REVIEW_MONTH" in result.detail["flags"]

    def test_end_of_month_flagged(self):
        result = f7_calendar(date(2026, 5, 30))
        assert "END_OF_MONTH" in result.detail["flags"]

    def test_normal_day_no_flags(self):
        result = f7_calendar(date(2026, 5, 15))
        assert result.detail["flags"] == []
        assert result.fired is False

    def test_diaspora_peak_flagged(self):
        result = f7_calendar(date(2026, 12, 10))
        assert "DIASPORA_PEAK" in result.detail["flags"]


# ─────────────────────────────────────────────
# Detection Engine Tests
# ─────────────────────────────────────────────

class TestDetectionEngine:

    def _make_feature(self, name, fired, value=0.0, detail=None, status="VALIDATED"):
        from engine.features import FeatureResult
        return FeatureResult(
            name=name, fired=fired, value=value,
            detail=detail or {}, status=status
        )

    def test_high_confidence_requires_cpii_plus_one(self):
        features = {
            "F1": self._make_feature("F1_ZSCORE", True, 2.6),
            "F2": self._make_feature("F2_CPII", True, 2.0),
            "F3": self._make_feature("F3_GVCI", True, 0.2),
            "F4": self._make_feature("F4_RSS", False),
            "F5": self._make_feature("F5_NLP", False, 0.0, {"tone": "NEUTRAL"}),
            "F6": self._make_feature("F6_BPPS", False, 0.0, {"cbk_suppression": False}),
            "F7": self._make_feature("F7_CALENDAR", False, 0.0, {"flags": []}),
        }
        result = compute_cips(features)
        assert result.confidence == "HIGH"
        assert result.cips_score >= 5

    def test_none_confidence_when_no_signals(self):
        features = {
            "F1": self._make_feature("F1_ZSCORE", False, 0.5),
            "F2": self._make_feature("F2_CPII", False, 0.5),
            "F3": self._make_feature("F3_GVCI", False, 0.8),
            "F4": self._make_feature("F4_RSS", False),
            "F5": self._make_feature("F5_NLP", False, 0.0, {"tone": "NEUTRAL"}),
            "F6": self._make_feature("F6_BPPS", False, 0.0, {"cbk_suppression": False}),
            "F7": self._make_feature("F7_CALENDAR", False, 0.0, {"flags": []}),
        }
        result = compute_cips(features)
        assert result.confidence == "NONE"
        assert result.cips_score == 0

    def test_calendar_downgrades_confidence(self):
        features = {
            "F1": self._make_feature("F1_ZSCORE", True, 2.6),
            "F2": self._make_feature("F2_CPII", True, 2.0),
            "F3": self._make_feature("F3_GVCI", True, 0.2),
            "F4": self._make_feature("F4_RSS", False),
            "F5": self._make_feature("F5_NLP", False, 0.0, {"tone": "NEUTRAL"}),
            "F6": self._make_feature("F6_BPPS", False, 0.0, {"cbk_suppression": False}),
            "F7": self._make_feature("F7_CALENDAR", True, 1.0,
                                     {"flags": ["BUDGET_MONTH"]}),
        }
        result = compute_cips(features)
        assert result.confidence == "MEDIUM"
        assert result.confidence_raw == "HIGH"

    def test_kes_support_direction(self):
        features = {
            "F1": self._make_feature("F1_ZSCORE", True, 2.5),
            "F2": self._make_feature("F2_CPII", False),
            "F3": self._make_feature("F3_GVCI", False),
            "F4": self._make_feature("F4_RSS", False),
            "F5": self._make_feature("F5_NLP", False, 0.0, {"tone": "NEUTRAL"}),
            "F6": self._make_feature("F6_BPPS", False, 0.0, {"cbk_suppression": False}),
            "F7": self._make_feature("F7_CALENDAR", False, 0.0, {"flags": []}),
        }
        result = compute_cips(features)
        assert result.direction == "KES_SUPPORT"

    def test_floor_defence_direction(self):
        features = {
            "F1": self._make_feature("F1_ZSCORE", True, -2.5),
            "F2": self._make_feature("F2_CPII", False),
            "F3": self._make_feature("F3_GVCI", False),
            "F4": self._make_feature("F4_RSS", False),
            "F5": self._make_feature("F5_NLP", False, 0.0, {"tone": "NEUTRAL"}),
            "F6": self._make_feature("F6_BPPS", False, 0.0, {"cbk_suppression": False}),
            "F7": self._make_feature("F7_CALENDAR", False, 0.0, {"flags": []}),
        }
        result = compute_cips(features)
        assert result.direction == "KES_FLOOR_DEFENCE"

    def test_dovish_nlp_reduces_score(self):
        features = {
            "F1": self._make_feature("F1_ZSCORE", True, 2.1),
            "F2": self._make_feature("F2_CPII", False),
            "F3": self._make_feature("F3_GVCI", False),
            "F4": self._make_feature("F4_RSS", False),
            "F5": self._make_feature("F5_NLP", False, -1.0, {"tone": "DOVISH"}),
            "F6": self._make_feature("F6_BPPS", False, 0.0, {"cbk_suppression": False}),
            "F7": self._make_feature("F7_CALENDAR", False, 0.0, {"flags": []}),
        }
        result = compute_cips(features)
        assert result.components.get("nlp_tone") == -1
