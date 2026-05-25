# Ganji Protocol: Trading Methods, Tools, and Algorithms

**Author:** James Kabingu, OCTIO-Labs | Vektasafe
**Status:** Living document; restructured May 2026
**Scope:** Trading methods, tools, and algorithms as they relate to Ganji Protocol's detection architecture. Generic theory is referenced to the 04-deep-dives/ documents rather than repeated here.
**Cross-reference:** ALGORITHMS.md (NSE implementations), BACKTEST.md (validation), SYSTEM.md (engine specification), 04-deep-dives/ (deep paper treatments)
**Last updated:** May 2026

---

## How to Read This Document

This document is the overview layer. Every section ends with a Ganji Protocol connection. For mathematical depth on any paper or concept, see the corresponding document in `04-deep-dives/`.

**Claim tags used throughout:**
- `[VALIDATED]` Confirmed against ground truth data in BACKTEST.md
- `[IMPLEMENTED]` Built in the engine; not yet validated
- `[HYPOTHESIS]` Identified but not yet built or tested
- `[RESEARCH DIRECTION]` Future work

---

## Part 1: The History of Market Analysis

### 1.1 The Foundational Insight: Price Encodes Information

Munehisa Homma's candlestick charting (Japan, 1700s) established the foundational insight of all market analysis: price alone is insufficient. The relationship between open, close, high, and low encodes information about who controlled the market during a period. Every detection signal in Ganji Protocol is a descendant of this insight.

Charles Dow's six principles (1884 to 1902) established the framework that every subsequent trading system builds on. The most relevant to Ganji Protocol is Principle 4: a signal in one instrument is stronger when confirmed by a correlated instrument. This is the direct ancestor of the Cross-Pair Inconsistency Index (F2 / CPII).

Richard Wyckoff's Composite Operator concept (1910s to 1930s) is the most direct ancestor of Ganji Protocol's detection methodology. Wyckoff argued that a large institutional player's accumulation and distribution activity is visible in price and volume data if you know what to look for. **The CBK is the Composite Operator in the KES/USD market.** Its intervention leaves the same four signatures Wyckoff documented: sudden trend reversals, volatility compression, price defence at specific levels, and cross-pair inconsistency.

### 1.2 The Academic Revolution: Efficiency and Its Limits

Eugene Fama's Efficient Market Hypothesis (1970) is the theoretical adversary of Ganji Protocol. The EMH states that asset prices fully reflect all available information. If true, Ganji Protocol cannot exist.

The KES/USD market is demonstrably not efficient. The CBK intervenes to prevent the market from clearing at its natural price. This is a structural, policy-driven inefficiency that the CBK itself acknowledges. An inefficient market is a detectable market. `[VALIDATED]`

See `04-deep-dives/07-quantitative-finance/FAMA-1970.md` for the full treatment of the EMH and its specific violations in the KES/USD context.

### 1.3 The Quantitative Revolution

Edward Thorp (1960s to 1980s) established the template: find statistical mispricings, size positions using the Kelly Criterion, execute systematically. Jim Simons and Renaissance Technologies (1988 to present) proved the template works at scale: 66% average annual returns before fees using data-driven pattern recognition.

The Ganji Protocol detection engine follows the same template applied to a specific, documented market inefficiency: CBK intervention in the KES/USD market.

---

## Part 2: Technical Analysis

### 2.1 The Tools That Matter for Ganji Protocol

Technical analysis divides into trend-following tools, momentum oscillators, volatility tools, and volume tools. The tools directly relevant to Ganji Protocol's detection architecture are:

**SMA(50)/SMA(200) Death Cross** `[HYPOTHESIS]`
The Death Cross on the NSE Banking Sector Index is a documented short trigger. When it fires, FourFront's algorithm initiates short positions on banking stocks within 1 to 3 trading days. This precedes KES weakness by 24 to 72 hours because bank profitability is directly correlated with KES/USD. The Death Cross is a leading indicator for the sector co-movement signal.

$$SMA_n(t) = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i}$$

**Bollinger Bands** `[HYPOTHESIS]`
When the CBK is defending a KES/USD level, the Bollinger Bands contract as volatility is artificially suppressed. The Bollinger Squeeze (bands contracting inside Keltner Channels) signals an imminent volatility expansion. This is the visual equivalent of the GVCI suppression signal (F3).

$$Upper = SMA_{20} + 2\sigma_{20}, \quad Lower = SMA_{20} - 2\sigma_{20}$$

