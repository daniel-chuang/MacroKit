# Comprehensive Macro/RV Rates Strategy Catalog

**Legend:**

- ⭐⭐⭐ = Core strategy, widely used by institutions
- ⭐⭐ = Common, solid risk-adjusted returns
- ⭐ = Specialized/opportunistic, lower frequency

**Data Frequency:**

- 📅 = Daily EOD sufficient
- ⏰ = Intraday helpful but not required
- ⚡ = Intraday/real-time required

---

## 1. DIRECTIONAL MACRO STRATEGIES

### Fed Policy / Rate Direction

| Strategy                         | Stars  | Freq | Horizon     | Est. Sharpe | Leverage | Description                                                                                                                 | Data Dependencies                                                                                                            |
| -------------------------------- | ------ | ---- | ----------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **FOMC front-running**           | ⭐⭐   | 📅   | 2-6 weeks   | 0.6-0.9     | 3-5x     | Position ahead of Fed meetings based on economic data surprises and Fed speak. Go long duration if data weak, short if hot. | `us_economic_indicators` (NFP, CPI, PCE), `us_market_data` (Fed Funds futures), `fomc_events`, SOFR futures                  |
| **Dot plot divergence**          | ⭐⭐⭐ | 📅   | 3-9 months  | 0.8-1.2     | 3-5x     | Trade the gap between market pricing (Fed Funds futures) and FOMC dot plot projections. Fade extremes.                      | `us_market_data` (Fed Funds futures, SOFR futures), `fomc_events` (dot plots), Fed Funds OIS curve                           |
| **Economic surprise momentum**   | ⭐⭐   | 📅   | 1-3 months  | 0.5-0.8     | 3-4x     | Trade direction based on Citi/Bloomberg economic surprise indices. Positive surprises → rates up, negative → rates down.    | `us_economic_indicators` (all major releases), `economic_surprises` (calculated), `us_treasury_yields`                       |
| **Unemployment-inflation trade** | ⭐⭐   | 📅   | 3-12 months | 0.6-1.0     | 2-4x     | Phillips curve positioning. Rising unemployment → rally bonds. Hot labor market → sell bonds.                               | `us_economic_indicators` (UNRATE, wage growth, CPI), `us_treasury_yields`, `us_market_data` (VIX)                            |
| **Recession positioning**        | ⭐⭐⭐ | 📅   | 6-24 months | 0.9-1.4     | 2-3x     | Buy duration when recession indicators flash (inverted curve, LEI, credit spreads widening).                                | `us_treasury_yields` (curve inversion), `us_economic_indicators` (LEI), `equity_indices` (credit spreads), `yield_curve_pca` |
| **QE/QT flow impact**            | ⭐⭐   | 📅   | 3-12 months | 0.7-1.1     | 2-4x     | Position based on Fed balance sheet expansion/contraction. QT → higher term premium. QE → lower yields.                     | Fed balance sheet data (FRED: WALCL), `us_treasury_yields`, `fitted_curve_parameters` (term premium estimates)               |

### Inflation Strategies

| Strategy                      | Stars  | Freq | Horizon     | Est. Sharpe | Leverage | Description                                                                                               | Data Dependencies                                                                                                    |
| ----------------------------- | ------ | ---- | ----------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **TIPS breakeven trades**     | ⭐⭐⭐ | 📅   | 6-24 months | 0.8-1.2     | 2-3x     | Trade nominal UST vs TIPS based on inflation expectations. Buy breakevens if CPI surprises likely.        | `us_treasury_yields` (nominal), TIPS yields (separate table needed), `us_economic_indicators` (CPI, PCE), oil prices |
| **Oil-inflation correlation** | ⭐⭐   | 📅   | 2-6 months  | 0.5-0.9     | 3-5x     | Front-end rates tied to oil prices. Rising oil → Fed hikes → sell 2Y. Falling oil → rally front end.      | `us_market_data` (WTI crude), `us_economic_indicators` (CPI), `us_treasury_yields` (2Y focus)                        |
| **Wage growth trades**        | ⭐⭐   | 📅   | 3-9 months  | 0.6-1.0     | 3-4x     | Average hourly earnings surprises lead Fed policy. Strong wages → curve flattening (front end sells off). | `us_economic_indicators` (average hourly earnings, NFP), `us_treasury_yields`, `calculated_spreads` (2s10s)          |
| **Commodity basket signal**   | ⭐     | 📅   | 2-6 months  | 0.4-0.7     | 3-4x     | Basket of commodities (CRB index) predicts inflation. Rising commodities → sell bonds 3-6 months forward. | `us_market_data` (CRB index, gold, copper), `us_economic_indicators` (CPI), `us_treasury_yields`                     |

### Growth / Risk Appetite

| Strategy                       | Stars  | Freq | Horizon     | Est. Sharpe | Leverage | Description                                                                                                                   | Data Dependencies                                                                                           |
| ------------------------------ | ------ | ---- | ----------- | ----------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Equities-bonds correlation** | ⭐⭐⭐ | 📅   | 1-6 months  | 0.7-1.1     | 2-4x     | When stocks rally hard, bonds often sell off (risk-on). When stocks crash, bonds rally (flight to quality). Trade the regime. | `equity_indices` (SPX, NDX), `us_treasury_yields`, rolling correlation calculations, `us_market_data` (VIX) |
| **Credit spreads signal**      | ⭐⭐⭐ | 📅   | 2-8 weeks   | 0.9-1.3     | 2-3x     | Widening IG/HY spreads → buy Treasuries (flight to quality). Tightening spreads → sell Treasuries.                            | `us_market_data` (CDX IG, CDX HY spreads), `us_treasury_yields`, `equity_indices` (VIX)                     |
| **ISM manufacturing trades**   | ⭐⭐   | 📅   | 1-3 months  | 0.5-0.8     | 3-5x     | ISM >55 → strong growth → sell bonds. ISM <45 → recession fears → buy bonds.                                                  | `us_economic_indicators` (ISM manufacturing, ISM services), `us_treasury_yields`                            |
| **Global growth divergence**   | ⭐     | 📅   | 3-12 months | 0.4-0.8     | 2-4x     | US exceptionalism → dollar strength + higher US yields. Weak global growth → US yield rally.                                  | `us_market_data` (DXY), international yield data, `us_treasury_yields`, global PMI data                     |

