# Ganji Protocol: Algorithm Technical Research

**Author:** James Kabingu, OCTIO-Labs | Vektasafe
**Status:** Living document; incomplete. Pillars 2 and 3 pending.
**Scope:** Technical decomposition of algorithm classes operating in markets Ganji Protocol monitors
**Cross-reference:** See ENTITIES.md for entity-by-entity application of these algorithms

---

## Pillar 1: Equity Algorithms on the Nairobi Securities Exchange

### 1.1 The NSE Market Structure and Its Effect on Algorithms

Understanding the NSE's structural characteristics is prerequisite to understanding how algorithms behave on it. These characteristics directly constrain what strategies are viable and what signals they produce.

**Liquidity profile:**
The NSE equity market turnover in 2024 was KSh 105.97 billion, growing 32% to 4.93 billion shares. By 2025, equity turnover grew a further 37% to KSh 145.4 billion. On a typical session in May 2026, the NSE traded approximately 18 million shares in roughly 8,700 deals, valued at KSh 758 million. The NYSE trades over one billion shares daily. This difference is not merely quantitative; it is structural. It changes how every algorithm class behaves.

**Liquidity concentration:**
Volume is concentrated in five stocks: Equity Group Holdings, Safaricom, KCB, Absa Bank Kenya, and Kenya Power. These five routinely account for the majority of daily volume. Any algorithm trading outside this tier faces serious execution risk; the order book is too thin to absorb large trades without moving the price against itself.

**Structural consequence for algorithms:**
On the NSE, a single institutional order can move a stock significantly. A 500,000-share order in Equity Bank represents 5 to 10% of daily volume. This means:

1. Algorithms cannot execute at the speed and scale they operate at on developed exchanges.
2. When an institutional algorithm initiates a position, it is far more visible in price and volume data than a similar-sized position on the LSE would be.
3. Price trends persist longer in thin markets because large orders are absorbed gradually over days, not minutes. This makes trend-following strategies more profitable on the NSE than on deep exchanges.
4. Statistical arbitrage spreads between correlated stocks persist longer before reverting, making pairs trading viable on a longer timescale than in developed markets.

**Trading hours:**
The NSE operates Monday to Friday, 09:30 to 15:00 East Africa Time; 5.5 hours per day. Algorithms cannot run overnight. Gaps between close and open carry full overnight risk with no electronic hedging mechanism.

**HFT viability:**
True high-frequency trading (co-location, microsecond execution, market-making at scale) is not viable on the NSE. The daily volume is too low to make sub-millisecond arbitrage profitable. What is described as HFT on the NSE is more accurately fast algorithmic trading: execution in seconds rather than milliseconds, exploiting price inefficiencies that persist for minutes or hours. The distinction matters for Ganji Protocol because it determines the timescale on which signals are detectable.

---

### 1.2 Algorithm Class A: Modern Portfolio Theory Rebalancing (Robo-Advisory Layer)

**Documentation status:** Fully documented in academic literature. Standard algorithm behind every licensed robo-advisor globally.

**Academic foundation:**
- Markowitz, H. (1952). "Portfolio Selection." *Journal of Finance*, 7(1), 77-91. Foundational paper establishing Mean-Variance Optimisation.
- Tokat, Y. and Wicas, N. (2007). "Portfolio Rebalancing in Theory and Practice." *Journal of Investing*, 16(2), 52-59. Documents threshold-based rebalancing methodology.

**How the algorithm works:**

**Step 1: Risk profiling and target allocation mapping**

The client completes a questionnaire. Responses are scored and mapped to a risk score from 1 to 10. The score determines a target asset allocation vector $\mathbf{w}^* = (w_1^*, w_2^*, \ldots, w_n^*)$ where $\sum_i w_i^* = 1$.

Example mapping on the NSE:
- Risk score 1 to 3: 70% money market / bonds, 30% equities
- Risk score 4 to 6: 50% money market / bonds, 50% equities
- Risk score 7 to 10: 20% money market / bonds, 80% equities

**Step 2: Portfolio construction via Mean-Variance Optimisation (MVO)**

Given the target equity allocation, the algorithm selects specific NSE-listed securities by solving:

$$\min_{\mathbf{w}} \sigma_p^2 = \mathbf{w}^T \Sigma \mathbf{w}$$

subject to:

$$\sum_i w_i = 1, \quad \mathbf{w}^T \mathbf{\mu} = r_{target}, \quad w_i \geq 0 \; \forall i$$

where $\Sigma$ is the covariance matrix of returns, $\mathbf{\mu}$ is the vector of expected returns, and $r_{target}$ is the target portfolio return implied by the risk score.

On the NSE, the investable universe is approximately 20 liquid stocks. The covariance matrix is therefore 20x20, making the optimisation computationally trivial. The solution produces the efficient frontier; the algorithm selects the portfolio on the frontier corresponding to $r_{target}$.

**Step 3: Threshold-based rebalancing (band rebalancing)**

The algorithm monitors each position's actual weight $w_i(t)$ daily. When any position drifts beyond a tolerance band:

$$|w_i(t) - w_i^*| > \delta$$

where $\delta$ is the rebalancing threshold (typically 5%), a rebalance trade is triggered. The algorithm sells the overweight position and buys the underweight position to restore $\mathbf{w}^*$.

The rebalancing trade size for position $i$ is:

$$\Delta_i = (w_i^* - w_i(t)) \times V_{portfolio}$$

where $V_{portfolio}$ is the total portfolio value.

**Step 4: Dividend reinvestment**

Cash received from dividends is automatically reinvested into the most underweight position relative to $\mathbf{w}^*$.

**Ganji Protocol signal implication:**

When a large number of robo-advisory clients are simultaneously rebalancing after a market decline (banking stocks fall below their target weight), the algorithm generates mechanical buying pressure on NSE banking stocks. This is distinguishable from institutional short selling because the direction is opposite: rebalancing buys after a decline, while institutional shorting sells into a decline. The signal is a volume spike in banking stocks on a down day without a fundamental catalyst, representing mechanical rebalancing rather than informed buying.

---

### 1.3 Algorithm Class B: VWAP Execution Algorithm

**Documentation status:** Fully documented. Industry standard for institutional order execution since the 1980s.

**Academic foundation:**
- Berkowitz, S., Logue, D., and Noser, E. (1988). "The Total Cost of Transactions on the NYSE." *Journal of Finance*, 43(1), 97-112. Established VWAP as the benchmark for execution quality.
- Almgren, R. and Chriss, N. (2001). "Optimal Execution of Portfolio Transactions." *Journal of Risk*, 3(2), 5-39. Mathematical framework for optimal order slicing.

**How the algorithm works:**

Given a target order of $Q$ shares to execute over a trading day of $T$ periods, the VWAP algorithm slices the order into child orders $q_t$ for each period $t$:

$$q_t = Q \times \frac{V_t^{hist}}{\sum_{\tau=1}^{T} V_\tau^{hist}}$$

where $V_t^{hist}$ is the historical average volume in period $t$.

The algorithm executes $q_t$ shares in each period $t$, distributing the order in proportion to the historical volume profile of the stock.

**Market impact model:**

The expected market impact of executing $q_t$ shares in period $t$ is:

$$MI_t = \sigma_t \sqrt{\frac{q_t}{V_t^{hist}}} \times \eta$$

where $\sigma_t$ is the intraday volatility in period $t$ and $\eta$ is a market impact coefficient estimated from historical data. On the NSE, $\eta$ is higher than on developed exchanges due to lower liquidity, meaning the same order size creates proportionally more price impact.

**Almgren-Chriss optimal execution:**

The more sophisticated version minimises the expected cost plus a risk penalty:

$$\min_{\{q_t\}} \left[ \sum_{t=1}^{T} q_t \cdot MI_t + \lambda \cdot \text{Var}\left(\sum_{t=1}^{T} q_t \cdot P_t\right) \right]$$

where $\lambda$ is a risk aversion parameter. Higher $\lambda$ means the algorithm executes faster (less timing risk) at the cost of higher market impact.

**NSE-specific application:**

On the NSE, the volume profile is concentrated in the opening (09:30 to 10:30) and closing (14:00 to 15:00) periods. A VWAP algorithm on the NSE would therefore send approximately 35 to 40% of the order in the first hour and 30 to 35% in the final hour, with the remainder distributed across the midday session.

**Ganji Protocol signal implication:**

VWAP execution creates a predictable intraday volume pattern. When an institutional algorithm is executing a large order, volume in the target stock exceeds the historical VWAP profile by a statistically significant margin. This is detectable as a volume anomaly: actual volume / expected VWAP volume > 1.5 standard deviations above the 30-day average ratio. On the NSE, where institutional order flow is sparse, this signal is cleaner than on deep exchanges.

