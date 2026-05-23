# Ganji Protocol: Entity Technical Research

**Author:** James Kabingu, OCTIO-Labs | Vektasafe
**Status:** Living document; incomplete. Pillar 2 and Pillar 3 entities pending.
**Scope:** Deep technical assessment of each market participant whose activity produces signals detectable by Ganji Protocol
**Cross-reference:** See ALGORITHMS.md for the mathematical treatment of algorithm classes referenced here. See LANDSCAPE.md for the institutional terrain overview.

---

## How to Read This Document

Each entity entry follows a fixed structure:

1. **Entity profile:** Ownership, regulatory status, capital base, client profile
2. **Documented strategy:** What algorithm class they run, what instruments, what timeframes
3. **Market microstructure footprint:** How their order flow moves prices in observable data
4. **KES/USD connection:** The precise mechanism linking their activity to forex market conditions
5. **Ganji Protocol signals:** What `detector.py` should watch for, with data sources
6. **Documentation status:** What is confirmed public record vs what is inferred

---

## Pillar 1 Entities: NSE Equity Market Participants

---

### Entity 1.1: FourFront Management — Standard Investment Bank (SIB)

#### 1.1.1 Entity Profile

**Parent company:** Standard Investment Bank (SIB), Kenya's oldest independent investment bank, founded in 1995. SIB is licensed by the Capital Markets Authority (CMA) as a stockbroker, investment adviser, and fund manager.

**FourFront division:** Established as SIB's algorithmic trading and robo-advisory arm. Timeline of regulatory milestones:
- 2008: First SMS/mobile trading provider in Kenya
- 2012: Licensed as first premium retail trading service provider in Kenya
- 2018: Digitised service delivery; fully integrated online trading
- 2022: Licensed as Kenya's first Robo-Advisor by the CMA
- 2023: Launched Kenya's first algorithmic trading system on the NSE
- 2024: Became Kenya's first large short selling lending book provider

**Founder and CEO:** Donald Wangunyu. Publicly described as the pioneer of algorithm-based trading, high-frequency trading, and short selling on the NSE.

**Regulatory licences held:**
- CMA Stockbroker licence
- CMA Investment Adviser licence
- CMA Fund Manager licence
- CMA Robo-Advisor licence (first in Kenya, 2022)
- CMA Algorithm Trading Provider licence (first in Kenya, 2023)
- CMA Short Selling Lending Book Provider licence (first in Kenya, 2024)

**Client profile:**
- Retail investors: individual traders accessing the NSE via FourFront's robo-advisory platform
- Institutional clients: fund managers and corporate investors accessing FourFront's quantitative trading desk
- Stockbrokers: brokers using FourFront's order flow aggregation service to generate institutional block orders from retail flow

**Contact and data outlets:**
- Website: fourfrontmgt.ke
- LinkedIn: linkedin.com/company/fourfrontmgt
- SIB research reports: sib.co.ke/reports (monthly NSE performance summaries)
- Contact: clientservice@sib.co.ke | +254 777 333 000
- Address: 16th Floor, JKUAT Building, Kenyatta Avenue, Nairobi

---

#### 1.1.2 Documented Strategy: Retail Robo-Advisory Layer

**Algorithm class:** Modern Portfolio Theory rebalancing. See ALGORITHMS.md Section 1.2 for full mathematical treatment.

**What FourFront publicly states:**
> "FourFront's robo-advisory solution collects information from clients about their financial situation and future goals through an online survey, then uses that data to offer investment advice and automatically invest client assets."
> "Our AI system adjusts to a client's daily balance, tracks price changes, and identifies trading opportunities tailored to that client on the NSE."

**Instruments:** NSE-listed equities and Kenyan government securities (Treasury bills and bonds).

**Timeframe:** Daily rebalancing check. Trades triggered when portfolio weights drift beyond the tolerance band.

**Specific documented behaviour:**

The retail layer operates on a threshold-based rebalancing model. When a client's equity allocation drifts more than 5% from its target weight (the standard industry threshold documented in Tokat and Wicas, 2007), the system generates a rebalancing trade. On the NSE, where banking stocks (Equity, KCB, NCBA, Cooperative Bank, Absa) constitute a large share of the equity index, a market-wide decline in banking stocks simultaneously pushes thousands of retail client portfolios below their target equity weight. This triggers a wave of mechanical buy orders across the banking sector.