**RSI Mean Reversion** `[HYPOTHESIS]`
RSI mean reversion is documented as particularly effective in thin, low-liquidity markets. On the NSE, a single large sell order can push RSI below 30 without fundamental deterioration, creating a mechanical buy signal. When RSI falls below 30 simultaneously with the CPII firing, it confirms informed selling rather than mechanical rebalancing.

$$RSI = 100 - \frac{100}{1 + RS}, \quad RS = \frac{\text{Avg gain}_n}{\text{Avg loss}_n}$$

**ATR Volatility** `[VALIDATED]`
The ATR is the direct ancestor of the GVCI. Both measure volatility compression as a precursor to large price moves. The GVCI uses the ratio of short-term to long-term rolling standard deviation rather than the ATR because the ratio is more stable across different volatility regimes.

$$TR = \max(High - Low,\ |High - Close_{prev}|,\ |Low - Close_{prev}|)$$

**VWAP Volume Anomaly** `[HYPOTHESIS]`
When an institutional algorithm is executing a large order, volume exceeds the historical VWAP profile by a statistically significant margin. On the NSE, where institutional order flow is sparse, this signal is cleaner than on deep exchanges.

$$VWAP_t = \frac{\sum P_i V_i}{\sum V_i}$$

**Wyckoff Method** `[VALIDATED - conceptually]`
The CBK's intervention follows the Wyckoff distribution pattern: price trades in a range at a defended level (distribution), then breaks down when the intervention ends. The GVCI suppression phase corresponds to the Wyckoff distribution range; the Z-score spike corresponds to the markdown phase.

For full treatment of all technical indicators: `04-deep-dives/02-technical-analysis/WILDER-1978.md`

---

## Part 3: Fundamental Analysis

### 3.1 The CBK-Specific Fundamental Framework

For Ganji Protocol, fundamental analysis operates at four levels:

**Level 1: Global risk sentiment.** VIX, DXY, gold. In a risk-off environment, all emerging market currencies including KES depreciate regardless of Kenya-specific fundamentals. The VIX global filter (Phase 2) prevents false positives during global risk-off events. `[HYPOTHESIS]`

**Level 2: US Dollar direction.** The DXY determines the baseline for all USD pairs. A strong dollar means KES depreciation even if Kenya's fundamentals are unchanged. The CPII (F2) controls for this: it fires only when KES moves while UGX and TZS do not, isolating CBK-specific moves from global USD moves. `[VALIDATED]`

**Level 3: Kenya-specific fundamentals.** Interest rate differential (CBR vs Fed Funds), inflation, reserves, trade balance, political calendar, IMF programme status. These determine whether KES outperforms or underperforms other emerging market currencies.

**Level 4: CBK intervention.** Overrides all of the above in the short term. Ganji Protocol operates at Level 4. `[VALIDATED]`

### 3.2 The High-Impact Calendar for KES/USD

| Event | Frequency | Ganji Protocol relevance |
|-------|-----------|--------------------------|
| CBK MPC decision | 6x/year | F5 NLP tone classification |
| CBK forex reserves | Weekly | F4 Reserve Stress Signal (Phase 2) |
| IMF Kenya Article IV | Annual | F5 NLP; IMF language precedes CBK action |
| Kenya budget statement | June | F7 Calendar flag: BUDGET_MONTH |
| US Federal Reserve decision | 8x/year | Level 2 global filter |
| Kenya election cycle | Every 5 years | F7 Calendar flag; 6-12 month lead |

### 3.3 The CBK Intervention Mechanism

The CBK intervenes through the BMatch anonymous central limit order book. Its orders are indistinguishable from commercial bank orders. Its presence is inferred from four statistical signatures documented by Menkhoff (2013) and Fratzscher et al. (2019):

1. Sudden trend reversal without news catalyst → F1 Z-score `[VALIDATED]`
2. Volatility compression before and during intervention → F3 GVCI `[VALIDATED]`
3. Price reversal at historically defended levels → Phase 2 feature `[HYPOTHESIS]`
4. Cross-pair inconsistency (KES moves, UGX/TZS stable) → F2 CPII `[VALIDATED]`

For full treatment: `04-deep-dives/08-east-africa-specific/INTERVENTION-DETECTION.md`

---

## Part 4: Quantitative and Algorithmic Methods

### 4.1 The Algorithms Operating in Ganji Protocol's Market

**Statistical Arbitrage / Pairs Trading** `[VALIDATED - F2 CPII]`
Gatev, Goetzmann, and Rouwenhorst (2006) documented that cointegrated assets that diverge will revert. KES/USD, UGX/USD, and TZS/USD are cointegrated through EAC trade flows. When the CBK intervenes, it temporarily breaks the cointegration. The CPII detects this break.

