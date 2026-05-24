# Ganji Protocol: System Specification

**Author:** James Kabingu, OCTIO-Labs | Vektasafe
**Status:** Living document; Phase 1 specification complete, Phase 2 pending
**Scope:** Engineering specification of the Ganji Protocol detection engine, signal pipeline, proprietary models, and output schema
**Cross-reference:** ALGORITHMS.md (algorithm foundations), BACKTEST.md (validation results), LANDSCAPE.md (data source registry), ENTITIES.md (entity signal map)
**Last updated:** May 2026

---

## Notation

Throughout this document, claims are tagged as follows:

- `[VALIDATED]` Signal or model validated against ground truth data in BACKTEST.md
- `[IMPLEMENTED]` Code exists or pseudocode is specified here; not yet validated
- `[HYPOTHESIS]` Ganji-specific interpretation not yet empirically tested
- `[RESEARCH DIRECTION]` Identified as viable; not yet designed or built

---

## Section 1: System Architecture

### 1.1 Overview

Ganji Protocol is a signal intelligence system. It ingests public financial data, computes detection features, scores them against a composite intervention model, and delivers a structured signal output to subscribers. It does not execute trades. It does not manage capital. It does not issue financial advice.

The system has five layers:

```
┌─────────────────────────────────────────────────────┐
│  Layer 5: Signal Delivery                           │
│  REST API · Webhooks · SMS · Dashboard              │
├─────────────────────────────────────────────────────┤
│  Layer 4: Signal Output                             │
│  JSON schema · Confidence tier · Regulatory filter  │
├─────────────────────────────────────────────────────┤
│  Layer 3: Detection Engine                          │
│  Proprietary models · Composite scoring · Thresholds│
├─────────────────────────────────────────────────────┤
│  Layer 2: Feature Engineering                       │
│  Z-score · Cross-pair · Volatility · NLP · P2P      │
├─────────────────────────────────────────────────────┤
│  Layer 1: Data Ingestion                            │
│  CBK · Bank of Uganda · Bank of Tanzania · Binance  │
└─────────────────────────────────────────────────────┘
```

Each layer is independent. A failure in Layer 1 (data ingestion) does not corrupt Layer 3 (detection engine); it triggers a fallback data source and flags the signal as operating on degraded data. Each layer is described in its own section below.

### 1.2 Data Flow

The daily pipeline executes in the following sequence:

```
18:00 EAT  →  Ingest CBK daily rates (Layer 1)
18:05 EAT  →  Ingest Bank of Uganda rates (Layer 1)
18:05 EAT  →  Ingest Bank of Tanzania rates (Layer 1)
18:10 EAT  →  Query Binance P2P KES/USDT (Layer 1)
18:15 EAT  →  Compute detection features (Layer 2)
18:20 EAT  →  Run proprietary models (Layer 3)
18:25 EAT  →  Compute composite confidence score (Layer 3)
18:30 EAT  →  Generate signal output JSON (Layer 4)
18:35 EAT  →  Deliver to subscribers (Layer 5)
```

Total pipeline runtime: under 35 minutes on a $5/month VPS. No real-time infrastructure required in Phase 1.

### 1.3 Phase Boundaries

| Phase | Data frequency | Detection window | Infrastructure |
|-------|---------------|-----------------|----------------|
| Phase 1 (current) | Weekly proxy (Yahoo Finance) | 5 trading days | Local machine |
| Phase 2 | Daily (CBK scraper) | 1 trading day | Cloud VPS + TimescaleDB |
| Phase 3 | Real-time | Hours | Cloud + streaming pipeline |

Phase boundaries are hard. Phase 2 does not begin until the CBK scraper (SCRAPER.md) is built, validated, and producing clean daily data. Phase 3 does not begin until Phase 2 signals are validated on daily data.

---

## Section 2: Data Ingestion Layer

### 2.1 Design Principles

The ingestion layer has three requirements. First, every data source must be free and publicly accessible without authentication, except where a free API key is available. Second, every data source must have a documented fallback: if the primary source fails, the pipeline continues on degraded data rather than halting. Third, every ingested value is timestamped, sourced, and stored before any computation runs against it. Raw data is never overwritten.

### 2.2 Primary Data Sources

**Source 1: CBK Daily Indicative Rates** `[IMPLEMENTED - Phase 2]`

| Field | Value |
|-------|-------|
| URL | centralbank.go.ke/cbk-indicative-rates |
| Format | HTML table |
| Update time | 12:00 to 16:00 EAT daily |
| Ingestion time | 18:00 EAT (scraper, SCRAPER.md) |
| Phase 1 proxy | Yahoo Finance USDKES=X weekly close |
| Fallback | Commercial bank mean rate (Section 2.3) |

Pairs ingested: KES/USD, KES/UGX, KES/TZS, KES/EUR, KES/GBP.

Raw storage schema:

```
date        | pair    | buying_rate | selling_rate | mean_rate | source
2026-05-23  | KES/USD | 128.20      | 129.50       | 128.85    | CBK
```

**Source 2: Bank of Uganda Daily Rates** `[RESEARCH DIRECTION - Phase 2]`

| Field | Value |
|-------|-------|
| URL | bou.or.ug/statistics |
| Format | HTML table or downloadable CSV |
| Pairs ingested | UGX/USD |
| Fallback | Previous day's rate (stale flag applied) |

**Source 3: Bank of Tanzania Daily Rates** `[RESEARCH DIRECTION - Phase 2]`

| Field | Value |
|-------|-------|
| URL | bot.go.tz/exchange-rates |
| Format | HTML table |
| Pairs ingested | TZS/USD |
| Fallback | Previous day's rate (stale flag applied) |

**Source 4: Binance P2P KES/USDT** `[IMPLEMENTED - Phase 1]`

| Field | Value |
|-------|-------|
| Endpoint | p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search |
| Authentication | None required |
| Method | POST with JSON payload |
| Update frequency | Real-time; queried at pipeline execution |
| Fallback | Previous query result (stale flag applied) |

Fields extracted per query: min price, max price, mean price across top 20 ads, spread, active ad count, payment methods present.

Raw storage schema:

```
timestamp           | min_price | max_price | mean_price | spread | ad_count
2026-05-23T18:10Z   | 129.35    | 129.70    | 129.52     | 0.35   | 20
```

**Source 5: CBK Weekly Bulletin** `[HYPOTHESIS - Phase 2]`

| Field | Value |
|-------|-------|
| URL | centralbank.go.ke/publications/weekly-bulletin |
| Format | PDF |
| Update frequency | Weekly (Friday) |
| Fields extracted | Foreign exchange reserves (USD millions), interbank rate |
| Extraction method | PDF parser (pdfplumber or PyMuPDF) |
| Fallback | Previous week's bulletin (stale flag applied) |

The reserve drawdown signal (Section 3.5) depends on this source. It is the only PDF source in the pipeline and requires a dedicated parser.

**Source 6: CBK MPC Press Statements** `[IMPLEMENTED - Phase 1 NLP]`

| Field | Value |
|-------|-------|
| URL | centralbank.go.ke/press-releases |
| Format | HTML or PDF |
| Update frequency | 6 times per year |
| Processing | Gemma 4 NLP classifier (Section 3.6) |
| Fallback | Previous statement classification retained until new statement published |

### 2.3 Fallback Hierarchy

When a primary source fails, the pipeline applies the following fallback hierarchy in order:

```
1. Primary source (CBK, Bank of Uganda, Bank of Tanzania, Binance P2P)
2. Commercial bank mean rate (mean of 9 Tier 1 bank published rates)
3. Previous day's value with STALE flag applied to signal output
4. Pipeline halt with ERROR flag; no signal published
```

The commercial bank mean rate fallback requires scraping nine bank websites (documented in ENTITIES.md Entity 2.2). This is a Phase 2 capability. In Phase 1, the fallback is previous day's value with STALE flag.

### 2.4 Data Quality Checks

Every ingested value passes three quality checks before entering the feature engineering layer.

**Check 1: Range validation**

KES/USD must fall within a plausible range. The historical range since 2000 is approximately 60 to 165. Any value outside 50 to 200 is flagged as a data error and the fallback value is used.

```python
PLAUSIBLE_RANGE = {
    "KES/USD": (50.0, 200.0),
    "KES/UGX": (0.020, 0.060),
    "KES/TZS": (0.010, 0.040),
}

def range_check(pair: str, value: float) -> bool:
    low, high = PLAUSIBLE_RANGE[pair]
    return low <= value <= high
```

**Check 2: Spike detection**

A single-day move exceeding 5% on KES/USD is flagged for review. It may be a genuine intervention event (in which case it is a signal) or a data error (in which case it should be excluded). The pipeline flags it and includes it in the signal output with a SPIKE_DETECTED annotation.

```python
def spike_check(today: float, yesterday: float, threshold: float = 0.05) -> bool:
    return abs((today - yesterday) / yesterday) > threshold
```

**Check 3: Staleness check**

If the CBK has not published a new rate for more than 2 business days (public holiday or system outage), the stored value is marked STALE and the signal output includes a DATA_STALE warning.

### 2.5 Raw Data Store

All ingested data is stored in append-only CSV files in Phase 1, upgrading to TimescaleDB in Phase 2. The append-only constraint is absolute: no historical value is ever modified. Corrections are appended as new rows with a CORRECTED flag and a reference to the original row.

```
data/
  cbk_rates.csv          # CBK daily rates (Phase 2: scraped; Phase 1: manual)
  bou_rates.csv          # Bank of Uganda daily rates
  bot_rates.csv          # Bank of Tanzania daily rates
  binance_p2p.csv        # Binance P2P KES/USDT snapshots
  cbk_reserves.csv       # CBK weekly forex reserves
  cbk_nlp.csv            # NLP classification outputs per MPC statement
```

---

## Section 3: Feature Engineering

### 3.1 Design Principles

Feature engineering transforms raw ingested rates into the detection inputs that the proprietary models consume. Every feature has four properties: a precise mathematical definition, an exact parameter set, a documented academic or empirical basis, and a phase tag indicating when it is available.

No feature is computed from future data. All rolling windows use only data available at computation time. This constraint is enforced at the code level, not assumed.

### 3.2 Feature 1: KES/USD Z-Score Deviation `[VALIDATED]`

**Definition:**

$$Z_t = \frac{P_t - \mu_{30}(P)}{\sigma_{30}(P)}$$

where $P_t$ is the KES/USD mean rate on day $t$, $\mu_{30}(P)$ is the 30-day rolling mean, and $\sigma_{30}(P)$ is the 30-day rolling standard deviation.

**Parameters:**

| Parameter | Value | Basis |
|-----------|-------|-------|
| Rolling window | 30 trading days | BACKTEST.md Phase 1 validation |
| Standalone threshold | 2.5 | Reduces false positives to ~4/year (BACKTEST.md Part 6) |
| Composite trigger threshold | 2.0 | First-layer trigger; requires corroboration |

**Implementation:**

```python
def z_score(rates: pd.Series, window: int = 30) -> pd.Series:
    return (rates - rates.rolling(window).mean()) / rates.rolling(window).std()
```

**Validation results (BACKTEST.md Part 3.1):**

| Metric | Value |
|--------|-------|
| Recall | 1.00 (fired before all 4 ground truth events) |
| Precision (standalone, threshold 2.0) | 0.36 |
| Estimated false positives per year | 6 to 8 |

**Interpretation:** High recall, low standalone precision. Functions as a sensitive first-layer trigger. Requires corroboration from Features 2 or 3 before escalating confidence.

---

### 3.3 Feature 2: Cross-Pair Inconsistency Index (CPII) `[VALIDATED]`

**Definition:**

A genuine USD movement affects KES, UGX, and TZS proportionally. A CBK-specific intervention affects KES while UGX and TZS remain stable. The Cross-Pair Inconsistency Index (CPII) measures this divergence.

Step 1: Compute the daily return for each pair:

$$r_{KES,t} = \frac{P_{KES/USD,t} - P_{KES/USD,t-1}}{P_{KES/USD,t-1}}$$

$$r_{UGX,t} = \frac{P_{UGX/USD,t} - P_{UGX/USD,t-1}}{P_{UGX/USD,t-1}}$$

$$r_{TZS,t} = \frac{P_{TZS/USD,t} - P_{TZS/USD,t-1}}{P_{TZS/USD,t-1}}$$

Step 2: Compute the EAC basket return (equal-weighted mean of UGX and TZS):

$$r_{basket,t} = \frac{r_{UGX,t} + r_{TZS,t}}{2}$$

Step 3: Compute the divergence of KES from the basket:

$$CPII_t = r_{KES,t} - r_{basket,t}$$

Step 4: Normalise as a Z-score over a 30-day rolling window:

$$CPII\_Z_t = \frac{CPII_t - \mu_{30}(CPII)}{\sigma_{30}(CPII)}$$

**Signal fires when:** $|CPII\_Z_t| > 1.5$

**Parameters:**

| Parameter | Value | Basis |
|-----------|-------|-------|
| Basket composition | UGX/USD, TZS/USD (equal weight) | EAC trade flow correlation |
| Rolling window | 30 trading days | Consistent with Feature 1 |
| Threshold | 1.5 standard deviations | BACKTEST.md Phase 1 validation |

**Implementation:**

```python
def cross_pair_inconsistency(
    kes_usd: pd.Series,
    ugx_usd: pd.Series,
    tzs_usd: pd.Series,
    window: int = 30,
    threshold: float = 1.5
) -> pd.Series:
    r_kes = kes_usd.pct_change()
    r_basket = (ugx_usd.pct_change() + tzs_usd.pct_change()) / 2
    cpii = r_kes - r_basket
    cpii_z = (cpii - cpii.rolling(window).mean()) / cpii.rolling(window).std()
    return cpii_z.abs() > threshold
```

**Validation results (BACKTEST.md Part 3.2):**

| Metric | Value |
|--------|-------|
| Recall | 0.90 |
| Estimated precision | 0.85 to 0.90 |
| Estimated false positives per year | 1 to 2 |

**Interpretation:** The highest-precision signal in the detection layer. Receives the highest weight (3 points) in the composite scoring function. The primary failure mode is a global USD event that moves all three pairs simultaneously, masking a concurrent CBK intervention.

---

### 3.4 Feature 3: Ganji Volatility Compression Index (GVCI) `[VALIDATED]`

**Definition:**

The GVCI measures the degree to which KES/USD volatility is being artificially suppressed relative to its historical norm. When the CBK is defending a price level, it absorbs orders on both sides of the market, compressing the daily range. The GVCI detects this compression.

Step 1: Compute the 5-day rolling standard deviation of daily KES/USD returns:

$$\sigma_{5,t} = \text{std}(r_{KES,t-4}, \ldots, r_{KES,t})$$

Step 2: Compute the 30-day rolling standard deviation:

$$\sigma_{30,t} = \text{std}(r_{KES,t-29}, \ldots, r_{KES,t})$$

Step 3: Compute the GVCI as the ratio of short-term to long-term volatility:

$$GVCI_t = \frac{\sigma_{5,t}}{\sigma_{30,t}}$$

Step 4: Signal fires when GVCI falls below the suppression threshold:

$$\text{Suppression signal}: \quad GVCI_t < \theta_{suppress}$$

**Parameters:**

| Parameter | Value | Basis |
|-----------|-------|-------|
| Short-term window | 5 trading days | BACKTEST.md Phase 1 validation |
| Long-term window | 30 trading days | Consistent with Features 1 and 2 |
| Suppression threshold ($\theta_{suppress}$) | 0.3 | BACKTEST.md Part 3.3 |

**Implementation:**

```python
def gvci(rates: pd.Series, short_window: int = 5,
         long_window: int = 30, threshold: float = 0.3) -> pd.Series:
    returns = rates.pct_change()
    sigma_short = returns.rolling(short_window).std()
    sigma_long = returns.rolling(long_window).std()
    ratio = sigma_short / sigma_long
    return ratio < threshold
```

**Validation results (BACKTEST.md Part 3.3):**

| Metric | Value |
|--------|-------|
| Recall | 0.90 |
| Estimated precision | 0.70 |
| Estimated false positives per year | 3 to 5 |

**Interpretation:** A corroborating signal. Fires before and during active CBK price defence. The primary false positive source is low-volatility periods that are not caused by intervention (holiday periods, thin summer trading). The seasonal calendar filter (Section 3.8) reduces this false positive rate.

---

### 3.5 Feature 4: Reserve Stress Signal (RSS) `[HYPOTHESIS - Phase 2]`

**Definition:**

The CBK publishes weekly foreign exchange reserve levels in its weekly bulletin. A sudden reserve drawdown signals CBK dollar sales to defend the shilling.

$$RSS_t = R_{t-1} - R_t$$

where $R_t$ is the foreign exchange reserve level in USD millions in week $t$.

**Signal fires when:**

$$RSS_t > \$200\text{M} \quad \text{and} \quad \text{no scheduled debt payment in week } t$$

**Parameters:**

| Parameter | Value | Basis |
|-----------|-------|-------|
| Drawdown threshold | $200 million per week | ENTITIES.md Entity 2.1; CBK historical data |
| Debt payment calendar | Kenya external debt schedule | treasury.go.ke |
| Data source | CBK weekly bulletin (PDF) | centralbank.go.ke/publications/weekly-bulletin |
| Data lag | 1 week | CBK publication schedule |

**Status note:** This signal is tagged `[HYPOTHESIS]` because the $200 million threshold has not been empirically validated against the ground truth event set. The threshold is derived from ENTITIES.md Entity 2.1 documentation. Phase 2 validation will test this threshold against the CBK reserve data for the four ground truth events.

---

### 3.6 Feature 5: CBK NLP Tone Classification `[IMPLEMENTED]`

**Definition:**

The CBK MPC press statement is classified into one of four tone categories using Gemma 4. The classification is a discrete feature, not a continuous one.

**Tone categories:**

| Category | Definition | Market implication |
|----------|-----------|-------------------|
| DOVISH | Language signals rate cuts or accommodation | KES depreciation pressure |
| NEUTRAL | No directional signal | No implication |
| HAWKISH | Language signals rate hikes or tightening | KES appreciation pressure |
| INTERVENTION_IMMINENT | Explicit language about exchange rate stability, orderly markets, or reserve adequacy | CBK intervention likely within 1 to 14 days |

**Key phrases mapped to INTERVENTION_IMMINENT:**

- "excessive volatility"
- "orderly market conditions"
- "foreign exchange reserves remain adequate"
- "the Committee will continue to monitor"
- "disorderly market conditions"
- "exchange rate stability"

**Prompt template:**

```python
PROMPT = """
You are a central bank communication analyst for East African forex markets.

Analyse this CBK press statement and classify its tone:

{statement_text}

Respond in JSON only:
{{
    "tone": "DOVISH" or "NEUTRAL" or "HAWKISH" or "INTERVENTION_IMMINENT",
    "key_phrases": ["list of phrases that drove the classification"],
    "intervention_probability": "LOW" or "MEDIUM" or "HIGH",
    "reasoning": "one sentence"
}}
"""
```

**Signal contribution to composite score:**

| Tone | Score contribution |
|------|--------------------|
| INTERVENTION_IMMINENT | +2 |
| HAWKISH | +1 |
| NEUTRAL | 0 |
| DOVISH | -1 (reduces composite score) |

**Status note:** The NLP classifier is implemented and the prompt is defined. Empirical validation against the four ground truth events (do MPC statements preceding each event classify as HAWKISH or INTERVENTION_IMMINENT?) is pending and constitutes part of Phase 2 validation.

---

### 3.7 Feature 6: Binance P2P Premium Signal (BPPS) `[IMPLEMENTED - Phase 1]`

**Definition:**

The Binance P2P KES/USDT mean price is compared to the CBK official KES/USD rate. The premium measures the degree to which the informal market is pricing KES differently from the official rate.

$$BPPS_t = \frac{P_{P2P,t} - P_{CBK,t}}{P_{CBK,t}}$$

**Signal fires when:**

$$BPPS_t > 0.005 \quad \text{(capital flight: P2P premium > 0.5\%)}$$

$$BPPS_t < -0.005 \quad \text{(CBK suppression: official rate above P2P)}$$

**Parameters:**

| Parameter | Value | Basis |
|-----------|-------|-------|
| Capital flight threshold | +0.5% | ENTITIES.md Entity 3.5; observed P2P data |
| Suppression threshold | -0.5% | ENTITIES.md Entity 3.5 |
| Normal liquidity premium | 0.3 to 0.5% | Live Binance P2P API query, May 2026 |

**Implementation:**

```python
def binance_p2p_premium(p2p_mean: float, cbk_rate: float,
                         threshold: float = 0.005) -> dict:
    premium = (p2p_mean - cbk_rate) / cbk_rate
    return {
        "premium": premium,
        "capital_flight": premium > threshold,
        "cbk_suppression": premium < -threshold,
        "normal": abs(premium) <= threshold
    }
```

**Observed baseline (May 2026):** P2P mean 129.52 KES/USDT vs CBK rate ~129.00 KES/USD. Premium: +0.40%. Within normal liquidity premium range. No signal.

---

### 3.8 Feature 7: Seasonal Calendar Filter `[IMPLEMENTED]`

**Definition:**

Certain calendar events create predictable KES volatility that is not caused by CBK intervention. The seasonal calendar filter reduces false positives by flagging periods where non-intervention volatility is expected.

**High-volatility calendar events (KES/USD):**

| Event | Typical timing | Effect on KES |
|-------|---------------|---------------|
| Kenya budget statement | June | High volatility; direction depends on fiscal stance |
| IMF quarterly review | March, June, September, December | KES appreciation on positive review |
| US Non-Farm Payrolls | First Friday of each month | USD volatility; affects all EM currencies |
| Kenya general election | August 2027 (next) | KES depreciation pressure 6 to 12 months prior |
| End of month | Last 3 business days | Corporate USD demand; mild KES depreciation |
| December to January | Annual | Diaspora remittance inflows; KES support |
| March and September | Annual | Government external debt service; USD demand |