---

## 2. CURVE STRATEGIES

### Steepeners / Flatteners

| Strategy                    | Stars  | Freq | Horizon      | Est. Sharpe | Leverage | Description                                                                                                         | Data Dependencies                                                                                           |
| --------------------------- | ------ | ---- | ------------ | ----------- | -------- | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **2s10s mean reversion**    | ⭐⭐⭐ | 📅   | 2-8 weeks    | 1.0-1.5     | 3-5x     | When 2s10s spread hits 2+ stdev from mean, fade it. Historical range: -50bp to +280bp (extreme: inverted vs steep). | `us_treasury_yields` (2Y, 10Y), `calculated_spreads` (2s10s with z-scores), `yield_curve_pca`               |
| **5s30s carry steepener**   | ⭐⭐   | 📅   | 3-12 months  | 0.7-1.1     | 2-4x     | Long 30Y, short 5Y. Collect positive carry while betting on steepening. Works in stable/easing environments.        | `us_treasury_yields` (5Y, 30Y), `calculated_spreads`, carry calculations, repo rates                        |
| **FOMC curve flattener**    | ⭐⭐   | 📅   | 4-8 weeks    | 0.8-1.2     | 3-4x     | Pre-FOMC: curve flattens as front end prices in hikes. Post-FOMC: often reverses. Trade the pattern.                | `us_treasury_yields`, `fomc_events` (meeting calendar), `calculated_spreads` (2s10s, 5s30s)                 |
| **Recession steepener**     | ⭐⭐⭐ | 📅   | 6-18 months  | 0.9-1.4     | 2-3x     | As recession nears, curve steepens (front end rallies on cut expectations). Classic late-cycle trade.               | `us_treasury_yields`, `us_economic_indicators` (LEI, unemployment), `calculated_spreads`, `yield_curve_pca` |
| **Term premium extraction** | ⭐     | 📅   | 12-36 months | 0.5-0.9     | 1-3x     | Long backend vs front when term premium compressed. ACM model indicates fair value.                                 | `us_treasury_yields`, `fitted_curve_parameters` (term premium models like ACM), Fed balance sheet data      |

### Butterfly Trades

| Strategy                 | Stars  | Freq | Horizon   | Est. Sharpe | Leverage | Description                                                                               | Data Dependencies                                                                                         |
| ------------------------ | ------ | ---- | --------- | ----------- | -------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **2s5s10s fly**          | ⭐⭐⭐ | 📅   | 2-6 weeks | 1.2-1.8     | 4-6x     | Most liquid butterfly. Trade z-score: (2×5Y) - 2Y - 10Y. Mean reversion when \|z\| > 1.5. | `us_treasury_yields` (2Y, 5Y, 10Y), `calculated_spreads` (butterfly with z-scores, percentiles)           |
| **5s10s30s fly**         | ⭐⭐   | 📅   | 2-8 weeks | 1.0-1.5     | 4-6x     | Backend butterfly. Responds to supply (auction cycle) and convexity hedging flows.        | `us_treasury_yields` (5Y, 10Y, 30Y), `us_auctions` (supply calendar), `calculated_spreads`                |
| **Condor (2s5s10s30s)**  | ⭐     | 📅   | 3-8 weeks | 0.8-1.2     | 5-7x     | Four-point trade. Isolates specific curve segment richness/cheapness. More complex risk.  | `us_treasury_yields` (2Y, 5Y, 10Y, 30Y), `calculated_spreads`, `yield_curve_pca` (for risk decomposition) |
| **Auction-driven flies** | ⭐⭐   | 📅   | 1-3 weeks | 1.3-1.9     | 4-6x     | Butterflies cheapen into auctions (supply), richen after. Trade around Treasury calendar. | `us_treasury_yields`, `us_auctions` (auction calendar, results), `calculated_spreads`                     |

---

## 3. SWAP-RELATED RV STRATEGIES

### Swap Spreads

| Strategy                           | Stars  | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                                                | Data Dependencies                                                                                                 |
| ---------------------------------- | ------ | ---- | ---------- | ----------- | -------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **10Y swap spread mean reversion** | ⭐⭐⭐ | 📅   | 4-12 weeks | 0.9-1.3     | 3-5x     | 10Y swap spread vs Treasury. Historical range: -50 to +50bp. Trade extremes back to mean (currently ~+25bp).               | `us_swap_rates` (10Y SOFR OIS), `us_treasury_yields` (10Y), `calculated_spreads` (swap spreads with z-scores)     |
| **2Y swap spread momentum**        | ⭐⭐   | 📅   | 2-6 weeks  | 0.6-1.0     | 4-6x     | Front-end swap spreads more volatile, driven by LIBOR/SOFR vs Fed Funds. Trend-following works better than mean reversion. | `us_swap_rates` (2Y), `us_treasury_yields` (2Y), `us_market_data` (Fed Funds, SOFR), `calculated_spreads`         |
| **Swap spread curve trade**        | ⭐     | 📅   | 4-12 weeks | 0.5-0.9     | 3-5x     | 2Y swap spread vs 10Y swap spread. Divergences signal funding stress or regulatory changes.                                | `us_swap_rates` (2Y, 10Y), `us_treasury_yields` (2Y, 10Y), `calculated_spreads` (swap spread differential)        |
| **Cross-currency basis**           | ⭐     | 📅   | 8-24 weeks | 0.4-0.8     | 2-4x     | USD vs EUR/JPY/GBP swap spreads reflect FX hedging demand. Extreme bases mean-revert.                                      | `us_swap_rates`, international swap rates (not in schema), `us_market_data` (FX rates), cross-currency basis data |