---

### 1.4 Algorithm Class C: Pairs Trading / Statistical Arbitrage

**Documentation status:** Fully documented methodology. NSE application inferred from market structure.

**Academic foundation:**
- Gatev, E., Goetzmann, W., and Rouwenhorst, K. (2006). "Pairs Trading: Performance of a Relative-Value Arbitrage Rule." *Review of Financial Studies*, 19(3), 797-827. The foundational empirical paper on pairs trading.
- Engle, R. and Granger, C. (1987). "Co-integration and Error Correction: Representation, Estimation, and Testing." *Econometrica*, 55(2), 251-276. The statistical foundation for identifying cointegrated pairs.
- Karungu, R., Memba, F., and Muturi, W. (2018). "Influence of Momentum Effect on Stock Performance of Firms Listed in the Nairobi Securities Exchange." Documents that momentum and mean-reversion effects exist on the NSE.

**How the algorithm works:**

**Step 1: Pair identification via cointegration testing**

Two stocks $A$ and $B$ are cointegrated if a linear combination of their prices is stationary:

$$P_{A,t} - \beta P_{B,t} = \mu + \epsilon_t$$

where $\epsilon_t \sim I(0)$ (stationary). The Engle-Granger two-step procedure tests this:

1. Regress $P_{A,t}$ on $P_{B,t}$ using OLS to estimate $\hat{\beta}$
2. Test the residuals $\hat{\epsilon}_t = P_{A,t} - \hat{\beta} P_{B,t}$ for stationarity using the Augmented Dickey-Fuller (ADF) test

If the ADF test rejects the null of a unit root (p-value < 0.05), the pair is cointegrated and suitable for pairs trading.

**NSE banking sector cointegrated pairs (most likely):**
- KCB / Equity Bank: both large-cap, similar business models, same macro exposure
- NCBA / Cooperative Bank: both mid-tier, similar retail focus
- Absa Kenya / Standard Chartered: both foreign-owned, similar institutional client base

**Step 2: Spread computation and normalisation**

The spread is:

$$S_t = P_{A,t} - \hat{\beta} P_{B,t}$$

Normalised as a Z-score over a rolling window of $n$ days:

$$Z_t = \frac{S_t - \mu_S^{(n)}}{\sigma_S^{(n)}}$$

where $\mu_S^{(n)}$ and $\sigma_S^{(n)}$ are the rolling mean and standard deviation of the spread.

**Step 3: Entry and exit rules**

| Condition | Action |
|-----------|--------|
| $Z_t < -2$ | Enter: Long $A$, Short $B$ (spread abnormally wide; $A$ cheap relative to $B$) |
| $Z_t > +2$ | Enter: Short $A$, Long $B$ (spread abnormally wide; $A$ expensive relative to $B$) |
| $Z_t$ crosses 0 | Exit position (spread has reverted to mean) |
| $\|Z_t\| > 3$ | Stop-loss exit (spread diverging further; cointegration may have broken) |

**Step 4: Position sizing**

The dollar-neutral position sizes are:

$$\text{Long position in } A: \quad \frac{C}{P_{A,t}}$$
$$\text{Short position in } B: \quad \frac{C \cdot \hat{\beta}}{P_{B,t}}$$

where $C$ is the capital allocated to the trade. This ensures the position is market-neutral: gains from one leg offset losses from the other if the overall market moves.

**Ganji Protocol signal implication:**

When the KCB/Equity Bank spread Z-score exceeds +2 (KCB expensive relative to Equity), the pairs algorithm shorts KCB and longs Equity. This creates detectable selling pressure on KCB specifically, without a KCB-specific news catalyst. The direction of the trade (which stock is being shorted) indicates which bank the algorithm considers more exposed to the prevailing macro risk. Since KCB has higher government securities exposure and Equity has higher regional forex income, the direction of the pairs trade encodes information about whether the algorithm is pricing in interest rate risk (KCB short) or forex risk (Equity short).

---

### 1.5 Algorithm Class D: Momentum and Trend Following

**Documentation status:** Fully documented. Empirically validated on emerging markets including Africa.