**Order size profile:** Individual retail rebalancing orders are small (KSh 10,000 to KSh 500,000 per client). However, FourFront aggregates retail order flow into institutional blocks for execution. The aggregated block can represent KSh 5 million to KSh 50 million in a single banking stock, which is significant relative to the NSE's daily volume in that stock.

---

#### 1.1.3 Documented Strategy: Institutional Algorithmic Trading Layer

**Algorithm classes:** VWAP execution, pairs trading / statistical arbitrage, momentum / trend following, short selling. See ALGORITHMS.md Sections 1.3, 1.4, 1.5, and 1.6 for full mathematical treatment.

**What FourFront publicly states:**
> "For fund managers and corporate investors: We are licensed to deploy our algorithmic trading as your customized proprietary desk; delivering advanced trading, disciplined risk management, proactive securities lending, and ring-fenced regulatory compliance."
> "We generate order flow from retail investors that can be offered individually or as aggregated institutional blocks to the stock market."

**Instruments:** NSE-listed equities, with concentration in the five most liquid stocks: Equity Group Holdings, Safaricom, KCB, Absa Bank Kenya, Kenya Power.

**Timeframe:** Intraday to multi-day. VWAP execution operates intraday. Pairs trading and momentum strategies operate on daily close prices with holding periods of days to weeks.

**Specific documented behaviour:**

FourFront operates two distinct execution modes simultaneously:

**Mode 1: VWAP order execution for institutional clients**

When a fund manager client needs to build or unwind a large position in an NSE-listed stock, FourFront's algorithm slices the order across the trading day in proportion to the historical volume profile of that stock. On the NSE, where the opening (09:30 to 10:30) and closing (14:00 to 15:00) periods account for approximately 65 to 70% of daily volume, the VWAP algorithm concentrates execution in these windows.

Observable footprint: On days when FourFront is executing a large institutional order, the target stock shows above-average volume in the opening and closing periods relative to the midday session, with price movement in the direction of the order that is gradual rather than sudden. This is distinguishable from news-driven price movement, which tends to be immediate and accompanied by a volume spike across the full session.

**Mode 2: Proprietary directional trading**

FourFront's proprietary desk runs directional strategies on NSE banking stocks. Based on publicly stated capabilities (momentum trading, short selling) and the market structure of the NSE, the most likely strategy is a combination of:

- SMA(50)/SMA(200) crossover on the NSE Banking Sector Index as a macro filter
- Pairs trading between KCB and Equity Bank as the primary alpha source
- Short selling on individual banking stocks when the macro filter is bearish and the pairs spread signals relative weakness

The proprietary desk is not publicly documented in detail. The above is inferred from FourFront's stated capabilities and the documented algorithm classes that are viable on the NSE's market structure.

---

#### 1.1.4 Market Microstructure Footprint

FourFront's activity leaves four observable patterns in NSE public data:

**Pattern 1: Mechanical rebalancing buying**
- Timing: Within 1 to 2 trading days of a significant banking sector decline
- Observable: Volume spike in banking stocks on a down or flat day, without company-specific news
- Interpretation: Retail robo-advisory rebalancing triggered by portfolio weight drift
- Data source: NSE end-of-day data (nse.co.ke/dataservices)

**Pattern 2: VWAP execution signature**
- Timing: Intraday, concentrated in opening and closing periods
- Observable: Above-average volume in opening and closing periods relative to midday; gradual price movement in one direction across the full session
- Interpretation: Institutional VWAP order execution for a fund manager client
- Data source: NSE intraday data (requires licensed feed; not available in free tier)

**Pattern 3: Pairs trade entry**
- Timing: When KCB/Equity Bank spread Z-score exceeds ±2
- Observable: Selling pressure on one banking stock and buying pressure on the other, without company-specific news for either
- Interpretation: Pairs trade entry; the shorted stock is the one the algorithm considers more exposed to prevailing macro risk
- Data source: NSE end-of-day data

**Pattern 4: Sector short selling**
- Timing: 1 to 3 trading days after the NSE Banking Sector Index Death Cross fires, or after a CBK hawkish communication
- Observable: Simultaneous decline in all five banking stocks (Equity, KCB, NCBA, Cooperative Bank, Absa) by more than one standard deviation from their 30-day average daily return, without company-specific news for any of them
- Interpretation: FourFront's institutional algorithm has initiated short positions across the banking sector in response to a macro deterioration signal
- Data source: NSE end-of-day data