### Basis Trades

| Strategy                  | Stars | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                         | Data Dependencies                                                                                               |
| ------------------------- | ----- | ---- | ---------- | ----------- | -------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **SOFR-Fed Funds basis**  | ⭐⭐  | 📅   | 2-8 weeks  | 0.7-1.1     | 4-6x     | Spread between SOFR OIS and Fed Funds OIS reflects term repo dynamics. Widens at month/quarter end. | `us_swap_rates` (SOFR OIS, Fed Funds OIS), `us_market_data` (SOFR, Fed Funds), repo rates, `calculated_spreads` |
| **LIBOR-OIS spread**      | ⭐    | 📅   | Historical | N/A         | N/A      | Legacy: measured bank credit risk. Blew out in 2008 (400bp). Post-2023: archival interest only.     | `us_swap_rates` (legacy LIBOR), `us_market_data` (historical LIBOR), OIS rates                                  |
| **FRA-futures arbitrage** | ⭐    | 📅   | 1-4 weeks  | 0.6-1.0     | 5-8x     | Forward Rate Agreements vs SOFR futures. Small mispricings exploitable with low transaction costs.  | `us_treasury_futures` (SOFR futures), FRA rates (not in schema), `us_swap_rates`                                |

---

## 4. FUTURES-BASED STRATEGIES

### Calendar Spreads

| Strategy               | Stars  | Freq | Horizon     | Est. Sharpe | Leverage | Description                                                                                                      | Data Dependencies                                                                                  |
| ---------------------- | ------ | ---- | ----------- | ----------- | -------- | ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Futures roll trade** | ⭐⭐⭐ | 📅⏰ | 1-4 weeks   | 1.1-1.6     | 4-6x     | Long back contract, short front contract as front rolls off. Capture roll yield. Usually profitable in contango. | `us_treasury_futures` (front and back contracts, open interest), roll calendar, basis calculations |
| **White pack spreads** | ⭐⭐   | 📅   | 3-12 months | 0.7-1.1     | 3-5x     | SOFR futures pack spreads (quarterly strip). Trade Fed path expectations across the curve.                       | `us_treasury_futures` (SOFR futures - SR3), `us_market_data` (Fed Funds futures), `fomc_events`    |
| **Red-green spread**   | ⭐     | 📅   | 6-18 months | 0.5-0.9     | 3-5x     | Front pack (reds) vs second pack (greens). Isolates near-term vs medium-term rate expectations.                  | `us_treasury_futures` (SOFR futures packs), Fed path pricing                                       |
| **NOB spread**         | ⭐⭐⭐ | 📅   | 2-12 weeks  | 0.9-1.3     | 4-6x     | Notes Over Bonds: 10Y futures (ZN) vs 30Y (ZB). Pure curve trade using futures. Liquid, low transaction costs.   | `us_treasury_futures` (ZN, ZB), `calculated_spreads` (NOB z-scores), DV01 calculations             |
| **TUT spread**         | ⭐⭐   | 📅   | 2-12 weeks  | 0.8-1.2     | 4-6x     | Twos, Tens, Ultra: 2Y (ZT) vs 10Y (ZN) vs Ultra (UB). Three-legged curve expression.                             | `us_treasury_futures` (ZT, ZN, UB), `calculated_spreads`, DV01-neutral ratio calculations          |

### Basis (Cash-Futures)

| Strategy                        | Stars  | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                                | Data Dependencies                                                                                              |
| ------------------------------- | ------ | ---- | ---------- | ----------- | -------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Gross basis trade**           | ⭐⭐⭐ | 📅   | 2-8 weeks  | 1.0-1.4     | 5-8x     | Long futures, short CTD (cheapest-to-deliver) bond. Earn carry, converges to zero at delivery.             | `us_treasury_futures`, `us_treasury_prices` (CTD bond), `treasury_securities` (conversion factors), repo rates |
| **Net basis (implied repo)**    | ⭐⭐⭐ | 📅   | 2-8 weeks  | 1.1-1.5     | 5-8x     | Basis trade adjusted for financing. Exploit when implied repo rate deviates from actual GC repo.           | `us_treasury_futures`, `us_treasury_prices` (CTD), repo rates (GC and special), carry calculations             |
| **Delivery option value**       | ⭐     | 📅   | 4-12 weeks | 0.6-1.0     | 4-6x     | Short futures has delivery options (timing, quality, wild card). Model and trade the embedded optionality. | `us_treasury_futures`, `us_treasury_prices` (deliverable basket), `treasury_securities`, option pricing models |
| **Switch trades (CTD changes)** | ⭐⭐   | 📅⏰ | 2-6 weeks  | 0.8-1.2     | 4-6x     | When CTD switches (rate moves), old CTD richens, new cheapens. Trade the transition.                       | `us_treasury_futures`, `us_treasury_prices`, `treasury_securities` (deliverable basket), CTD model             |

### Futures Spread Strategies