**Academic foundation:**
- Jegadeesh, N. and Titman, S. (1993). "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency." *Journal of Finance*, 48(1), 65-91. The foundational momentum paper.
- Faber, M. (2007). "A Quantitative Approach to Tactical Asset Allocation." *Journal of Wealth Management*, 9(4), 69-79. Documents the 10-month (200-day) moving average as a timing rule.
- 2023 multi-market study: "The predictive ability of technical trading rules: an empirical analysis of developed and emerging equity markets." Covers 18 emerging markets; documents that moving average rules generate statistically significant excess returns in low-liquidity emerging markets.
- Karungu et al. (2018): Documents momentum effects on the NSE specifically.

**Documented moving average rules applicable to the NSE:**

**A. SMA(50) / SMA(200) Crossover (Golden Cross / Death Cross)**

The most widely documented and replicated technical rule in the literature.

$$\text{Buy signal}: \quad SMA_{50}(t) > SMA_{200}(t) \quad \text{and} \quad SMA_{50}(t-1) \leq SMA_{200}(t-1)$$
$$\text{Sell/Short signal}: \quad SMA_{50}(t) < SMA_{200}(t) \quad \text{and} \quad SMA_{50}(t-1) \geq SMA_{200}(t-1)$$

where $SMA_n(t) = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i}$.

The Death Cross (50-day crossing below 200-day) is the documented short trigger. On the NSE Banking Sector Index, this signal fires approximately 2 to 4 times per year based on historical volatility.

**B. MACD (Moving Average Convergence Divergence)**

Documented by Appel (1979). Uses exponential moving averages:

$$MACD_t = EMA_{12}(t) - EMA_{26}(t)$$
$$Signal_t = EMA_9(MACD_t)$$
$$Histogram_t = MACD_t - Signal_t$$

where $EMA_n(t) = P_t \cdot \frac{2}{n+1} + EMA_n(t-1) \cdot \left(1 - \frac{2}{n+1}\right)$.

Entry rules:
- Buy when $MACD_t$ crosses above $Signal_t$ (histogram turns positive)
- Sell/Short when $MACD_t$ crosses below $Signal_t$ (histogram turns negative)

**C. RSI Mean Reversion**

Documented by Wilder (1978). The Relative Strength Index:

$$RSI_t = 100 - \frac{100}{1 + RS_t}$$

where $RS_t = \frac{\text{Average gain over } n \text{ periods}}{\text{Average loss over } n \text{ periods}}$, typically $n = 14$.

Entry rules:
- Buy when $RSI_t < 30$ (oversold)
- Sell/Short when $RSI_t > 70$ (overbought)

RSI mean reversion is documented as particularly profitable in thin markets where price overshoots are common due to low liquidity. On the NSE, a single large sell order can push RSI below 30 on a stock that has not fundamentally deteriorated, creating a mechanical buy signal for RSI-based algorithms.

**Ganji Protocol signal implication:**

The Death Cross on the NSE Banking Sector Index is a documented short trigger that FourFront's institutional algorithm almost certainly monitors. When it fires, expect short selling pressure on banking stocks within 1 to 3 trading days. This precedes KES weakness by 24 to 72 hours because bank profitability is directly correlated with KES/USD (forex income is a major revenue line for Kenyan banks). The Death Cross therefore functions as a leading indicator for Ganji Protocol's KES/USD intervention detection.

---

### 1.6 Algorithm Class E: Short Selling Mechanics

**Documentation status:** Fully documented. Specific NSE application documented by FourFront's 2024 licensing.

**Academic foundation:**
- Bris, A., Goetzmann, W., and Zhu, N. (2007). "Efficiency and the Bear: Short Sales and Markets Around the World." *Journal of Finance*, 62(3), 1029-1079. Documents short selling mechanics and profitability across 46 markets including emerging markets.
- Faber (2007): Documents the 200-day moving average as the primary short trigger.

**Technical components required for short selling on the NSE:**