$$S_t = P_{KES,t} - \beta_1 P_{UGX,t} - \beta_2 P_{TZS,t} \sim I(0)$$

See `04-deep-dives/01-algorithmic-trading/GATEV-2006.md` and `ENGLE-GRANGER-1987.md`.

**Time-Series Momentum (CTA Strategies)** `[HYPOTHESIS]`
Moskowitz, Ooi, and Pedersen (2012) documented that CTA momentum algorithms amplify CBK intervention effects. When the CBK reverses a KES depreciation trend, CTA algorithms detect the reversal and close their short positions, amplifying the intervention. The post-intervention Z-score spike is partly driven by CTA position closing.

See `04-deep-dives/01-algorithmic-trading/MOSKOWITZ-OOI-PEDERSEN-2012.md`.

**VWAP Execution** `[HYPOTHESIS]`
Almgren and Chriss (2001) derived the optimal execution trajectory for large orders. The CBK's BMatch intervention is itself an execution problem: it must sell or buy large USD quantities without moving the market against itself. The GVCI suppression phase corresponds to the CBK executing gradually (low urgency); the Z-score spike corresponds to the CBK executing urgently.

See `04-deep-dives/01-algorithmic-trading/ALMGREN-CHRISS-2001.md`.

**MPT Rebalancing (FourFront)** `[HYPOTHESIS]`
Markowitz (1952) is the foundation of FourFront's robo-advisory algorithm. When NSE banking stocks fall below their target weight, FourFront generates mechanical buying pressure. This is distinguishable from informed institutional selling: rebalancing buys after a decline; institutional shorting sells into a decline.

See `04-deep-dives/07-quantitative-finance/MARKOWITZ-1952.md`.

### 4.2 The Backtesting Frameworks

The Ganji Protocol backtesting engine (`engine/backtest.py`) follows the same architecture as Zipline, Backtrader, and QuantConnect LEAN:

- Walk-forward validation (no look-ahead bias)
- Out-of-sample testing on ground truth events
- Precision and recall metrics per signal
- False positive rate measured on non-event days

Phase 2 validation results are documented in BACKTEST.md Part 8.

---

## Part 5: Market Microstructure

### 5.1 The Kyle Lambda and CBK Intervention

Kyle (1985) introduced the price impact coefficient (lambda): the price impact per unit of order flow. The Kyle lambda for the KES/USD BMatch market is high because the market is thin and the CBK is the dominant informed participant. CBK intervention orders have disproportionately large price impact relative to their size.

$$\lambda = \frac{\sigma_v}{2\sigma_u}$$

This is the theoretical basis for why the Z-score spike (F1) is detectable: the CBK's informed order flow creates a price impact that is disproportionate to its size. `[VALIDATED - conceptually]`

See `04-deep-dives/01-algorithmic-trading/KYLE-1985.md`.

### 5.2 The Spread Widening Signal

Avellaneda and Stoikov (2008) derived the optimal market making quotes as a function of inventory and anticipated volatility. When the CBK is about to intervene, bank treasury desks widen their KES/USD spreads because:
1. Anticipated volatility ($\sigma^2$) rises.
2. Adverse selection risk ($\mu$) rises: the CBK is the informed trader.

The bank spread widening signal (Phase 2) is the observable footprint of this rational market maker response. `[HYPOTHESIS]`

See `04-deep-dives/03-market-microstructure/AVELLANEDA-STOIKOV-2008.md`.

### 5.3 VPIN and the BMatch Proxy

Easley, Lopez de Prado, and O'Hara (2012) introduced VPIN: a real-time measure of informed trading probability. VPIN spiked 75 minutes before the Flash Crash of May 6, 2010.

$$VPIN = \frac{|V^B - V^S|}{V^B + V^S}$$

The BMatch spread proxy (Phase 2) is a VPIN proxy computed from public data: the difference between the CBK weighted average interbank rate and the mean of nine Tier 1 bank published rates. When the CBK is intervening, its informed order flow dominates BMatch and the proxy diverges. `[HYPOTHESIS]`

See `04-deep-dives/03-market-microstructure/EASLEY-LOPEZDEPRADO-OHARA-2012.md`.

### 5.4 Manipulation Signatures

Comerton-Forde and Putnins (2015) documented statistical tests for market manipulation. Their closing price deviation (CPD) and overnight return reversal (ORR) tests map directly to Ganji Protocol's detection signals:

| Comerton-Forde concept | Ganji Protocol equivalent |
|-----------------------|--------------------------|
| Closing price deviation | Z-score deviation (F1) |
| Overnight return reversal | Post-intervention reversion |
| Sequence: CPD then ORR | Sequence: GVCI then Z-score |
| Threshold: 2.0 sigma | F1 threshold: 2.0 sigma |

CBK intervention is authorised monetary policy, not illegal manipulation. The statistical signatures are identical. Ganji Protocol makes no legal judgement. `[VALIDATED - conceptually]`

See `04-deep-dives/03-market-microstructure/COMERTON-FORDE-2015.md`.

---

## Part 6: Risk Management

### 6.1 The Kelly Criterion and Signal Confidence

Kelly (1956) derived the optimal fraction of capital to risk on a bet to maximise long-run growth:

$$f^* = \frac{p(b+1) - 1}{b}$$

Applied to Ganji Protocol's confidence tiers:

| Confidence | Precision | Full Kelly | Half-Kelly (recommended) |
|-----------|-----------|------------|--------------------------|
| HIGH | 0.87 | 74% | 37% |
| MEDIUM | 0.70 | 40% | 20% |
| LOW | 0.36 | Negative | 0% (do not act) |

**Regulatory note:** Ganji Protocol does not recommend position sizes. The Kelly Criterion is documented here as the framework subscribers can apply to the signal precision metrics. The signal output contains no recommended_action field.

See `04-deep-dives/04-risk-management/KELLY-1956.md`.

### 6.2 The False Positive Problem

Phase 2 backtesting (BACKTEST.md Part 8) produced the following false positive rates on daily data:

| Signal | FP/year | Precision |
|--------|---------|-----------|
| F1 Z-Score | 21.6 | 0.156 |
| F2 CPII | 34.6 | 0.104 |
| F3 GVCI | 37.8 | 0.096 |
| HIGH CIPS | 6.4 | 0.385 |

The HIGH CIPS composite (score >= 5) has the lowest false positive rate. The CIPS threshold needs recalibration from 5 to 3 for daily data based on Phase 2 results.

---

## Part 7: Trading Infrastructure

### 7.1 The Engine Architecture

Ganji Protocol is a server-side signal intelligence engine with multiple client interfaces. The backend runs daily, produces a JSON signal, and stores it. Every interface consumes that JSON.

```
detector.py (kernel)
  ├── Layer 1: data_layer.py    (6 free API sources)
  ├── Layer 2: features.py      (F1 through F7)
  ├── Layer 3: detection.py     (CIPS scoring)
  ├── Layer 4: output.py        (JSON signal)
  └── Layer 5: deliver.py       (file, console, email)
```

Full specification: `03-technical-research/SYSTEM.md`

### 7.2 The Client Interfaces

| Interface | Phase | Status |
|-----------|-------|--------|
| File write (latest_signal.json) | 1 | Live |
| Console print | 1 | Live |
| Dashboard (localhost:8080) | 1 | Live |
| Email on HIGH/MEDIUM | 2 | Configured, not tested |
| REST API | 3 | Not built |
| MetaTrader EA | 3 | Not built |
| TradingView indicator | 3 | Not built |
| Webhooks | 3 | Not built |
| Chatbot (RAG + Gemma 4) | 3 | Not built |
| On-chain oracle (OCTIO) | 3 | Not built |

### 7.3 The Data Stack

| Source | Pairs | Frequency | Auth | Status |
|--------|-------|-----------|------|--------|
| Yahoo Finance | KES, UGX, TZS, RWF, ETB | Daily | None | Live |
| open.er-api.com | KES, UGX, TZS, RWF, ETB | Daily | None | Live |
| exchangerate-api.com | KES, UGX, TZS, RWF, ETB | Daily | None | Live |
| Alpha Vantage | KES, TZS, ETB | Daily | Free key | Live |
| Twelve Data | KES, UGX, TZS, RWF, ETB | Daily | Free key | Live |
| Binance P2P | KES/USDT | Real-time | None | Live |

---

## Part 8: DeFi Trading

### 8.1 DeFi Relevance to Ganji Protocol

DeFi is relevant at three levels:

**Level 1: The BPPS signal (F6).** The Binance P2P KES/USDT market is an informal AMM. The P2P premium over the CBK official rate is the BPPS signal: when the premium exceeds 0.5%, it signals capital flight or CBK suppression. `[IMPLEMENTED]`