| Strategy                   | Stars  | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                                           | Data Dependencies                                                                         |
| -------------------------- | ------ | ---- | ---------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **5Y vs 10Y futures**      | ⭐⭐⭐ | 📅   | 2-8 weeks  | 0.9-1.3     | 4-6x     | Directional curve trade using futures. Lower transaction costs than cash. DV01 neutral: DV01_10Y / DV01_5Y ≈ 2 ratio. | `us_treasury_futures` (ZF, ZN), DV01 calculations, `calculated_spreads`                   |
| **Ultra vs 30Y**           | ⭐     | 📅   | 2-8 weeks  | 0.6-1.0     | 3-5x     | Long Ultra (25Y+), short 30Y (ZB). Isolates very long end of curve. Low liquidity but unique exposure.                | `us_treasury_futures` (UB, ZB), `calculated_spreads`                                      |
| **Inter-commodity spread** | ⭐     | 📅   | 4-12 weeks | 0.5-0.8     | 3-5x     | Treasury futures vs Eurodollar futures (legacy) or SOFR futures. Isolates credit/term premium.                        | `us_treasury_futures` (Treasuries and SOFR), `calculated_spreads` (TED spread equivalent) |

---

## 5. VOLATILITY STRATEGIES

### Swaptions

| Strategy                    | Stars | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                                         | Data Dependencies                                                                    |
| --------------------------- | ----- | ---- | ---------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Straddle on FOMC**        | ⭐⭐  | 📅   | 1-4 weeks  | 0.4-0.8     | 1-2x     | Buy ATM payer + receiver swaption before Fed meeting. Profit if realized vol > implied. Expensive but defined risk. | `us_swaption_vols` (ATM vols), `fomc_events`, `realized_volatility`, `us_swap_rates` |
| **Vol surface arbitrage**   | ⭐    | 📅⏰ | 1-6 weeks  | 0.6-1.0     | 3-5x     | Exploit mispricing in swaption vol surface. E.g., 3M×10Y rich vs 6M×10Y. Requires SABR or other vol models.         | `us_swaption_vols` (full surface), SABR model parameters, `us_swap_rates`            |
| **Skew trades**             | ⭐    | 📅   | 2-8 weeks  | 0.5-0.9     | 3-4x     | Trade payer vs receiver vol at same expiry/tenor. Skew reflects market bias (hawkish → payer vol rich).             | `us_swaption_vols` (strikes across smile), `us_swap_rates`, skew calculations        |
| **Calendar spreads in vol** | ⭐    | 📅   | 4-12 weeks | 0.6-1.0     | 2-4x     | Long 6M vol, short 3M vol when term structure inverted (near-term events → front vol rich).                         | `us_swaption_vols` (multiple expiries), vol term structure, `fomc_events`            |
| **Vega carry**              | ⭐⭐  | 📅   | 3-6 months | 0.7-1.1     | 2-3x     | Sell swaption vol when implied > realized. Collect premium decay. Risky if rates volatile.                          | `us_swaption_vols`, `realized_volatility`, `us_swap_rates`, theta/vega calculations  |

### Caps/Floors

| Strategy                       | Stars | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                   | Data Dependencies                                                                |
| ------------------------------ | ----- | ---- | ---------- | ----------- | -------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Cap-floor parity arbitrage** | ⭐    | 📅   | 2-12 weeks | 0.8-1.2     | 4-6x     | Cap - Floor = Swap by put-call parity. Exploit violations with synthetic positions.           | `us_capfloor_vols`, `us_swap_rates`, parity violation calculations               |
| **Caplet spread trades**       | ⭐    | 📅   | 4-12 weeks | 0.5-0.9     | 3-5x     | Buy low-strike caplets, sell high-strike. Bet on upward rate surprises beyond market pricing. | `us_capfloor_vols` (multiple strikes), `us_swap_rates`, `us_economic_indicators` |
| **Diagonal cap spreads**       | ⭐    | 📅   | 3-9 months | 0.4-0.8     | 2-4x     | Different expiries, same strike. Isolates term structure of rate volatility.                  | `us_capfloor_vols` (term structure), `realized_volatility`                       |

### Realized Vol Strategies

| Strategy                           | Stars | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                                           | Data Dependencies                                                                           |
| ---------------------------------- | ----- | ---- | ---------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| **Vol regime switching**           | ⭐⭐  | 📅   | 2-6 months | 0.8-1.2     | 1-3x     | Model volatility regimes (GARCH, HMM). High vol → reduce duration exposure. Low vol → increase leverage.              | `realized_volatility`, `us_treasury_yields`, GARCH/HMM models, `us_market_data` (VIX, MOVE) |
| **Implied vs realized divergence** | ⭐⭐  | 📅   | 4-12 weeks | 0.7-1.1     | 2-4x     | When MOVE index (bond vol) deviates from realized vol, fade the gap. MOVE mean: ~100, spikes to 150+.                 | `us_market_data` (MOVE index), `realized_volatility`, `us_swaption_vols`                    |
| **Dispersion trades**              | ⭐    | 📅   | 4-12 weeks | 0.6-1.0     | 4-6x     | Trade correlation between different parts of curve. Sell index vol, buy individual tenor vol when correlation breaks. | `us_swaption_vols`, `yield_curve_pca`, correlation matrices, `realized_volatility`          |

---

## 6. CARRY & ROLL STRATEGIES