---

#### 1.1.5 KES/USD Connection

The connection between FourFront's NSE activity and KES/USD operates through two channels:

**Channel 1: Bank profitability and forex income**

Kenyan Tier 1 banks (Equity, KCB, NCBA, Stanbic, Standard Chartered) generate a significant share of revenue from forex-related activities: foreign exchange trading income, diaspora remittance fees, trade finance, and cross-border transaction fees. When KES depreciates, dollar-denominated funding costs rise and forex income margins compress. This deteriorates bank profitability, which FourFront's fundamental trigger detects and responds to with short selling.

The lead-lag relationship: FourFront's algorithm detects the macro deterioration signal (KES weakness, rising NPLs, hawkish CBK tone) and initiates short positions on banking stocks. This NSE activity is observable in public data 24 to 72 hours before the KES weakness fully manifests in CBK's published daily reference rates, because CBK rates are published once per day and reflect the weighted average of interbank trades, which lag the institutional positioning.

**Channel 2: Order flow aggregation and KES demand**

When FourFront aggregates retail buy orders into institutional blocks for NSE-listed stocks, it creates demand for KES (retail investors converting savings into equity). Conversely, when institutional clients are selling NSE positions (unwinding equity to hold cash or government securities), it creates KES supply. Large-scale institutional selling on the NSE therefore creates mild KES sell pressure in the forex market, as institutional investors convert KES equity proceeds into USD or government securities.

---

#### 1.1.6 Ganji Protocol Signals

| Signal | Trigger | Data Source | Lead Time to KES Move | ALGORITHMS.md Reference |
|--------|---------|-------------|----------------------|------------------------|
| Banking sector Death Cross | NSE Banking Sector Index SMA(50) crosses below SMA(200) | NSE end-of-day | 24 to 72 hours | Section 1.5A |
| Sector co-movement anomaly | All 5 banking stocks decline > 1 std dev simultaneously | NSE end-of-day | 24 to 72 hours | Section 1.6 |
| KCB/Equity pairs spread | Z-score exceeds ±2 | NSE end-of-day | 12 to 48 hours | Section 1.4 |
| VWAP volume anomaly | Volume > 1.5 std dev above 30-day mean | NSE end-of-day | Concurrent | Section 1.3 |
| Mechanical rebalancing | Volume spike on down day, no news catalyst | NSE end-of-day | Lagging (confirms prior move) | Section 1.2 |

---

#### 1.1.7 Documentation Status

| Claim | Status |
|-------|--------|
| FourFront is Kenya's first algorithm trading provider (2023) | Confirmed public record (CMA licence, FourFront website) |
| FourFront is Kenya's first short selling lending book provider (2024) | Confirmed public record (FourFront website, Business Daily) |
| FourFront runs a robo-advisory platform using MPT rebalancing | Confirmed; CMA Robo-Advisor licence; FourFront website description |
| FourFront runs VWAP execution for institutional clients | Inferred from stated capabilities and market structure |
| FourFront runs pairs trading on NSE banking stocks | Inferred from market structure and stated HFT capability |
| FourFront's short selling is triggered by macro signals | Inferred; consistent with documented short selling literature |
| FourFront's specific algorithm parameters | Not public; proprietary |

---

### Entity 1.2: WorldQuant Brain — Kenyan Consultants

#### 1.2.1 Entity Profile

**Parent company:** WorldQuant LLC, a global quantitative investment management firm founded in 2007 by Igor Tulchinsky, formerly of Millennium Management. WorldQuant manages approximately $7 billion in assets and employs over 1,000 people across 25 offices globally.

**WorldQuant Brain platform:** An open platform allowing independent researchers globally to build and submit quantitative alpha signals (predictive models) for global equity markets. WorldQuant pays researchers whose signals are selected for use in its trading strategies.

**Kenyan presence:** Kenya has thousands of registered WorldQuant Brain consultants, making it one of the largest African contributor bases on the platform. These are individuals building quantitative financial models, primarily for global equity markets rather than East African forex.

**Relevance to Ganji Protocol:** WorldQuant Brain represents a talent pool of Kenyans with quantitative modelling skills. Their models target global markets, not KES pairs. However, their existence demonstrates that quantitative modelling capability exists in Kenya and could be redirected toward East African forex signals.

