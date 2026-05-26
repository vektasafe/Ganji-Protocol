"""
Ganji Protocol Configuration
All parameters, thresholds, API endpoints, and data source settings.
No hardcoded values anywhere else in the engine. Everything lives here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
DATA_DIR = BASE_DIR / "data"
SIGNALS_DIR = DATA_DIR / "signals"

RAW_DATA_FILES = {
    "rates":      DATA_DIR / "rates.csv",
    "p2p":        DATA_DIR / "binance_p2p.csv",
    "signal_archive": SIGNALS_DIR / "signal_archive.jsonl",
    "signal_index":   SIGNALS_DIR / "signal_index.csv",
}

# ─────────────────────────────────────────────
# Currency Pairs
# ─────────────────────────────────────────────
EAC_PAIRS = {
    "KES": "USD/KES",
    "UGX": "USD/UGX",
    "TZS": "USD/TZS",
    "RWF": "USD/RWF",
    "ETB": "USD/ETB",
}

YAHOO_TICKERS = {
    "KES": "USDKES=X",
    "UGX": "USDUGX=X",
    "TZS": "USDTZS=X",
    "RWF": "USDRWF=X",
    "ETB": "USDETB=X",
}

PRIMARY_PAIR = "KES"
BASKET_PAIRS = ["UGX", "TZS"]   # used in CPII cross-pair signal

# ─────────────────────────────────────────────
# Data Source API Keys (loaded from .env)
# ─────────────────────────────────────────────
ALPHA_VANTAGE_KEY    = os.getenv("ALPHA_VANTAGE_KEY", "")
TWELVE_DATA_KEY      = os.getenv("TWELVE_DATA_KEY", "")
EXCHANGERATESAPI_KEY = os.getenv("EXCHANGERATESAPI_KEY", "")
FRED_KEY             = os.getenv("FRED_KEY", "")

# ─────────────────────────────────────────────
# Data Source Endpoints
# ─────────────────────────────────────────────
SOURCES = {
    "yahoo_finance": {
        "type":     "library",          # uses yfinance library
        "auth":     False,
        "history":  True,
        "realtime": False,
        "priority": 1,                  # primary source
    },
    "open_er_api": {
        "type":     "rest",
        "url":      "https://open.er-api.com/v6/latest/USD",
        "auth":     False,
        "history":  False,
        "realtime": True,
        "priority": 2,
    },
    "exchangerate_api": {
        "type":     "rest",
        "url":      "https://api.exchangerate-api.com/v4/latest/USD",
        "auth":     False,
        "history":  False,
        "realtime": True,
        "priority": 3,
    },
    "alpha_vantage": {
        "type":     "rest",
        "url":      "https://www.alphavantage.co/query",
        "auth":     True,
        "key_env":  "ALPHA_VANTAGE_KEY",
        "history":  True,
        "realtime": True,
        "priority": 4,
    },
    "twelve_data": {
        "type":     "rest",
        "url":      "https://api.twelvedata.com",
        "auth":     True,
        "key_env":  "TWELVE_DATA_KEY",
        "history":  True,
        "realtime": True,
        "priority": 5,
    },
    "exchangeratesapi_io": {
        "type":     "rest",
        "url":      "https://api.exchangeratesapi.io/v1",
        "auth":     True,
        "key_env":  "EXCHANGERATESAPI_KEY",
        "history":  True,
        "realtime": True,
        "priority": 6,
    },
    "binance_p2p": {
        "type":     "rest",
        "url":      "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
        "auth":     False,
        "history":  False,
        "realtime": True,
        "priority": 1,                  # primary real-time source
    },
}

# ─────────────────────────────────────────────
# Data Quality Thresholds
# ─────────────────────────────────────────────
PLAUSIBLE_RANGE = {
    "KES": (50.0,   200.0),
    "UGX": (2000.0, 5000.0),
    "TZS": (1500.0, 4000.0),
    "RWF": (800.0,  2000.0),
    "ETB": (50.0,   250.0),
}

SPIKE_THRESHOLD       = 0.05    # flag if single-day move > 5%
STALE_DAYS_THRESHOLD  = 2       # flag as stale if no update for > 2 business days
CROSS_CHECK_THRESHOLD = 0.005   # flag if two sources diverge > 0.5%
P2P_MIN_ADS           = 5       # minimum active P2P ads for BPPS to be valid

# ─────────────────────────────────────────────
# Historical Data Settings
# ─────────────────────────────────────────────
HISTORY_YEARS  = 5              # years of daily history to fetch
HISTORY_PERIOD = "5y"           # Yahoo Finance period string

# ─────────────────────────────────────────────
# Detection Engine Parameters (SYSTEM.md Section 3)
# ─────────────────────────────────────────────
ZSCORE_WINDOW              = 30     # rolling window for Z-score (trading days)
ZSCORE_THRESHOLD_LOW       = 2.0    # first-layer trigger
ZSCORE_THRESHOLD_HIGH      = 2.5    # standalone threshold

CPII_WINDOW                = 30     # rolling window for CPII
CPII_THRESHOLD             = 1.5    # standard deviations

GVCI_SHORT_WINDOW          = 5      # short volatility window
GVCI_LONG_WINDOW           = 30     # long volatility window
GVCI_SUPPRESSION_THRESHOLD = 0.3    # GVCI ratio below this = suppression

RSS_DRAWDOWN_THRESHOLD     = 200    # USD millions per week

BPPS_CAPITAL_FLIGHT        = 0.005  # P2P premium > 0.5% = capital flight
BPPS_SUPPRESSION           = -0.005 # P2P premium < -0.5% = CBK suppression

# ─────────────────────────────────────────────
# CIPS Scoring Weights (SYSTEM.md Section 4)
# ─────────────────────────────────────────────
CIPS_WEIGHTS = {
    "z_score_low":              1,
    "z_score_high":             1,
    "cpii":                     3,
    "gvci":                     2,
    "rss":                      2,
    "nlp_intervention_imminent": 2,
    "nlp_hawkish":              1,
    "nlp_neutral":              0,
    "nlp_dovish":               -1,
    "bpps":                     1,
}

CIPS_HIGH_THRESHOLD   = 5
CIPS_MEDIUM_THRESHOLD = 3
CIPS_LOW_THRESHOLD    = 1

# ─────────────────────────────────────────────
# Seasonal Calendar Flags
# ─────────────────────────────────────────────
CALENDAR_FLAGS = {
    "budget_month":        [6],
    "imf_review_months":   [3, 6, 9, 12],
    "diaspora_peak_months": [12, 1],
    "debt_service_months": [3, 9],
}

# ─────────────────────────────────────────────
# Pipeline Schedule
# ─────────────────────────────────────────────
PIPELINE_RUN_TIME = "18:00"     # EAT daily
PIPELINE_TIMEZONE = "Africa/Nairobi"