| Strategy                 | Stars  | Freq | Horizon     | Est. Sharpe | Leverage | Description                                                                                                              | Data Dependencies                                                                                            |
| ------------------------ | ------ | ---- | ----------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| **Pure carry**           | ⭐⭐⭐ | 📅   | 3-12 months | 0.9-1.3     | 2-4x     | Long high-yielding bonds (30Y), finance at lower rate. Earn (Y_30Y - r_repo) × time. Works in stable rate environment.   | `us_treasury_yields` (30Y), repo rates (GC), carry calculations, `realized_volatility` (for risk management) |
| **Roll-down carry**      | ⭐⭐⭐ | 📅   | 3-12 months | 1.0-1.4     | 2-4x     | Long 10Y bond, hold as it "rolls down" to 9.75Y, 9.5Y, etc. Price appreciates due to curve shape. Works on steep curves. | `us_treasury_yields` (full curve), `calculated_spreads`, roll-down calculations, repo rates                  |
| **Butterfly carry**      | ⭐⭐   | 📅   | 2-6 months  | 0.8-1.2     | 4-6x     | Construct butterfly to maximize carry while maintaining curve exposure. Balance coupon income vs financing costs.        | `us_treasury_yields`, `calculated_spreads`, carry calculations, repo rates                                   |
| **Barbell vs bullet**    | ⭐⭐   | 📅   | 6-24 months | 0.6-1.0     | 2-3x     | Barbell (2Y + 30Y) vs bullet (10Y). If curve parallel shifts, barbell earns more carry. If curve flattens, bullet wins.  | `us_treasury_yields` (2Y, 10Y, 30Y), carry calculations, `yield_curve_pca`, repo rates                       |
| **Financed carry trade** | ⭐⭐   | 📅   | 3-12 months | 0.7-1.1     | 5-10x    | Leverage via repo. Return = Leverage × (Y_bond - r_repo). Risk: rates rise or repo spikes.                               | `us_treasury_yields`, repo rates (GC and specials), `realized_volatility`, haircut calculations              |

---

## 7. SUPPLY/DEMAND TECHNICAL STRATEGIES

### Auction Dynamics

| Strategy                   | Stars  | Freq | Horizon   | Est. Sharpe | Leverage | Description                                                                                           | Data Dependencies                                                                                       |
| -------------------------- | ------ | ---- | --------- | ----------- | -------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Pre-auction cheapening** | ⭐⭐⭐ | 📅   | 3-7 days  | 1.5-2.0     | 4-6x     | Bonds cheapen 3-5bp in week before large auctions (supply overhang). Buy before, sell into auction.   | `us_auctions` (calendar, size), `us_treasury_yields`, `us_treasury_prices`, historical auction patterns |
| **Post-auction snap-back** | ⭐⭐⭐ | 📅   | 1-5 days  | 1.4-1.9     | 4-6x     | After successful auction (low tail), bonds richen back. Quick mean reversion trade.                   | `us_auctions` (results, tail), `us_treasury_yields`, `us_treasury_prices`                               |
| **Auction tail fade**      | ⭐⭐   | 📅   | 1-2 days  | 1.2-1.7     | 4-5x     | If auction tail >2bp (weak demand), fade the immediate cheapening. Often overshoots.                  | `us_auctions` (tail, bid-to-cover), `us_treasury_yields`, historical tail distributions                 |
| **Refunding cycle**        | ⭐⭐   | 📅   | 2-4 weeks | 1.0-1.4     | 3-5x     | Quarterly refunding (Feb/May/Aug/Nov): $96B+ issuance. Systematic cheapening before, richening after. | `us_auctions` (quarterly refunding calendar), `us_treasury_yields`, `us_treasury_prices`                |

### Month-End / Quarter-End

| Strategy                     | Stars  | Freq | Horizon  | Est. Sharpe | Leverage | Description                                                                                           | Data Dependencies                                                                                       |
| ---------------------------- | ------ | ---- | -------- | ----------- | -------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Month-end extension**      | ⭐⭐⭐ | 📅   | 3-7 days | 1.3-1.8     | 3-5x     | Asset managers extend duration into month-end (rebalancing). Long 2-3 days before, sell at month-end. | `us_treasury_yields`, calendar (month-end dates), `cftc_positioning`, historical patterns               |
| **Quarter-end repo squeeze** | ⭐⭐   | 📅   | 1-3 days | 1.1-1.6     | 4-6x     | Repo rates spike at quarter-end (balance sheet constraints). Impacts Treasury basis and swap spreads. | Repo rates (GC and specials), `us_treasury_futures`, `calculated_spreads` (basis), quarter-end calendar |
| **Window dressing**          | ⭐     | 📅   | 1-5 days | 0.8-1.2     | 2-4x     | Banks/funds reduce leverage at quarter-end. Systematic patterns: sell risk assets, buy Treasuries.    | `us_treasury_yields`, `equity_indices`, quarter-end calendar, historical flow patterns                  |

### Seasonality

| Strategy            | Stars | Freq | Horizon   | Est. Sharpe | Leverage | Description                                                                                            | Data Dependencies                                                    |
| ------------------- | ----- | ---- | --------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| **January effect**  | ⭐⭐  | 📅   | 2-4 weeks | 1.0-1.4     | 3-4x     | Bonds rally in January historically (tax loss harvesting reversal, new money flows). Statistical edge. | `us_treasury_yields`, historical January returns, calendar           |
| **Summer doldrums** | ⭐    | 📅   | 4-8 weeks | 0.6-1.0     | 2-3x     | July-August: lower volumes, lower volatility. Mean-reversion strategies work better. Avoid momentum.   | `us_treasury_yields`, `realized_volatility`, volume data, calendar   |
| **Year-end rally**  | ⭐⭐  | 📅   | 4-6 weeks | 0.9-1.3     | 3-4x     | November-December: Santa rally spillover into bonds. Positive seasonal bias.                           | `us_treasury_yields`, `equity_indices`, historical year-end patterns |

---

## 8. POSITIONING & SENTIMENT STRATEGIES

### CFTC Positioning

