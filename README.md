# Ganji Protocol

**Signal intelligence for East African forex markets.**

Ganji Protocol is a detection engine that identifies Central Bank of Kenya (CBK) intervention patterns in the KES/USD market before the price fully moves. It is not a trading system. It does not buy or sell. It is intelligence infrastructure: it tells every algorithm, every trader, and every DeFi protocol operating in East African currency markets when the market is being moved by a large, informed participant.

---

## The Problem

Every algorithmic trading system in East Africa trades blindly into manipulated markets.

The CBK intervenes in the KES/USD market approximately 4 to 8 times per year. Each intervention moves the market by 5 to 15% within weeks. Tier 1 banks executing CBK orders know the intervention is happening. Tier 5 retail traders in Nairobi find out after the price has moved. The gap between Tier 1 and Tier 5 is measured in hours to days.

No Bloomberg terminal, no TradingView indicator, no quantitative hedge fund, and no DeFi protocol has built a detection system for CBK intervention patterns. This is the gap Ganji Protocol fills.

---

## The Detection Engine

Ganji Protocol monitors seven signals derived entirely from free, public data sources:

| Signal | Description | Status |
|--------|-------------|--------|
| F1: Z-Score Deviation | KES/USD statistical anomaly vs 30-day mean | Validated |
| F2: Cross-Pair Inconsistency Index (CPII) | KES moves while UGX/TZS basket stays stable | Validated |
| F3: Ganji Volatility Compression Index (GVCI) | Artificial volatility suppression detection | Validated |
| F4: Reserve Stress Signal (RSS) | CBK reserve drawdown pattern | Phase 2 |
| F5: CBK NLP Tone Classification | Gemma 4 classification of MPC press statements | Implemented |
| F6: Binance P2P Premium Signal (BPPS) | P2P KES/USDT divergence from official rate | Implemented |
| F7: Seasonal Calendar Filter | Known high-volatility event annotation | Implemented |

These signals are combined into the **CBK Intervention Probability Score (CIPS)**, a composite confidence measure with three tiers: HIGH, MEDIUM, and LOW.

---

## Data Sources

All data sources are free. No scraping. All API-based.

- **Yahoo Finance** — 5-year daily history for KES, UGX, TZS, RWF, ETB
- **open.er-api.com** — Daily current rates, no key required
- **Alpha Vantage** — Daily rates, free API key
- **Twelve Data** — Daily rates, free API key
- **Binance P2P** — Real-time KES/USDT, no key required

---

## Signal Output

Every pipeline run produces a structured JSON signal:

```json
{
  "signal_id": "GP-2026-05-25-001",
  "pair": "KES/USD",
  "detection": {
    "cips_score": 3,
    "confidence": "MEDIUM",
    "direction": "KES_SUPPORT",
    "sequence_pattern": true
  },
  "signal_context": "Z-score deviation of 2.81 sigma above 30-day mean. Sequence pattern detected: volatility suppression preceded price spike.",
  "regulatory_note": "This output is signal intelligence based on statistical analysis of public data. It is not financial advice."
}
```

---

## Validation

Phase 1 backtesting (weekly proxy data, 4 ground truth events):
- F1 recall: 1.00 | F2 recall: 0.90 | F3 recall: 0.90
- HIGH confidence: 1 to 2 false positives per year

Phase 2 backtesting (daily data, 1,267 dates, May 2021 to May 2026):
- F1 recall: 0.75 | F2 recall: 0.50 | F3 recall: 0.50
- Individual signals confirmed on daily data
- Composite threshold recalibration in progress

Full methodology: `research/03-technical-research/BACKTEST.md`

---

## Repository Structure

```
ganji-protocol/
  research/
    01-foundation/          # Project vision and philosophy
    02-market-intelligence/ # LANDSCAPE.md, ENTITIES.md
    03-technical-research/  # ALGORITHMS.md, BACKTEST.md, SYSTEM.md, TRADING.md
    04-deep-dives/          # 19 deep academic paper treatments (local only)
  engine/                   # Detection engine (local only)
  data/                     # Rate data and signal archive (local only)
  detector.py               # Single entry point: runs the full pipeline
  index.html                # Signal dashboard (local only)
```

---

## Academic Foundation

Ganji Protocol is the first empirical application of the Menkhoff (2013) intervention fingerprint framework and the Fratzscher et al. (2019) pre-intervention positioning methodology to the Central Bank of Kenya. The research gap: East African forex manipulation detection has essentially zero academic literature.

Key papers:
- Menkhoff (2013) — Foreign Exchange Intervention in Emerging Markets: A Survey (126 citations)
- Fratzscher et al. (2019) — When Is Foreign Exchange Intervention Effective? (146 citations)
- Kyle (1985) — Continuous Auctions and Insider Trading (9,409 citations)
- Gatev et al. (2006) — Pairs Trading: Performance of a Relative-Value Arbitrage Rule (915 citations)

---

## OCTIO Integration

Ganji Protocol extends OCTIO's on-chain threat intelligence registry (`ThreatRegistry.sol`) with a new indicator type: `FOREX_MANIPULATION`. When a HIGH confidence signal fires, Ganji Protocol submits a `FOREX_MANIPULATION` indicator on-chain. DeFi protocols operating in the East African market can query `isFlagged()` before executing KES-denominated transactions.

---

## Status

**Phase 1 (current):** Research prototype. Engine running locally. Daily cron at 18:00 EAT. Signal archive accumulating.

**Phase 2 (next):** CBK daily rate scraper. Expanded ground truth set. NLP validation. Email delivery.

**Phase 3 (future):** REST API. Dashboard. MetaTrader EA. Webhooks. Chatbot. OCTIO integration.

---

## Author

James Kabingu — OCTIO-Labs | Vektasafe

---

*"The crowd is both friend and enemy."*
— Robert Ludlum, The Jason Bourne series