1. **Securities lending facility:** The short seller borrows shares from a lending book (FourFront's lending book, launched 2024). The borrower pays a stock borrow fee, typically 0.5 to 2% per annum of the position value.

2. **Margin account:** Collateral (typically 102 to 110% of the position value) is posted against the borrowed shares. If the position moves against the short seller, a margin call is triggered.

3. **Clearing mechanism:** The Central Depository and Settlement Corporation (CDSC) handles settlement. Short positions must be covered within the standard T+3 settlement cycle or rolled.

**Short selling algorithm — documented trigger conditions:**

The literature documents three trigger types for initiating short positions on banking stocks:

**Trigger 1: Technical breakdown (most common)**

$$\text{Short signal}: \quad P_t < SMA_{200}(t) \quad \text{and} \quad V_t > 1.5 \times \bar{V}_{30}$$

Price closes below the 200-day moving average on above-average volume. The volume confirmation filters out false breakdowns caused by a single low-volume day.

**Trigger 2: Fundamental deterioration**

The CBK publishes quarterly banking sector reports with NPL (Non-Performing Loan) ratios. When sector NPLs rise above a threshold (historically, NPL ratio > 12% has preceded banking sector underperformance on the NSE):

$$\text{Short signal}: \quad NPL_t > NPL_{threshold} \quad \text{and} \quad \Delta NPL_t > 0$$

**Trigger 3: Macro signal (most directly relevant to Ganji Protocol)**

$$\text{Short signal}: \quad \Delta KES/USD_t > \sigma_{KES} \times k \quad \text{or} \quad CBK\_tone = \text{HAWKISH}$$

When KES depreciates beyond $k$ standard deviations from its 30-day mean, or when Ganji Protocol's NLP layer classifies CBK communication as HAWKISH, the macro deterioration signal fires. Bank profitability is negatively correlated with KES depreciation (higher dollar-denominated funding costs, lower forex income margins for banks with net long USD positions).

**Short selling execution sequence:**

1. Algorithm identifies trigger condition
2. Checks available shares in lending book and borrow cost
3. Places sell order for borrowed shares (market or limit)
4. Sets stop-loss at $P_{entry} \times (1 + \delta_{stop})$ where $\delta_{stop}$ is typically 5 to 8%
5. Monitors position; closes by buying back shares when target price or stop-loss is reached
6. Returns borrowed shares to lending book; pays accrued borrow fee

**Ganji Protocol signal implication:**

When FourFront's algorithm initiates short positions on multiple banking stocks simultaneously (Trigger 3 firing across the sector), it creates a detectable pattern: selling pressure on Equity, KCB, and NCBA within a short time window, without company-specific news catalysts. This co-movement is the signal. It indicates the algorithm has detected a macro deterioration signal affecting the entire banking sector. Since this trigger is the same macro signal Ganji Protocol monitors (KES weakness, hawkish CBK tone), the NSE short selling pattern is a corroborating signal that appears in equity data before it appears in CBK published forex rates.

---

### 1.7 Detector Implementation: Signals from Pillar 1

The following signals have documented academic foundations and can be implemented directly in `detector.py`. All use NSE end-of-day data, which is freely available.

**Signal 1: NSE Banking Sector Death Cross**

```python
def banking_death_cross(banking_index_prices: pd.Series) -> pd.Series:
    """
    Returns True on the day the NSE Banking Sector Index 50-day SMA
    crosses below the 200-day SMA (Death Cross).
    Academic basis: Faber (2007); 2023 multi-market study.
    """
    sma50 = banking_index_prices.rolling(50).mean()
    sma200 = banking_index_prices.rolling(200).mean()
    cross = (sma50.shift(1) >= sma200.shift(1)) & (sma50 < sma200)
    return cross
```

**Signal 2: Pairs Spread Z-score (KCB / Equity Bank)**

```python
def pairs_spread_zscore(
    kcb: pd.Series,
    equity: pd.Series,
    window: int = 30
) -> pd.Series:
    """
    Returns the Z-score of the KCB/Equity Bank price spread.
    Z > +2: KCB expensive relative to Equity (short KCB signal).
    Z < -2: Equity expensive relative to KCB (short Equity signal).
    Academic basis: Gatev et al. (2006); Engle and Granger (1987).
    Note: production version should use cointegration beta from OLS regression.
    """
    spread = kcb - equity  # simplified; replace with beta-adjusted spread
    zscore = (spread - spread.rolling(window).mean()) / spread.rolling(window).std()
    return zscore
```

**Signal 3: Sector Co-movement Anomaly**

```python
def sector_comovement_anomaly(
    bank_returns: pd.DataFrame,
    window: int = 30,
    threshold: float = -1.0
) -> pd.Series:
    """
    Returns True when all five banking stocks decline simultaneously
    by more than `threshold` standard deviations from their rolling mean.
    Indicates institutional short selling across the sector.
    bank_returns columns: ['equity', 'kcb', 'ncba', 'cooperative', 'absa']
    Academic basis: Bris et al. (2007); Karungu et al. (2018).
    """
    mean = bank_returns.rolling(window).mean()
    std = bank_returns.rolling(window).std()
    zscores = (bank_returns - mean) / std
    all_below_threshold = (zscores < threshold).all(axis=1)
    return all_below_threshold
```

**Signal 4: VWAP Volume Anomaly**

```python
def vwap_volume_anomaly(
    volume: pd.Series,
    window: int = 30,
    multiplier: float = 1.5
) -> pd.Series:
    """
    Returns True when actual volume exceeds the expected VWAP volume
    by more than `multiplier` standard deviations.
    Indicates institutional VWAP execution in progress.
    Academic basis: Berkowitz et al. (1988); Almgren and Chriss (2001).
    """
    rolling_mean = volume.rolling(window).mean()
    rolling_std = volume.rolling(window).std()
    zscore = (volume - rolling_mean) / rolling_std
    return zscore > multiplier
```

---

### 1.8 What Is Documented vs What Is Inferred

| Algorithm | Documentation Status | Primary Source |
|-----------|---------------------|----------------|
| MPT rebalancing (robo-advisory) | Fully documented | Markowitz (1952); Tokat and Wicas (2007) |
| VWAP execution | Fully documented | Berkowitz et al. (1988); Almgren and Chriss (2001) |
| Pairs trading methodology | Fully documented | Gatev et al. (2006); Engle and Granger (1987) |
| Pairs trading on NSE banking stocks | Inferred from market structure | Karungu et al. (2018) |
| SMA(50)/SMA(200) crossover | Documented as profitable in emerging markets | Faber (2007); 2023 multi-market study |
| MACD (EMA 12/26) | Fully documented | Appel (1979) |
| RSI(14) mean reversion | Fully documented | Wilder (1978) |
| Short selling trigger (200-day MA) | Documented | Faber (2007); Bris et al. (2007) |
| Short selling trigger (macro/CBK) | Inferred; Ganji Protocol connection | Bris et al. (2007) |
| FourFront's specific parameters | Not public | Proprietary |

---

## Pillar 2: Forex Algorithms (Pending)

*To be completed. Scope: CBK BMatch order book mechanics, bank treasury desk algorithms, broker execution algorithms, interbank market microstructure.*

---

## Pillar 3: Crypto and Mobile Money Algorithms (Pending)

*To be completed. Scope: Trade For Impact's Zignaly-based strategies, Binance P2P KES/USDT pricing mechanics, M-Pesa routing algorithms and their effect on KES liquidity.*

---

## References

- Almgren, R. and Chriss, N. (2001). "Optimal Execution of Portfolio Transactions." *Journal of Risk*, 3(2), 5-39.
- Appel, G. (1979). *The Moving Average Convergence-Divergence Method*. Great Neck: Signalert.
- Berkowitz, S., Logue, D., and Noser, E. (1988). "The Total Cost of Transactions on the NYSE." *Journal of Finance*, 43(1), 97-112.
- Bris, A., Goetzmann, W., and Zhu, N. (2007). "Efficiency and the Bear: Short Sales and Markets Around the World." *Journal of Finance*, 62(3), 1029-1079.
- Engle, R. and Granger, C. (1987). "Co-integration and Error Correction: Representation, Estimation, and Testing." *Econometrica*, 55(2), 251-276.
- Faber, M. (2007). "A Quantitative Approach to Tactical Asset Allocation." *Journal of Wealth Management*, 9(4), 69-79.
- Gatev, E., Goetzmann, W., and Rouwenhorst, K. (2006). "Pairs Trading: Performance of a Relative-Value Arbitrage Rule." *Review of Financial Studies*, 19(3), 797-827.
- Jegadeesh, N. and Titman, S. (1993). "Returns to Buying Winners and Selling Losers." *Journal of Finance*, 48(1), 65-91.
- Karungu, R., Memba, F., and Muturi, W. (2018). "Influence of Momentum Effect on Stock Performance of Firms Listed in the Nairobi Securities Exchange."
- Markowitz, H. (1952). "Portfolio Selection." *Journal of Finance*, 7(1), 77-91.
- Tokat, Y. and Wicas, N. (2007). "Portfolio Rebalancing in Theory and Practice." *Journal of Investing*, 16(2), 52-59.
- Wilder, J. (1978). *New Concepts in Technical Trading Systems*. Trend Research.