**Implementation:**

```python
CALENDAR_FLAGS = {
    "budget_month": [6],
    "imf_review_months": [3, 6, 9, 12],
    "diaspora_peak_months": [12, 1],
    "debt_service_months": [3, 9],
}

def calendar_flag(date: pd.Timestamp) -> list[str]:
    flags = []
    if date.month in CALENDAR_FLAGS["budget_month"]:
        flags.append("BUDGET_MONTH")
    if date.month in CALENDAR_FLAGS["imf_review_months"]:
        flags.append("IMF_REVIEW_MONTH")
    if date.month in CALENDAR_FLAGS["diaspora_peak_months"]:
        flags.append("DIASPORA_PEAK")
    if date.month in CALENDAR_FLAGS["debt_service_months"]:
        flags.append("DEBT_SERVICE_MONTH")
    return flags
```

Calendar flags are appended to the signal output as context. They do not suppress signals; they annotate them. A HIGH confidence signal during a debt service month is still published, but the output includes DEBT_SERVICE_MONTH in the context field so the subscriber can weight it accordingly.

---

### 3.9 Feature Summary Table

| Feature | Name | Phase | Status | Precision | Recall |
|---------|------|-------|--------|-----------|--------|
| F1 | KES/USD Z-Score | 1 | VALIDATED | 0.36 | 1.00 |
| F2 | Cross-Pair Inconsistency Index (CPII) | 2 | VALIDATED | 0.87 | 0.90 |
| F3 | Ganji Volatility Compression Index (GVCI) | 1 | VALIDATED | 0.70 | 0.90 |
| F4 | Reserve Stress Signal (RSS) | 2 | HYPOTHESIS | TBD | TBD |
| F5 | CBK NLP Tone Classification | 1 | IMPLEMENTED | TBD | TBD |
| F6 | Binance P2P Premium Signal (BPPS) | 1 | IMPLEMENTED | TBD | TBD |
| F7 | Seasonal Calendar Filter | 1 | IMPLEMENTED | N/A | N/A |

---

## Section 4: The Detection Engine

### 4.1 Design Principles

The detection engine takes the seven features computed in Section 3 and produces a single output: the CBK Intervention Probability Score (CIPS) and its corresponding confidence tier. The engine has three properties.

First, it is deterministic. Given the same feature inputs, it always produces the same output. There is no randomness, no model drift, and no retraining cycle in Phase 1. The scoring function is a fixed weighted sum, not a learned model.

Second, it is transparent. Every component of the score is visible in the signal output. A subscriber can see exactly which features fired, what their values were, and how they contributed to the final score. There are no black-box components in Phase 1.

Third, it is conservative. The HIGH confidence tier requires multiple independent signals to fire simultaneously. A single signal, no matter how strong, cannot produce a HIGH confidence output alone. This design choice accepts a lower recall rate in exchange for a lower false positive rate.

### 4.2 The CBK Intervention Probability Score (CIPS)

The CIPS is the composite score that aggregates all feature signals into a single intervention probability measure. It is computed as a weighted sum of binary signal outputs.

**Scoring function:**

```python
def compute_cips(
    z_score: float,
    cpii_fired: bool,
    gvci_fired: bool,
    rss_fired: bool,
    nlp_tone: str,
    bpps: dict,
    calendar_flags: list[str]
) -> dict:
    """
    Computes the CBK Intervention Probability Score (CIPS).
    Returns score, confidence tier, and component breakdown.

    Weights based on Phase 1 backtesting (BACKTEST.md Part 4):
    - F1 Z-score: 1 point at threshold 2.0; 2 points at threshold 2.5
    - F2 CPII: 3 points (highest precision signal)
    - F3 GVCI: 2 points (corroborating signal)
    - F4 RSS: 2 points (Phase 2; not included in Phase 1 score)
    - F5 NLP tone: -1 to +2 points
    - F6 BPPS: 1 point per direction fired
    """
    score = 0
    components = {}

    # F1: Z-score
    if abs(z_score) > 2.0:
        score += 1
        components["z_score_low"] = 1
    if abs(z_score) > 2.5:
        score += 1
        components["z_score_high"] = 1

    # F2: Cross-Pair Inconsistency Index
    if cpii_fired:
        score += 3
        components["cpii"] = 3

    # F3: Ganji Volatility Compression Index
    if gvci_fired:
        score += 2
        components["gvci"] = 2

    # F4: Reserve Stress Signal (Phase 2 only)
    if rss_fired:
        score += 2
        components["rss"] = 2

    # F5: NLP tone
    nlp_scores = {
        "INTERVENTION_IMMINENT": 2,
        "HAWKISH": 1,
        "NEUTRAL": 0,
        "DOVISH": -1
    }
    nlp_contribution = nlp_scores.get(nlp_tone, 0)
    score += nlp_contribution
    components["nlp_tone"] = nlp_contribution

    # F6: Binance P2P Premium Signal
    if bpps.get("capital_flight") or bpps.get("cbk_suppression"):
        score += 1
        components["bpps"] = 1

    # Confidence tier
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
        "calendar_flags": calendar_flags
    }
```

### 4.3 Confidence Tier Definitions

| Tier | Score | Meaning | Estimated false positives per year | Phase 1 validated |
|------|-------|---------|-----------------------------------|-------------------|
| HIGH | >= 5 | Multiple independent signals corroborate. CBK intervention highly probable. | 1 to 2 | Yes |
| MEDIUM | 3 to 4 | Two signals corroborate or one strong signal. Elevated intervention probability. | 4 to 6 | Yes |
| LOW | 1 to 2 | Single weak signal. Monitor; do not act. | 8 to 12 | Yes |
| NONE | 0 | No signals active. Normal market conditions. | N/A | Yes |

**HIGH confidence requires:** CPII fired (3 points) plus at least one of Z-score > 2.5 (2 points), GVCI fired (2 points), or NLP INTERVENTION_IMMINENT (2 points). This combination fired correctly before all four ground truth events in BACKTEST.md.

### 4.4 Signal Direction Classification

The CIPS score measures intervention probability but not direction. Direction is classified separately.

**Direction classification logic:**

```python
def classify_direction(z_score: float, bpps: dict) -> str:
    """
    Classifies the direction of the detected intervention.

    KES_SUPPORT: CBK selling USD to prevent KES depreciation.
    KES_FLOOR_DEFENCE: CBK buying USD to prevent excessive KES appreciation.
    INDETERMINATE: Direction cannot be determined from available signals.
    """
    if z_score > 2.0 and not bpps.get("cbk_suppression"):
        return "KES_SUPPORT"
    elif z_score < -2.0 or bpps.get("cbk_suppression"):
        return "KES_FLOOR_DEFENCE"
    else:
        return "INDETERMINATE"
```

**Documented direction examples from ground truth events:**

| Event | Z-score direction | BPPS | Classified direction |
|-------|------------------|------|---------------------|
| Event 1 (Sep 2023) | +2.3 (KES depreciating) | Normal | KES_SUPPORT |
| Event 2 (Feb 2024) | +3.1 (KES depreciating) | Normal | KES_SUPPORT |
| Event 3 (Mar 2024) | -2.6 (KES appreciating) | Normal | KES_FLOOR_DEFENCE |
| Event 4 (Apr 2024) | -2.1 (KES appreciating) | Normal | KES_FLOOR_DEFENCE |