| Strategy                       | Stars  | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                             | Data Dependencies                                                                          |
| ------------------------------ | ------ | ---- | ---------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Leveraged funds contrarian** | ⭐⭐⭐ | 📅   | 2-8 weeks  | 1.3-1.8     | 3-5x     | When leveraged funds hit extreme net short/long (>2 stdev), fade. Crowded trades unwind.                | `cftc_positioning` (leveraged funds category), `us_treasury_futures`, z-score calculations |
| **Asset manager momentum**     | ⭐⭐   | 📅   | 4-12 weeks | 0.7-1.1     | 3-4x     | Asset managers trend-follow. Join their positioning for intermediate term.                              | `cftc_positioning` (asset manager category), `us_treasury_futures`                         |
| **Commercial hedger signal**   | ⭐     | 📅   | 4-12 weeks | 0.6-1.0     | 3-4x     | Commercials (dealers) often right at extremes. When they flip positioning, follow.                      | `cftc_positioning` (dealer/commercial category), `us_treasury_futures`                     |
| **Positioning delta**          | ⭐⭐   | 📅   | 1-4 weeks  | 0.8-1.2     | 4-6x     | Weekly change in net positioning predicts next week's returns. Large positioning swings → continuation. | `cftc_positioning` (weekly changes), `us_treasury_futures`                                 |

### Dealer Positioning