---

#### 1.2.2 Documented Strategy: Alpha Factor Construction

**Algorithm class:** Cross-sectional alpha factor models. These are not trading algorithms in the execution sense; they are predictive signals that feed into WorldQuant's portfolio construction engine.

**What WorldQuant Brain publicly documents:**

WorldQuant Brain provides extensive public documentation of its alpha construction methodology. An alpha is a mathematical expression that predicts future stock returns based on observable data. The general form is:

$$\alpha_t = f(X_{1,t}, X_{2,t}, \ldots, X_{k,t})$$

where $X_{i,t}$ are observable data fields (price, volume, fundamental data, alternative data) and $f$ is a function the researcher designs.

**Documented alpha construction operators (from WorldQuant Brain public documentation):**

WorldQuant Brain provides a library of operators for constructing alphas. The most commonly used include:

- `rank(x)`: Cross-sectional rank of $x$ across all stocks at time $t$, normalised to $[-0.5, 0.5]$
- `ts_mean(x, d)`: Time-series mean of $x$ over the past $d$ days
- `ts_std_dev(x, d)`: Time-series standard deviation of $x$ over $d$ days
- `ts_rank(x, d)`: Time-series rank of today's value of $x$ relative to the past $d$ days
- `delta(x, d)`: $x_t - x_{t-d}$ (change over $d$ days)
- `correlation(x, y, d)`: Rolling $d$-day correlation between $x$ and $y$
- `decay_linear(x, d)`: Linearly weighted moving average of $x$ over $d$ days

**Example documented alpha (from WorldQuant Brain tutorials):**

A simple momentum alpha:

$$\alpha = \text{rank}(-\text{ts\_rank}(\text{close}, 20))$$

This ranks stocks by how much their price has fallen over the past 20 days (negative momentum), predicting that recent losers will continue to underperform. This is the cross-sectional implementation of the Jegadeesh and Titman (1993) momentum effect.

**Instruments:** Global equities across 20+ markets. Kenyan consultants build alphas for US, European, and Asian markets, not for the NSE.

---

#### 1.2.3 Market Microstructure Footprint

WorldQuant Brain consultants do not directly trade on the NSE. Their alphas feed into WorldQuant's global portfolio, which trades on developed market exchanges. Their NSE footprint is therefore zero in terms of direct market impact.

**Indirect relevance to Ganji Protocol:** The alpha construction methodology documented by WorldQuant Brain is directly applicable to building Ganji Protocol's detection signals. The operator library (rank, ts_mean, ts_std_dev, delta, correlation) maps directly to the signal implementations in ALGORITHMS.md Section 1.7. Ganji Protocol's `detector.py` can be thought of as a specialised alpha construction engine for East African forex manipulation signals rather than global equity returns.

---

#### 1.2.4 KES/USD Connection

None directly. WorldQuant Brain consultants do not trade KES pairs.

**Indirect connection:** If a WorldQuant consultant builds an alpha that uses Kenyan macroeconomic data (CBK rates, NSE banking sector performance) as a predictor of global emerging market returns, WorldQuant's trading activity in global markets could theoretically create indirect demand or supply for KES through capital flow effects. This is too indirect to be a reliable Ganji Protocol signal.

---

#### 1.2.5 Ganji Protocol Signals

None from WorldQuant Brain activity directly.

**Strategic relevance:** WorldQuant Brain's operator library and alpha construction methodology should be studied as a framework for building Ganji Protocol's detection signals. The cross-sectional ranking and time-series operators are directly applicable to normalising KES/USD anomaly signals across multiple currency pairs.

---

#### 1.2.6 Documentation Status

| Claim | Status |
|-------|--------|
| WorldQuant Brain is a public platform for alpha construction | Confirmed; fully documented at worldquantbrain.com |
| Kenya has thousands of registered WorldQuant Brain consultants | Confirmed; WorldQuant public statements |
| Kenyan consultants build alphas for global markets, not NSE | Confirmed; WorldQuant Brain targets global equity markets |
| WorldQuant Brain operator library is applicable to Ganji Protocol signal construction | Inferred; methodological parallel |

---

### Entity 1.3: Tiny Fund

#### 1.3.1 Entity Profile