### 4.5 Manipulation vs Normal Volatility: The Differentiation Logic

This is the core detection problem. The engine differentiates CBK intervention from normal market volatility using three criteria applied in sequence.

**Criterion 1: Magnitude without news catalyst**

Normal volatility is driven by news events (US NFP, Fed decision, Kenya budget). CBK intervention creates price movements that are large relative to the absence of a scheduled news catalyst. The seasonal calendar filter (Feature 7) identifies scheduled high-volatility events. A large Z-score on a day with no calendar flag is more likely to be intervention than a large Z-score on a US NFP day.

```python
def news_adjusted_confidence(cips: dict, calendar_flags: list[str]) -> str:
    high_impact_flags = {"BUDGET_MONTH", "IMF_REVIEW_MONTH"}
    if any(f in high_impact_flags for f in calendar_flags):
        # Downgrade confidence by one tier during high-impact calendar events
        tier_map = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "NONE", "NONE": "NONE"}
        return tier_map[cips["confidence"]]
    return cips["confidence"]
```

**Criterion 2: Cross-pair specificity**

Normal USD volatility moves KES, UGX, and TZS proportionally. CBK intervention moves KES while UGX and TZS remain stable. The CPII (Feature 2) is the primary differentiator. A HIGH confidence signal that includes CPII is almost certainly intervention. A HIGH confidence signal without CPII (score built from Z-score + GVCI + NLP alone) is possible but less certain.

The signal output explicitly flags whether CPII contributed to the score:

```json
"cpii_contributed": true,
"cpii_note": "KES moved 2.1 std dev while UGX and TZS basket moved 0.3 std dev"
```

**Criterion 3: Volatility pattern**