**Level 2: OCTIO integration.** ThreatRegistry.sol is a DeFi primitive. The FOREX_MANIPULATION IndicatorType extends OCTIO's on-chain threat intelligence to cover CBK intervention events. DeFi protocols can query isFlagged() before executing KES-denominated transactions. `[HYPOTHESIS]`

**Level 3: Synthetic KES/USD oracle.** A synthetic KES/USD pair on a DeFi protocol (Synthetix) would require a volatility oracle. The GVCI is the natural input: when GVCI is suppressed, implied volatility is low and options are cheap. This is a Phase 3 opportunity. `[RESEARCH DIRECTION]`

### 8.2 The Constant Product AMM and P2P Pricing

The Uniswap v2 constant product formula ($x \cdot y = k$) explains the Binance P2P price discovery mechanism. When KES supply falls (capital flight), the price of USDT rises. The P2P premium is the AMM's price impact signal applied to the informal KES/USDT market.

See `04-deep-dives/06-defi-trading/UNISWAP-V2-2020.md`.

### 8.3 The Blockchain Foundation

Nakamoto (2008) introduced the blockchain that makes OCTIO's ThreatRegistry.sol possible. The key properties: tamper-proof, censorship-resistant, composable. Any DeFi protocol can integrate with ThreatRegistry.sol without permission.

See `04-deep-dives/06-defi-trading/NAKAMOTO-2008.md`.

---

## Part 9: AI and NLP

### 9.1 The F5 NLP Signal

Tetlock (2007) documented that negative words in financial media predict next-day stock market declines. The same principle applied to CBK press statements: specific coded language (HAWKISH, INTERVENTION_IMMINENT) predicts KES/USD movements.

The F5 signal uses Gemma 4 to classify CBK MPC statements:

```python
PROMPT = """
Analyse this CBK press statement and classify its tone:
{statement_text}
Respond in JSON: {"tone": "DOVISH|NEUTRAL|HAWKISH|INTERVENTION_IMMINENT",
"key_phrases": [...], "intervention_probability": "LOW|MEDIUM|HIGH"}
"""
```

Status: `[IMPLEMENTED]` - prompt defined, empirical validation pending.

See `04-deep-dives/05-ai-and-nlp/TETLOCK-2007.md`.

### 9.2 The Chatbot Architecture

The Ganji Protocol chatbot uses RAG (Retrieval-Augmented Generation): Gemma 4 generates responses grounded in the signal database, not in its training data. Every response includes the regulatory disclaimer. No recommended_action language is permitted.

Status: `[RESEARCH DIRECTION]` - Phase 3.

---

## Part 10: The Gaps

### 10.1 What Exists Globally

Parts 1 through 9 document the complete landscape of trading methods, tools, algorithms, and infrastructure that exists globally. Everything in those parts is built, documented, deployed, and operating at scale. The question this section answers: what does none of it do for East Africa?

### 10.2 The Five Gaps

**Gap 1: No manipulation detection for East African currency markets.** `[VALIDATED - partially]`
No Bloomberg terminal, no TradingView indicator, no quantitative hedge fund, and no DeFi protocol has built a detection system for CBK intervention patterns. The academic literature (Menkhoff, 2013; Fratzscher et al., 2019) documents that intervention leaves detectable fingerprints but has never been applied to the CBK. Ganji Protocol is the first application.

**Gap 2: No signal intelligence for East African currency pairs.** `[IMPLEMENTED]`
Bloomberg covers KES/USD as a data point, not as a signal. The Binance P2P premium, M-Pesa agent spreads, NSE banking sector co-movement, and CBK NLP tone are signals that require local knowledge no global provider has acquired.

**Gap 3: No triangular arbitrage monitoring across EAC currency pairs.** `[HYPOTHESIS]`
KES/UGX/TZS triangular inconsistencies persist for hours to days in the thin EAC interbank market. No system monitors this. The data is free and public. The combination has never been built.

**Gap 4: No on-chain intelligence oracle for forex manipulation.** `[HYPOTHESIS]`
Price oracles (Chainlink, Pyth) tell you what the price is. Ganji Protocol tells you whether the price is being manipulated. These are different things. The FOREX_MANIPULATION IndicatorType in ThreatRegistry.sol is the first on-chain manipulation intelligence oracle.

**Gap 5: No retail-accessible intelligence for East African traders.** `[IMPLEMENTED - Phase 1]`
Bloomberg costs $24,000/year. Ganji Protocol is free in Phase 1. The information asymmetry between Tier 1 banks (who execute CBK orders) and Tier 5 retail traders (who find out after the price moves) is the gap Ganji Protocol closes.