**Founded:** August 2025
**Model:** Copy trading platform. Subscribers copy the trades of a human trader rather than an algorithm.
**Scale:** 17 subscribers and $425 in monthly recurring revenue as of launch (August 2025).
**Relevance:** Not an algorithmic trading firm. Relevant as a distribution model comparison: Ganji Protocol's Tier 1 retail signal feed ($20/month) operates on the same subscription infrastructure at a different layer.

---

#### 1.3.2 Documented Strategy

Copy trading is not an algorithm in the quantitative sense. It is a signal relay: the platform copies the position entries and exits of a designated lead trader into subscriber accounts proportionally. The lead trader makes discretionary decisions; the platform automates the replication.

**Technical infrastructure:** Copy trading platforms use broker API integration (typically MetaTrader 4/5 or a proprietary API) to monitor the lead trader's account in real time and replicate trades into subscriber accounts within milliseconds of the lead trader's execution.

**Documented platforms used in Kenya:** Zignaly (also used by Trade For Impact), eToro CopyTrader, and proprietary broker copy trading systems.

---

#### 1.3.3 Market Microstructure Footprint

Negligible. At 17 subscribers and $425 monthly revenue, Tiny Fund's aggregate position sizes are too small to create observable market impact on the NSE or in the KES/USD interbank market.

---

#### 1.3.4 KES/USD Connection

None directly. Tiny Fund's lead trader trades NSE equities. The KES/USD connection is indirect and too small to be a reliable signal.

---

#### 1.3.5 Ganji Protocol Signals

None. Tiny Fund is documented here for completeness and as a distribution model reference, not as a signal source.

---

#### 1.3.6 Documentation Status

| Claim | Status |
|-------|--------|
| Tiny Fund launched August 2025 with 17 subscribers | Confirmed; SDK.finance case study |
| $425 monthly recurring revenue at launch | Confirmed; SDK.finance case study |
| Copy trading model, not algorithmic | Confirmed |

---

## Pillar 2 Entities: Forex Market Participants (Pending)

*To be completed. Entities: CBK treasury desk, Tier 1 bank treasury desks (Equity, KCB, Stanbic, Standard Chartered, NCBA), CMA-licensed forex brokers (FXPesa, Scope Markets, Pepperstone Kenya, Windsor Brokers, FP Markets, HF Markets, Empire FX Trade), CBK BMatch system.*

*Scope for each entity: documented treasury desk strategy, interbank market positioning behaviour, order flow patterns in BMatch, KES/USD signal implications for detector.py.*

---

## Pillar 3 Entities: Crypto and Mobile Money Participants (Pending)

*To be completed. Entities: Trade For Impact Asset Management, Trade Sense Ltd, Candlesticks Investments Ltd, EIS Global Pte. Ltd., Binance P2P Kenya, Yellow Card, Kotani Pay, Safaricom M-Pesa.*

*Scope for each entity: documented algorithm type, Zignaly/Binance API integration details, KES/USDT pricing mechanics, M-Pesa routing algorithm and KES liquidity effects, OCTIO integration points.*

---

## References

- Bris, A., Goetzmann, W., and Zhu, N. (2007). "Efficiency and the Bear: Short Sales and Markets Around the World." *Journal of Finance*, 62(3), 1029-1079.
- Capital Markets Authority Kenya. Licensed entities register. licensees.cma.or.ke.
- FourFront Management. Company website. fourfrontmgt.ke. Accessed May 2026.
- Gatev, E., Goetzmann, W., and Rouwenhorst, K. (2006). "Pairs Trading: Performance of a Relative-Value Arbitrage Rule." *Review of Financial Studies*, 19(3), 797-827.
- Jegadeesh, N. and Titman, S. (1993). "Returns to Buying Winners and Selling Losers." *Journal of Finance*, 48(1), 65-91.
- Karungu, R., Memba, F., and Muturi, W. (2018). "Influence of Momentum Effect on Stock Performance of Firms Listed in the Nairobi Securities Exchange."
- Nairobi Securities Exchange. Market data and statistics. nse.co.ke/dataservices.
- SDK.finance. (2025). Tiny Fund case study.
- Standard Investment Bank. Research reports. sib.co.ke/reports.
- Tokat, Y. and Wicas, N. (2007). "Portfolio Rebalancing in Theory and Practice." *Journal of Investing*, 16(2), 52-59.
- WorldQuant Brain. Alpha construction documentation. worldquantbrain.com. Accessed May 2026.