Normal volatility is random. CBK intervention creates a specific volatility pattern: high volatility before the intervention (the market is moving against the CBK's desired level), then compressed volatility during the intervention (the CBK is absorbing orders), then a sharp move when the intervention ends or is overwhelmed.

The GVCI (Feature 3) detects the compression phase. A sequence of GVCI suppression followed by a Z-score spike is the strongest intervention signature in the detection layer.

```python
def sequence_pattern(gvci_history: pd.Series, z_score_history: pd.Series,
                     lookback: int = 5) -> bool:
    """
    Returns True if GVCI suppression preceded a Z-score spike within
    the lookback window. This is the strongest intervention signature.
    """
    recent_suppression = gvci_history.tail(lookback).any()
    current_spike = abs(z_score_history.iloc[-1]) > 2.0
    return recent_suppression and current_spike
```

### 4.6 Detection Engine Failure Modes

| Failure mode | Condition | Effect on output | Mitigation |
|-------------|-----------|-----------------|------------|
| Global risk-off event | VIX > 30; all EM currencies fall simultaneously | CPII fails (all pairs move together); false negative | Add VIX as global context filter (Phase 2) |
| CBK intervention during US NFP | Large USD move coincides with CBK action | CPII may not fire; confidence downgraded | Calendar flag annotates output |
| Data staleness | CBK or central bank source unavailable | STALE flag; confidence capped at MEDIUM | Fallback hierarchy (Section 2.3) |
| P2P market illiquidity | Fewer than 5 active Binance P2P ads | BPPS unreliable | Ad count check; BPPS excluded if ad_count < 5 |
| NLP model hallucination | Gemma 4 misclassifies CBK statement | NLP contribution incorrect | NLP contribution capped at +2; cannot alone produce HIGH confidence |

### 4.7 The Detection Pipeline: Full Pseudocode

```python
def run_detection_pipeline(date: pd.Timestamp) -> dict:
    # Layer 1: Ingest
    cbk = load_cbk_rates(date)
    bou = load_bou_rates(date)
    bot = load_bot_rates(date)
    p2p = query_binance_p2p()
    nlp_tone = load_latest_nlp_classification()

    # Layer 2: Quality checks
    cbk = apply_quality_checks(cbk)
    bou = apply_quality_checks(bou)
    bot = apply_quality_checks(bot)

    # Layer 2: Feature engineering
    f1 = z_score(cbk["KES/USD"])
    f2 = cross_pair_inconsistency(cbk["KES/USD"], bou["UGX/USD"], bot["TZS/USD"])
    f3 = gvci(cbk["KES/USD"])
    f4 = False  # Phase 2
    f5 = nlp_tone
    f6 = binance_p2p_premium(p2p["mean_price"], cbk["KES/USD"].iloc[-1])
    f7 = calendar_flag(date)

    # Layer 3: Detection engine
    cips = compute_cips(f1.iloc[-1], f2.iloc[-1], f3.iloc[-1],
                        f4, f5, f6, f7)
    direction = classify_direction(f1.iloc[-1], f6)
    sequence = sequence_pattern(f3, f1)
    confidence = news_adjusted_confidence(cips, f7)

    # Layer 4: Signal output
    return build_signal_output(date, cips, confidence, direction,
                               sequence, f1, f2, f3, f6, f7)
```

---

## Section 5: Signal Output Schema

### 5.1 Design Principles

The signal output is the contract between the detection engine and the subscriber. It has four requirements.

First, it is machine-readable. Every field has a defined type, a defined set of possible values, and a defined meaning. A trading bot can consume it without human interpretation.

Second, it is self-explanatory. A human reading the output without prior knowledge of Ganji Protocol can understand what fired, why, and what the data shows. The signal_context field carries the plain-language explanation.

Third, it is regulatorily compliant. The output contains no recommended_action field. It describes market conditions; it does not instruct the subscriber what to do. This is the boundary between signal intelligence (no CMA licence required) and financial advice (CMA licence required under the Capital Markets Act).

Fourth, it is auditable. Every output is stored with a unique signal_id. Historical outputs are never modified. The full history of signal firings is queryable via the API.

### 5.2 Full Signal Output Schema

```json
{
  "signal_id": "GP-2026-05-23-001",
  "pair": "KES/USD",
  "timestamp": "2026-05-23T18:30:00Z",
  "data_date": "2026-05-23",
  "pipeline_version": "1.0.0",

  "detection": {
    "cips_score": 6,
    "confidence": "HIGH",
    "direction": "KES_SUPPORT",
    "sequence_pattern_detected": true,
    "cpii_contributed": true
  },

  "components": {
    "z_score": {
      "value": 2.7,
      "threshold_low_fired": true,
      "threshold_high_fired": true,
      "points": 2
    },
    "cpii": {
      "fired": true,
      "cpii_z_value": 2.1,
      "kes_return": 0.018,
      "basket_return": 0.003,
      "divergence": 0.015,
      "points": 3
    },
    "gvci": {
      "fired": true,
      "gvci_value": 0.24,
      "threshold": 0.30,
      "points": 2
    },
    "rss": {
      "available": false,
      "phase": 2,
      "points": 0
    },
    "nlp_tone": {
      "tone": "HAWKISH",
      "key_phrases": ["orderly market conditions", "adequate reserves"],
      "intervention_probability": "HIGH",
      "statement_date": "2026-05-15",
      "points": 1
    },
    "bpps": {
      "p2p_mean": 129.52,
      "cbk_rate": 129.00,
      "premium": 0.004,
      "capital_flight": false,
      "cbk_suppression": false,
      "points": 0
    }
  },

  "context": {
    "calendar_flags": ["IMF_REVIEW_MONTH"],
    "confidence_before_calendar_adjustment": "HIGH",
    "confidence_after_calendar_adjustment": "MEDIUM",
    "data_quality": {
      "cbk_rates": "FRESH",
      "bou_rates": "FRESH",
      "bot_rates": "STALE",
      "binance_p2p": "FRESH",
      "stale_sources": ["bot_rates"]
    },
    "spike_detected": false
  },

  "signal_context": "Z-score deviation of 2.7 sigma combined with cross-pair inconsistency (KES moved 1.8% while UGX/TZS basket moved 0.3%) and volatility suppression (GVCI 0.24, below threshold 0.30). Pattern is consistent with active CBK price defence. NLP classification of the May 15 MPC statement is HAWKISH with key phrases indicating exchange rate concern. Note: IMF review month; confidence adjusted from HIGH to MEDIUM. Bank of Tanzania rate is stale; cross-pair signal uses previous day TZS value.",

  "regulatory_note": "This output is signal intelligence based on statistical analysis of public data. It is not financial advice. No action is recommended or implied. The subscriber determines how to use this information."
}
```

### 5.3 Field Definitions

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| signal_id | string | Unique identifier. Format: GP-{YYYY}-{MM}-{DD}-{sequence} |
| pair | string | Currency pair monitored. Phase 1: KES/USD only |
| timestamp | ISO 8601 | UTC timestamp of signal generation |
| data_date | ISO 8601 date | The trading date the signal covers |
| pipeline_version | semver | Version of the detection pipeline that produced this output |

**detection object:**

| Field | Type | Possible values | Description |
|-------|------|----------------|-------------|
| cips_score | integer | 0 to 12 | Raw composite score before calendar adjustment |
| confidence | string | HIGH, MEDIUM, LOW, NONE | Confidence tier after calendar adjustment |
| direction | string | KES_SUPPORT, KES_FLOOR_DEFENCE, INDETERMINATE | Classified intervention direction |
| sequence_pattern_detected | boolean | true, false | Whether GVCI suppression preceded Z-score spike |
| cpii_contributed | boolean | true, false | Whether CPII fired and contributed to score |

**context object:**

| Field | Type | Description |
|-------|------|-------------|
| calendar_flags | array of strings | Active calendar flags from Feature 7 |
| confidence_before_calendar_adjustment | string | Confidence tier before calendar downgrade |
| confidence_after_calendar_adjustment | string | Final published confidence tier |
| data_quality | object | Freshness status of each data source |
| spike_detected | boolean | Whether a >5% single-day move was detected |

**Prohibited fields:**

The following fields must never appear in the signal output:

| Prohibited field | Reason |
|-----------------|--------|
| recommended_action | Constitutes financial advice under the Capital Markets Act |
| buy | Constitutes financial advice |
| sell | Constitutes financial advice |
| position_size | Constitutes financial advice |
| stop_loss | Constitutes financial advice |
| take_profit | Constitutes financial advice |

### 5.4 Signal Storage Schema

Every signal output is stored in the signal archive immediately after generation. The archive is append-only.

```
signals/
  signal_archive.jsonl    # One JSON object per line; append-only
  signal_index.csv        # Lightweight index: signal_id, date, confidence, direction
```

The JSONL format allows efficient streaming reads for historical queries without loading the full archive into memory.

### 5.5 Null Signal Output

When the pipeline produces a NONE confidence score, a null signal is still published. This confirms to subscribers that the pipeline ran successfully and found no anomaly. A missing output is ambiguous (did the pipeline fail or did nothing fire?). A null signal is unambiguous.

```json
{
  "signal_id": "GP-2026-05-22-001",
  "pair": "KES/USD",
  "timestamp": "2026-05-22T18:30:00Z",
  "data_date": "2026-05-22",
  "pipeline_version": "1.0.0",
  "detection": {
    "cips_score": 0,
    "confidence": "NONE",
    "direction": "INDETERMINATE",
    "sequence_pattern_detected": false,
    "cpii_contributed": false
  },
  "signal_context": "No anomalous signals detected. KES/USD within normal volatility range. Cross-pair consistency normal. Volatility regime normal.",
  "regulatory_note": "This output is signal intelligence based on statistical analysis of public data. It is not financial advice."
}
```

### 5.6 Error Output

When the pipeline fails (data ingestion error, computation error, or output generation error), an error signal is published instead of a null signal.

```json
{
  "signal_id": "GP-2026-05-21-001",
  "pair": "KES/USD",
  "timestamp": "2026-05-21T18:35:00Z",
  "data_date": "2026-05-21",
  "pipeline_version": "1.0.0",
  "detection": null,
  "error": {
    "code": "DATA_INGESTION_FAILURE",
    "source": "cbk_rates",
    "message": "CBK rates page returned HTTP 503. Fallback to previous day value applied. Signal published on degraded data.",
    "degraded": true
  },
  "signal_context": "Pipeline ran on degraded data. CBK rates unavailable; previous day value used. Treat this signal with reduced confidence.",
  "regulatory_note": "This output is signal intelligence based on statistical analysis of public data. It is not financial advice."
}
```

---

## Section 6: Validation Results

### 6.1 Scope and Limitations

This section presents the Phase 1 validation results in system specification format. The full methodology is documented in BACKTEST.md. The results here are presented as engineering metrics: what the system achieves, under what conditions, and where it fails.

Two limitations apply to all Phase 1 results and must be stated explicitly.

**Limitation 1: Proxy data.** Phase 1 validation used Yahoo Finance USDKES=X weekly close data as a proxy for CBK daily rates. The CBK daily rate archive is not yet programmatically accessible (SCRAPER.md). Weekly data cannot validate a 72-hour detection window. The validated detection window for Phase 1 is therefore 5 trading days, not 72 hours. The 72-hour window is a Phase 2 target.

**Limitation 2: Small ground truth set.** Four confirmed intervention events constitute the Phase 1 ground truth. This is sufficient to validate the detection hypothesis but insufficient to produce statistically robust precision and recall estimates. The false positive rates reported below are estimates derived from the signal firing frequency on non-event days, not from a large labelled dataset. Phase 2 validation will expand the ground truth set to 10 to 15 events using the full CBK daily rate archive.

### 6.2 Ground Truth Event Set

| Event ID | Date | Type | Rate movement | Confirmed by |
|----------|------|------|--------------|-------------|
| GT-001 | Sep 18, 2023 | KES support | 144.70 to 147.25 (+1.8%) | CBK bulletin; MPC statement |
| GT-002 | Feb 12, 2024 | KES support | 163.21 to 140.12 (-14.2%) | CBK governor statements; IMF records |
| GT-003 | Mar 11, 2024 | KES support (continued) | 141.00 to 136.16 (-3.4%) | CBK reserve data; MPC statement |
| GT-004 | Apr 8, 2024 | Floor defence | 128.44 to 125.79 (-2.1%) | Price pattern; Menkhoff (2013) |

### 6.3 Per-Signal Validation Results

**Feature 1: KES/USD Z-Score (F1)**

| Metric | Value | Notes |
|--------|-------|-------|
| True positives | 4 / 4 | Fired before all ground truth events |
| Recall | 1.00 | |
| Precision (threshold 2.0) | 0.36 | Estimated; 7 false positives per year |
| Precision (threshold 2.5) | ~0.50 | Estimated; 4 false positives per year |
| Detection window | 5 trading days | Phase 1 proxy data limitation |
| Status | VALIDATED | |

**Feature 2: Cross-Pair Inconsistency Index (F2 / CPII)**

| Metric | Value | Notes |
|--------|-------|-------|
| True positives | 4 / 4 | Fired before all ground truth events |
| Recall | 0.90 | Estimated; may miss events during global USD moves |
| Precision | 0.85 to 0.90 | Estimated; 1 to 2 false positives per year |
| Detection window | 5 trading days | Phase 1 proxy data limitation |
| Status | VALIDATED | Highest-precision signal in the system |
| Phase 2 dependency | Bank of Uganda and Bank of Tanzania daily rates | Currently inferred from weekly proxy |

**Feature 3: Ganji Volatility Compression Index (F3 / GVCI)**

| Metric | Value | Notes |
|--------|-------|-------|
| True positives | 4 / 4 | Fired before all ground truth events |
| Recall | 0.90 | Estimated |
| Precision | 0.70 | Estimated; 3 to 5 false positives per year |
| Detection window | 5 trading days | Phase 1 proxy data limitation |
| Status | VALIDATED | Primary false positive source: holiday low-volatility periods |

**Feature 4: Reserve Stress Signal (F4 / RSS)**

| Metric | Value | Notes |
|--------|-------|-------|
| True positives | Not tested | Phase 2 only |
| Status | HYPOTHESIS | $200M threshold not yet empirically validated |
| Phase 2 action | Validate against CBK reserve data for GT-001 through GT-004 | |

**Feature 5: CBK NLP Tone Classification (F5)**

| Metric | Value | Notes |
|--------|-------|-------|
| True positives | Not tested | Prompt defined; not run against ground truth |
| Status | IMPLEMENTED | Empirical validation pending |
| Phase 2 action | Classify MPC statements preceding GT-001 through GT-004; measure tone accuracy | |

**Feature 6: Binance P2P Premium Signal (F6 / BPPS)**

| Metric | Value | Notes |
|--------|-------|-------|
| True positives | Not tested | Historical P2P data not available for 2023 to 2024 |
| Status | IMPLEMENTED | Real-time data available; historical data limited |
| Phase 2 action | Monitor prospectively; build historical baseline from current data forward | |

### 6.4 Composite Score Validation Results

**Phase 1 composite scoring function (F1 + F2 + F3 only):**

| Confidence tier | Score threshold | Ground truth events detected | Estimated false positives per year |
|----------------|----------------|------------------------------|-------------------------------------|
| HIGH | >= 5 | 4 / 4 (100%) | 1 to 2 |
| MEDIUM | 3 to 4 | 4 / 4 (100%) | 4 to 6 |
| LOW | 1 to 2 | 4 / 4 (100%) | 8 to 12 |

**HIGH confidence breakdown for each ground truth event:**

| Event | F1 points | F2 points | F3 points | Total | Confidence |
|-------|-----------|-----------|-----------|-------|------------|
| GT-001 (Sep 2023) | 2 (Z=2.3) | 3 | 2 | 7 | HIGH |
| GT-002 (Feb 2024) | 2 (Z=3.1) | 3 | 2 | 7 | HIGH |
| GT-003 (Mar 2024) | 2 (Z=2.6) | 3 | 2 | 7 | HIGH |
| GT-004 (Apr 2024) | 1 (Z=2.1) | 3 | 2 | 6 | HIGH |

All four ground truth events produced a composite score of 6 or above, well above the HIGH confidence threshold of 5.

### 6.5 Phase 2 Validation Targets

Phase 2 validation will address the four open items from Phase 1.

| Item | Current status | Phase 2 target | Success criterion |
|------|---------------|----------------|-------------------|
| Detection window | 5 trading days (weekly proxy) | 1 trading day (CBK daily data) | Signal fires within 1 trading day of confirmed intervention |
| Ground truth set size | 4 events | 10 to 15 events | Sufficient for statistically robust precision/recall estimates |
| F4 RSS threshold | Unvalidated ($200M) | Validated against CBK reserve data | Threshold confirmed or revised with empirical basis |
| F5 NLP accuracy | Unvalidated | Validated against MPC statements preceding GT-001 to GT-004 | Tone classification accuracy >= 80% on ground truth set |

### 6.6 Honest Assessment of Current System Maturity

| Dimension | Current state | Target state |
|-----------|--------------|-------------|
| Detection hypothesis | Validated on 4 events | Validated on 10 to 15 events with daily data |
| Data infrastructure | Manual / Yahoo Finance proxy | Automated CBK scraper + Bank of Uganda + Bank of Tanzania |
| NLP layer | Prompt defined; not empirically tested | Validated against historical MPC statements |
| False positive rate | Estimated from signal frequency | Measured from labelled dataset |
| Detection window | 5 trading days | 1 trading day |
| Production readiness | Research prototype | Not yet production-ready |

The system is a validated research prototype. The detection hypothesis is confirmed. The infrastructure to move from prototype to production is defined in SCRAPER.md and the Phase 2 plan in BACKTEST.md Part 5. Production readiness requires Phase 2 completion.

---

## Section 7: Phase Roadmap

### 7.1 Phase 1: Research Prototype (Current)

**Status:** Complete.

**What exists:**

| Component | Status | Location |
|-----------|--------|----------|
| Detection hypothesis | Validated on 4 ground truth events | BACKTEST.md |
| Feature definitions (F1, F2, F3) | Mathematically specified | Section 3 |
| CIPS scoring function | Specified with validated weights | Section 4 |
| Signal output schema | Fully defined | Section 5 |
| NLP prompt template | Defined; not empirically tested | Section 3.6 |
| Binance P2P ingestion | Implemented; live data confirmed | Section 2.2 |
| Seasonal calendar filter | Implemented | Section 3.8 |
| Data store schema | Defined | Section 2.5 |
| Research documentation | Complete across 5 documents | research/03-technical-research/ |

**What does not exist:**

| Component | Reason | Phase |
|-----------|--------|-------|
| detector.py | Not yet built | 2 |
| CBK daily rate scraper | Not yet built (SCRAPER.md) | 2 |
| Bank of Uganda scraper | Not yet built | 2 |
| Bank of Tanzania scraper | Not yet built | 2 |
| CBK reserve PDF parser | Not yet built | 2 |
| REST API | Not yet built | 2 |
| Dashboard | Not yet built | 3 |
| Subscriber management | Not yet built | 3 |

### 7.2 Phase 2: Prototype to Production Pipeline

**Entry condition:** CBK scraper (SCRAPER.md) is built, validated, and producing clean daily data for a minimum of 30 consecutive trading days.

**Deliverables:**

**2.1 detector.py**

The core detection script. Implements the full pipeline from Section 4.7 using daily CBK data. Runs via cron at 18:00 EAT Monday to Friday.

```
detector.py
  ├── ingest.py          # Layer 1: data ingestion
  ├── features.py        # Layer 2: feature engineering (F1 to F7)
  ├── engine.py          # Layer 3: CIPS scoring and direction classification
  ├── output.py          # Layer 4: signal output JSON generation
  └── deliver.py         # Layer 5: signal delivery (file write; email in Phase 2)
```

**2.2 Phase 2 data infrastructure**

| Component | Tool | Purpose |
|-----------|------|---------|
| CBK scraper | Python + BeautifulSoup | Daily CBK rate ingestion |
| Bank of Uganda scraper | Python + BeautifulSoup | Daily UGX/USD ingestion |
| Bank of Tanzania scraper | Python + BeautifulSoup | Daily TZS/USD ingestion |
| CBK reserve parser | pdfplumber | Weekly reserve extraction from PDF bulletin |
| Data store | TimescaleDB (PostgreSQL extension) | Replaces CSV files |
| Cron scheduler | Linux cron | Runs pipeline at 18:00 EAT daily |

**2.3 Phase 2 validation**

Run the full detection pipeline against the CBK daily rate archive from January 2022 to present. Expand the ground truth set from 4 to 10 to 15 events. Validate F4 (RSS threshold), F5 (NLP accuracy), and the 1-trading-day detection window. Document results in BACKTEST.md Part 5.

**2.4 Phase 2 signal delivery**

Email digest to subscribers when HIGH or MEDIUM confidence signal fires. Plain-text email containing the signal_context field and the component breakdown. No dashboard required in Phase 2.

**Exit condition for Phase 2:** detector.py running cleanly on daily data for 60 consecutive trading days with no pipeline failures. Phase 2 validation complete with ground truth set of 10 or more events.

### 7.3 Phase 3: Production System

**Entry condition:** Phase 2 exit condition met. At least 10 paying subscribers.

**Deliverables:**

**3.1 REST API**

Exposes the signal archive and real-time signal state to subscribers via authenticated HTTP endpoints. Documented in TRADING.md Section 7.6.

```
GET  /api/v1/signal/current
GET  /api/v1/signal/history?days=30
GET  /api/v1/signal/{pair}
POST /api/v1/webhook/subscribe
```

**3.2 Dashboard**

React frontend with TradingView Lightweight Charts library. Displays:
- Current signal state (confidence tier, direction, CIPS score)
- Component breakdown (which features fired)
- Historical signal timeline
- KES/USD price chart with signal overlay
- Binance P2P premium chart

**3.3 Webhook delivery**

Real-time HTTP POST to subscriber-defined URLs when HIGH confidence signal fires. Retry logic with exponential backoff documented in TRADING.md Section 7.6.

**3.4 MetaTrader integration**

Expert Advisor (EA) template that consumes Ganji Protocol webhook output and executes trades based on subscriber-defined rules. Template provided to Professional and Institutional tier subscribers.

**3.5 Chatbot**

RAG-based conversational interface grounded in Ganji Protocol signal data. Documented in TRADING.md Section 9.5. Answers questions about current and historical signals without providing financial advice.

**3.6 Phase 3 additional signals**

| Signal | Description | Data source |
|--------|-------------|-------------|
| VIX global filter | Suppress CPII false negatives during global risk-off | FRED API (free) |
| BMatch spread proxy | CBK weighted average vs commercial bank mean | 9 bank website scrapers |
| Triangular arbitrage monitor | KES/UGX/TZS consistency check | CBK + BOU + BOT daily rates |
| NSE banking sector co-movement | All 5 banking stocks decline simultaneously | NSE end-of-day data |
| Google Trends KES signal | Search volume for "dollar rate Kenya" | Google Trends API |

**3.7 OCTIO integration**

Submit FOREX_MANIPULATION indicator to ThreatRegistry.sol when HIGH confidence signal fires. Documented in LANDSCAPE.md Part 13 and ENTITIES.md Entity 3.1.

```solidity
// ThreatRegistry.sol extension
enum IndicatorType {
    PHISHING,
    DNS_HIJACK,
    SMART_CONTRACT_EXPLOIT,
    FOREX_MANIPULATION  // Added by Ganji Protocol
}
```

### 7.4 Component Dependency Map

```
Phase 1 (complete)
  └── Detection hypothesis validated
  └── Feature specifications defined
  └── Signal output schema defined

Phase 2 (next)
  ├── Requires: CBK scraper (SCRAPER.md)
  ├── Requires: Bank of Uganda scraper
  ├── Requires: Bank of Tanzania scraper
  ├── Produces: detector.py
  ├── Produces: Phase 2 validation results
  └── Produces: Email signal delivery

Phase 3 (future)
  ├── Requires: Phase 2 complete
  ├── Requires: 10+ paying subscribers
  ├── Produces: REST API
  ├── Produces: Dashboard
  ├── Produces: Webhook delivery
  ├── Produces: MetaTrader EA template
  ├── Produces: Chatbot
  └── Produces: OCTIO integration
```

### 7.5 Open Research Questions

The following questions are unresolved and constitute the research agenda for Phase 2 and Phase 3.

| Question | Priority | Phase |
|----------|----------|-------|
| Does the $200M reserve drawdown threshold hold across all documented CBK intervention events? | High | 2 |
| What is the NLP classification accuracy of Gemma 4 on historical CBK MPC statements? | High | 2 |
| Does the GVCI suppression-then-spike sequence pattern improve precision over GVCI alone? | High | 2 |
| Can the detection methodology be generalised to Bank of Uganda and Bank of Tanzania interventions? | Medium | 2 |
| Does the Binance P2P premium lead or lag the CBK official rate during intervention events? | Medium | 2 |
| What is the optimal CPII basket weighting (equal weight vs trade-flow weighted)? | Medium | 3 |
| Can a Hidden Markov Model improve regime detection over the current threshold-based approach? | Low | 3 |
| Does Google Trends search volume for KES-related terms provide a leading signal? | Low | 3 |

---

## References

- Almgren, R. and Chriss, N. (2001). Optimal Execution of Portfolio Transactions. *Journal of Risk*, 3(2), 5-39.
- Comerton-Forde, C. and Putnins, T. (2015). Stock Price Manipulation: Prevalence and Determinants. *Review of Finance*, 19(4), 1581-1616.
- Dominguez, K. and Frankel, J. (1993). Does Foreign Exchange Intervention Work? Peterson Institute for International Economics.
- Easley, D., Lopez de Prado, M., and O'Hara, M. (2012). Flow Toxicity and Liquidity in a High-frequency World. *Review of Financial Studies*, 25(5), 1457-1493.
- Engle, R. and Granger, C. (1987). Co-integration and Error Correction. *Econometrica*, 55(2), 251-276.
- Fratzscher, M. et al. (2019). When Is Foreign Exchange Intervention Effective? Evidence from 33 Countries. *American Economic Journal: Macroeconomics*, 11(1), 132-156.
- Glosten, L. and Milgrom, P. (1985). Bid, Ask and Transaction Prices in a Specialist Market with Heterogeneously Informed Traders. *Journal of Financial Economics*, 14(1), 71-100.
- Ito, T. and Yabu, T. (2007). What Prompts Japan to Intervene in the Forex Market? *Journal of International Money and Finance*, 26(2), 193-212.
- Kyle, A. (1985). Continuous Auctions and Insider Trading. *Econometrica*, 53(6), 1315-1335.
- Menkhoff, L. (2013). Foreign Exchange Intervention in Emerging Markets: A Survey of Empirical Studies. *World Economy*, 36(9), 1187-1208.
- Central Bank of Kenya. Daily indicative rates: centralbank.go.ke/cbk-indicative-rates
- Bank of Uganda. Statistics: bou.or.ug/statistics
- Bank of Tanzania. Exchange rates: bot.go.tz/exchange-rates
- Binance P2P. Public API: p2p.binance.com
- Yahoo Finance. USDKES=X historical data: finance.yahoo.com