| Strategy                      | Stars | Freq | Horizon   | Est. Sharpe | Leverage | Description                                                                                                  | Data Dependencies                                                                                            |
| ----------------------------- | ----- | ---- | --------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| **Primary dealer survey**     | ⭐⭐  | 📅   | 2-8 weeks | 0.7-1.1     | 3-4x     | FRBNY dealer survey shows expected rate path. Deviations from market pricing = trade signal.                 | FRBNY primary dealer survey data (not in schema), `us_treasury_yields`, `us_market_data` (Fed Funds futures) |
| **Dealer inventory extremes** | ⭐    | 📅   | 2-6 weeks | 0.6-1.0     | 3-5x     | FINRA data: when dealers accumulate large positions, often signals reversal (they're stuck, need to unload). | Dealer inventory data (not in schema), `us_treasury_prices`                                                  |

### Retail Sentiment

| Strategy                 | Stars | Freq | Horizon   | Est. Sharpe | Leverage | Description                                                                                       | Data Dependencies                                                        |
| ------------------------ | ----- | ---- | --------- | ----------- | -------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **Bond fund flows**      | ⭐⭐  | 📅   | 2-8 weeks | 0.8-1.2     | 2-4x     | ICI weekly fund flows. Large outflows from bond funds → contrarian buy signal (retail panic).     | ICI fund flow data (not in schema), `us_treasury_yields`                 |
| **ETF premium/discount** | ⭐⭐  | 📅   | 1-5 days  | 0.9-1.3     | 3-5x     | TLT/IEF trading at premium to NAV → excessive bullishness. Discount → bearishness. Fade extremes. | ETF data (TLT, IEF prices and NAV - not in schema), `us_treasury_yields` |

---

## 9. CROSS-ASSET / MACRO CORRELATION

| Strategy                          | Stars | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                                               | Data Dependencies                                                                                      |
| --------------------------------- | ----- | ---- | ---------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Equity-bond correlation trade** | ⭐⭐  | 📅   | 4-12 weeks | 0.6-1.0     | 2-4x     | When stocks and bonds correlate positively (unusual), inflation fears. When negative, growth fears. Trade regime changes. | `equity_indices` (SPX), `us_treasury_yields`, rolling correlation calculations, `us_market_data` (VIX) |
| **Dollar-yields correlation**     | ⭐⭐  | 📅   | 2-8 weeks  | 0.5-0.9     | 3-5x     | Strong dollar → higher US yields (carry trade). Weak dollar → lower yields. Lead-lag relationship.                        | `us_market_data` (DXY), `us_treasury_yields`, correlation calculations                                 |
| **Gold-real yields**              | ⭐⭐  | 📅   | 4-16 weeks | 0.7-1.1     | 2-3x     | Gold inversely correlated with real yields. Rising TIPS yields → sell gold, buy bonds. Falling → opposite.                | `us_market_data` (gold price), TIPS yields (not in schema), `us_treasury_yields`                       |
| **VIX-MOVE correlation**          | ⭐    | 📅   | 1-4 weeks  | 0.6-1.0     | 3-4x     | VIX (equity vol) and MOVE (bond vol) usually correlate. Divergences = opportunity. Low MOVE + high VIX → buy bonds.       | `us_market_data` (VIX, MOVE), `us_treasury_yields`, correlation calculations                           |
| **Oil-breakevens**                | ⭐⭐  | 📅   | 4-12 weeks | 0.6-1.0     | 3-4x     | Oil leads inflation expectations by 3-6 months. Rising oil → sell TIPS breakevens forward. Model lag structure.           | `us_market_data` (WTI crude), TIPS breakevens (not in schema), `us_economic_indicators` (CPI)          |
| **EM risk appetite**              | ⭐    | 📅   | 4-12 weeks | 0.5-0.9     | 2-4x     | EM currency weakness → flight to Treasuries. EM strength → Treasuries sell off. Use EM FX basket as signal.               | EM FX data (not in schema), `us_treasury_yields`, `us_market_data` (VIX)                               |

---

## 10. QUANTITATIVE / STATISTICAL STRATEGIES

### Mean Reversion

| Strategy                  | Stars  | Freq | Horizon   | Est. Sharpe | Leverage | Description                                                                                                  | Data Dependencies                                                                     |
| ------------------------- | ------ | ---- | --------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| **Z-score reversion**     | ⭐⭐⭐ | 📅   | 1-6 weeks | 1.2-1.7     | 4-6x     | Any spread (curve, swap, basis) with \|z\| > 2 mean-reverts. Entry at 2σ, exit at 0. Hold 2-4 weeks average. | `calculated_spreads` (all types with z-scores), `us_treasury_yields`, `us_swap_rates` |
| **Cointegration pairs**   | ⭐⭐   | 📅   | 2-8 weeks | 1.0-1.4     | 4-6x     | Find cointegrated bond pairs (e.g., 7Y vs interpolated 5Y-10Y). Trade deviations from equilibrium.           | `us_treasury_yields` (full curve), cointegration tests, error correction model        |
| **Bollinger band bounce** | ⭐     | 📅   | 1-4 weeks | 0.7-1.1     | 3-5x     | When yields hit 2σ Bollinger bands, fade the move. Works in range-bound markets.                             | `us_treasury_yields`, Bollinger band calculations, `realized_volatility`              |

### Momentum

| Strategy                 | Stars | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                                        | Data Dependencies                                                                             |
| ------------------------ | ----- | ---- | ---------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| **Time-series momentum** | ⭐⭐  | 📅   | 4-12 weeks | 0.6-1.0     | 3-5x     | 12-month momentum in yields. If yields rising for 6+ months, stay short. If falling, stay long. Trend persistence. | `us_treasury_yields`, momentum calculations (3M, 6M, 12M returns)                             |
| **Dual momentum**        | ⭐    | 📅   | 8-16 weeks | 0.5-0.9     | 2-4x     | Combine absolute momentum (trend) with relative momentum (vs other assets). Switch between bonds and alternatives. | `us_treasury_yields`, `equity_indices`, `us_market_data` (commodities), momentum calculations |
| **Breakout trading**     | ⭐    | 📅   | 2-8 weeks  | 0.5-0.8     | 3-5x     | When yields break multi-month range, momentum continues 60% of time. Ride initial 2-4 weeks.                       | `us_treasury_yields`, support/resistance levels, breakout detection                           |

### Factor Models

| Strategy                    | Stars  | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                            | Data Dependencies                                                                              |
| --------------------------- | ------ | ---- | ---------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| **PCA factor trading**      | ⭐⭐⭐ | 📅   | 2-8 weeks  | 0.9-1.3     | 3-5x     | Decompose curve into level/slope/curvature. Trade when factors hit extremes (e.g., curvature 2σ rich). | `yield_curve_pca` (pre-computed factors), `us_treasury_yields`, factor z-scores                |
| **Macro factor timing**     | ⭐⭐   | 📅   | 4-12 weeks | 0.7-1.1     | 2-4x     | Regression model: yields = f(growth, inflation, Fed, sentiment). When residuals large, fade.           | `us_economic_indicators`, `us_treasury_yields`, `us_market_data`, regression residuals         |
| **Regime-switching models** | ⭐⭐   | 📅   | 8-24 weeks | 0.8-1.2     | 2-3x     | HMM or Markov-switching model identifies bull/bear/sideways regimes. Adjust duration accordingly.      | `us_treasury_yields`, `realized_volatility`, `us_economic_indicators`, HMM state probabilities |

### Machine Learning

| Strategy                      | Stars | Freq | Horizon   | Est. Sharpe | Leverage | Description                                                                                                         | Data Dependencies                                                                                          |
| ----------------------------- | ----- | ---- | --------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Random forest prediction**  | ⭐⭐  | 📅   | 1-4 weeks | 0.6-1.0     | 3-5x     | Train RF on 100+ features (econ data, technical, sentiment). Predict next week's yield direction. Rebalance weekly. | `us_economic_indicators`, `us_treasury_yields`, `us_market_data`, `cftc_positioning`, technical indicators |
| **Gradient boosting returns** | ⭐⭐  | 📅   | 1-8 weeks | 0.7-1.1     | 3-5x     | XGBoost on high-dimensional feature space. Predict forward returns. Top/bottom quintile → long/short.               | Same as RF + engineered features, lagged variables                                                         |
| **LSTM sequence models**      | ⭐    | 📅   | 2-8 weeks | 0.5-0.9     | 3-5x     | Recurrent network on time series. Learns temporal patterns in yields. Generates directional signals.                | `us_treasury_yields` (sequences), `us_economic_indicators`, normalized features                            |
| **Reinforcement learning**    | ⭐    | 📅   | Adaptive  | 0.4-0.8     | 2-4x     | RL agent learns optimal policy for entering/exiting positions. State = market features, reward = Sharpe.            | All market data, custom reward function, state representation                                              |

---

## 11. SPECIALTY / ADVANCED STRATEGIES

### Convexity

| Strategy                       | Stars | Freq | Horizon     | Est. Sharpe | Leverage | Description                                                                                                                     | Data Dependencies                                                                                            |
| ------------------------------ | ----- | ---- | ----------- | ----------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Mortgage convexity hedging** | ⭐⭐  | 📅⏰ | 1-4 weeks   | 0.7-1.1     | 2-4x     | When rates drop, mortgage portfolios extend duration (negative convexity). They sell Treasuries to hedge. Trade into this flow. | MBS data (not in schema), `us_treasury_yields`, `realized_volatility`, mortgage OAS spreads                  |
| **Gamma scalping bonds**       | ⭐    | 📅⏰ | Days-weeks  | 0.5-0.9     | 3-5x     | Long optionality (swaptions/bond options), delta-hedge. Profit from realized vol > implied vol.                                 | `us_swaption_vols`, `realized_volatility`, `us_treasury_yields` or `us_swap_rates`, delta/gamma calculations |
| **Barbell for convexity**      | ⭐    | 📅   | 6-24 months | 0.6-1.0     | 2-3x     | Barbell (short + long duration) has positive convexity vs bullet. Outperforms in volatile markets.                              | `us_treasury_yields`, convexity calculations, `realized_volatility`                                          |

### International Arbitrage

| Strategy                       | Stars | Freq | Horizon    | Est. Sharpe | Leverage | Description                                                                                                                 | Data Dependencies                                                                                  |
| ------------------------------ | ----- | ---- | ---------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Covered interest parity**    | ⭐    | 📅   | 4-12 weeks | 0.5-0.9     | 4-6x     | Borrow in USD, invest in EUR Bunds, hedge FX. Profit when CIP deviates (basis). Post-2008: persistent deviations.           | `us_treasury_yields`, international bond yields (not in schema), FX forwards, cross-currency basis |
| **Rate differential momentum** | ⭐    | 📅   | 8-24 weeks | 0.5-0.8     | 2-4x     | Fed vs ECB/BoJ rate differentials drive yield spreads. When differentials widen, US yields rise relatively. Trade momentum. | `us_market_data` (Fed Funds), international rate data (not in schema), `us_treasury_yields`        |
| **Global curve arbitrage**     | ⭐    | 📅   | 4-16 weeks | 0.4-0.8     | 3-5x     | US 2s10s vs Germany 2s10s. When spreads diverge >1.5σ, convergence trade. Reflects synchronized global growth.              | `calculated_spreads` (2s10s), international curve data (not in schema), correlation analysis       |

### Structured Products

| Strategy                | Stars | Freq | Horizon      | Est. Sharpe | Leverage | Description                                                                                                | Data Dependencies                                                                |
| ----------------------- | ----- | ---- | ------------ | ----------- | -------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Callable bond basis** | ⭐    | 📅   | 8-24 weeks   | 0.6-1.0     | 2-4x     | Callable agencies trade cheap to non-callables by embedded option value. When gap too wide, buy callables. | Agency bond data (not in schema), `us_swaption_vols`, OAS calculations           |
| **CMS spread options**  | ⭐    | 📅   | 12-36 months | 0.5-0.9     | 2-3x     | Constant Maturity Swap spread options. Bet on curve steepening/flattening with defined risk.               | `us_swap_rates`, CMS spread option data (not in schema), `calculated_spreads`    |
| **Range accruals**      | ⭐    | 📅   | 6-24 months  | 0.5-0.8     | 1-2x     | Accrue interest if rate stays in range. Sell when volatility underpriced. Buy when overpriced.             | `us_swap_rates`, `realized_volatility`, `us_swaption_vols`, range accrual pricer |

---

## DATA DEPENDENCIES SUMMARY

### Critical Tables (Must Have)

- [x] `us_treasury_yields` - Used by 95%+ of strategies
  - [ ] Forward + spot curves
- [ ] `us_cusip` - CUSIP level data
- [ ] `us_forwards` -
- [ ] `us_treasury_futures` - Essential for futures strategies (25% of catalog)
- [ ] `calculated_spreads` - Pre-computed spreads with z-scores (critical for RV)
- [x] `us_economic_indicators` - Macro positioning (60% of strategies)
- [x] `us_market_data` - Fed Funds, SOFR, VIX, commodities, FX
- [ ] `cftc_positioning` - Sentiment/positioning strategies

### Important Tables (High Value)

- [ ] `us_swap_rates` - Swap spread strategies
- [ ] `us_swaption_vols` - Volatility strategies
- [ ] `us_auctions` - Auction cycle strategies (high Sharpe)
- [ ] `realized_volatility` - Risk management, vol strategies
- [ ] `yield_curve_pca` - Factor-based strategies
- [ ] `fomc_events` - Fed policy positioning

### Useful Tables (Enhanced Analysis)

- `us_treasury_prices` - Basis trades, liquidity analysis
- `us_capfloor_vols` - Cap/floor strategies
- `fitted_curve_parameters` - Advanced curve modeling
- `equity_indices` - Cross-asset correlation
- `treasury_securities` - Reference data

### Missing Tables (Would Need to Add)

- TIPS yields and breakevens
- Repo rates (GC and specials)
- MBS data
- ETF prices (TLT, IEF)
- Fund flow data (ICI)
- Dealer inventory
- International bond yields
- FX forwards/cross-currency basis

---

## STRATEGY SELECTION GUIDE

### Highest Sharpe (>1.3)

1. Pre-auction cheapening (1.5-2.0)
2. Post-auction snap-back (1.4-1.9)
3. 2s5s10s butterfly (1.2-1.8)
4. Leveraged funds contrarian (1.3-1.8)
5. Month-end extension (1.3-1.8)
6. Z-score reversion (1.2-1.7)

### Best for Beginners (Simple + Good Sharpe)

1. 2s10s mean reversion (⭐⭐⭐, 1.0-1.5)
2. Auction cycle trades (⭐⭐⭐, 1.3-1.9)
3. Pure carry (⭐⭐⭐, 0.9-1.3)
4. CFTC contrarian (⭐⭐⭐, 1.3-1.8)

### Most Institutional (Core Holdings)

1. Dot plot divergence
2. Recession positioning
3. 2s10s mean reversion
4. 2s5s10s butterfly
5. NOB spread
6. Gross/net basis
7. Roll-down carry

### Low Leverage Required (<3x)

1. Recession positioning (2-3x)
2. Pure carry (2-4x)
3. Barbell vs bullet (2-3x)
4. Vol regime switching (1-3x)
5. Macro factor timing (2-4x)

### High Leverage Strategies (>5x)

1. Gross basis (5-8x)
2. Net basis (5-8x)
3. Financed carry (5-10x)
4. 2s5s10s butterfly (4-6x)
5. Futures roll trade (4-6x)