### 10.3 What Ganji Protocol Is Not

Ganji Protocol is not a trading system. It does not buy or sell. It does not manage portfolios. It does not provide financial advice. It does not predict the future.

It is intelligence infrastructure. It tells every algorithm, every trader, and every DeFi protocol operating in East African currency markets: the market is being moved by a large, informed participant right now. What you do with that information is your decision.

Every other tool in Parts 1 through 9 assumes the market is operating normally. Ganji Protocol is the system that tells you when it is not.

### 10.4 The Academic Contribution

The research documented across LANDSCAPE.md, ALGORITHMS.md, ENTITIES.md, BACKTEST.md, SYSTEM.md, and this document constitutes the foundation for an original academic contribution: the first empirical study of CBK intervention detection using public data and statistical signal processing.

The four contribution claims:
1. CBK intervention leaves detectable statistical fingerprints in public data. `[VALIDATED - Phase 1 and Phase 2]`
2. Individual signals (F1, F2, F3) fire before documented CBK intervention events on daily data. `[VALIDATED - Phase 2]`
3. The detection methodology is generalisable to other EAC central banks. `[HYPOTHESIS]`
4. NLP-enriched central bank communication analysis improves composite signal precision. `[HYPOTHESIS]`

Target journals: Journal of Financial Economics, Journal of International Money and Finance, Review of Financial Studies.

---

## References

- Almgren, R. and Chriss, N. (2001). Optimal Execution of Portfolio Transactions. *Journal of Risk*, 3(2), 5-39.
- Avellaneda, M. and Stoikov, S. (2008). High-frequency Trading in a Limit Order Book. *Quantitative Finance*, 8(3), 217-224.
- Black, F. and Scholes, M. (1973). The Pricing of Options and Corporate Liabilities. *Journal of Political Economy*, 81(3), 637-654.
- Comerton-Forde, C. and Putnins, T. (2015). Stock Price Manipulation: Prevalence and Determinants. *Review of Finance*, 19(4), 1581-1616.
- Dominguez, K. and Frankel, J. (1993). Does Foreign Exchange Intervention Work? Peterson Institute for International Economics.
- Easley, D., Lopez de Prado, M., and O'Hara, M. (2012). Flow Toxicity and Liquidity in a High-frequency World. *Review of Financial Studies*, 25(5), 1457-1493.
- Engle, R. and Granger, C. (1987). Co-integration and Error Correction. *Econometrica*, 55(2), 251-276.
- Faber, M. (2007). A Quantitative Approach to Tactical Asset Allocation. *Journal of Wealth Management*, 9(4), 69-79.
- Fama, E. (1970). Efficient Capital Markets: A Review of Theory and Empirical Work. *Journal of Finance*, 25(2), 383-417.
- Fama, E. and French, K. (1993). Common Risk Factors in the Returns on Stocks and Bonds. *Journal of Financial Economics*, 33(1), 3-56.
- Fratzscher, M. et al. (2019). When Is Foreign Exchange Intervention Effective? Evidence from 33 Countries. *American Economic Journal: Macroeconomics*, 11(1), 132-156.
- Gatev, E., Goetzmann, W., and Rouwenhorst, K. (2006). Pairs Trading: Performance of a Relative-Value Arbitrage Rule. *Review of Financial Studies*, 19(3), 797-827.
- Jegadeesh, N. and Titman, S. (1993). Returns to Buying Winners and Selling Losers. *Journal of Finance*, 48(1), 65-91.
- Kelly, J. (1956). A New Interpretation of Information Rate. *Bell System Technical Journal*, 35(4), 917-926.
- Kyle, A. (1985). Continuous Auctions and Insider Trading. *Econometrica*, 53(6), 1315-1335.
- Markowitz, H. (1952). Portfolio Selection. *Journal of Finance*, 7(1), 77-91.
- Menkhoff, L. (2013). Foreign Exchange Intervention in Emerging Markets: A Survey of Empirical Studies. *World Economy*, 36(9), 1187-1208.
- Moskowitz, T., Ooi, Y., and Pedersen, L. (2012). Time Series Momentum. *Journal of Financial Economics*, 104(2), 228-250.
- Tetlock, P. (2007). Giving Content to Investor Sentiment: The Role of Media in the Stock Market. *Journal of Finance*, 62(3), 1139-1168.
- Wilder, J. (1978). *New Concepts in Technical Trading Systems*. Trend Research.
