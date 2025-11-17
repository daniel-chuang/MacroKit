For a comprehensive macro trading library focused on US rates with RV (relative value) and macro analysis, you'll need several categories of data:

## Market Data

**Rates Curves & Fixings**

- [ ] SOFR fixings and forward curves
- [ ] Fed Funds rates (historical and implied)
- [ ] Treasury yield curves (on-the-run and off-the-run)
- [ ] Swap curves (SOFR-based, legacy LIBOR for historical analysis)
- [ ] OIS curves
- [ ] LIBOR historical data (for backtesting)

**Futures**

- [ ] Treasury futures (ZN, ZB, ZF, ZT, UB)
- [ ] prices, open interest, volume
- [ ] SOFR futures (SR3, SFI)
- [ ] full term structure
- [ ] Fed Funds futures
- [ ] Eurodollar futures (historical, for pre-SOFR analysis)

**Cash Bonds**

- [ ] UST prices, yields, and spreads across the curve
- [ ] Coupon schedules and maturity dates
- [ ] Auction data and WI (when-issued) levels
- [ ] TIPS data for breakeven inflation

**Options & Volatility**

- [ ] Swaption volatility surfaces (payer/receiver, various tenors and expirations)
- [ ] Cap/floor volatility surfaces
- [ ] Treasury futures options (implied vol, skew)
- [ ] MOVE index (bond market volatility)

## Fundamental & Macro Data

**Central Bank**

- [ ] FOMC meeting dates, decisions, and dot plots
- [ ] Fed balance sheet data (QT/QE operations)
- [ ] Fed speeches and minutes
- [ ] Market-implied Fed probabilities

**Economic Indicators**

- [ ] CPI, PCE, PPI (headline and core)
- [ ] Employment data (NFP, unemployment, wages)
- [ ] GDP and GDP components
- [ ] ISM manufacturing and services
- [ ] Retail sales, consumer confidence
- [ ] Housing data

**Fiscal Data**

- [ ] Treasury issuance calendar and auction results
- [ ] Budget deficit/surplus data
- [ ] TGA (Treasury General Account) balance

## Cross-Asset & Market Microstructure

**Positioning & Flows**

- [ ] CFTC Commitment of Traders reports
- [ ] Primary dealer positioning (FRBNY data)
- [ ] Treasury custody holdings (foreign official holdings)
- [ ] Mutual fund and ETF flows

**Correlations & Spreads**

- [ ] Equity indices (SPX, NDX) for risk-on/risk-off
- [ ] FX rates (DXY, major pairs)
- [ ] Commodities (oil, gold)
- [ ] Credit spreads (IG, HY CDX indices)
- [ ] Swap spreads and basis

**Liquidity Metrics**

- [ ] Bid-ask spreads across products
- [ ] Trade volumes and market depth
- [ ] Repo rates (general collateral,specials)
- [ ] Fails data

## Technical & Derived Data

**Calculated Metrics**

- [ ] DV01, duration, convexity for all instruments
- [ ] Carry and roll-down
- [ ] Butterfly spreads, curve steepness
- [ ] Real yields and breakevens
- [ ] Forward rate expectations
- [ ] Vol-adjusted spread metrics (Sharpe ratios, z-scores)

**Historical Analysis**

- [ ] Time series with sufficient history (10+ years ideally)
- [ ] Regime classifications
- [ ] Volatility estimates (realized, GARCH, etc.)

## Data Providers to Consider

- [ ] **Bloomberg** (most comprehensive, expensive)
- [ ] **Refinitiv/LSEG** (broad coverage)
- [ ] **CME/CBOT** (futures data directly)
- [ ] **FRED** (Federal Reserve economic data - [ ] free)
- [ ] **Treasury Direct** (auction data - [ ] free)
- [ ] **ICE** (swap data)
- [ ] **Quandl/Nasdaq Data Link** (aggregated sources)

## Implementation Notes

For your Python library, you'll want to:

- [ ] Build a robust data pipeline with caching/storage (consider TimescaleDB or Arctic)
- [ ] Implement data validation and cleaning
- [ ] Create interpolation methods for curves
- [ ] Build pricing engines for derivatives
- [ ] Design a flexible factor model framework for macro signals
- [ ] Implement portfolio construction and risk management tools
- [ ] Consider real-time vs end-of-day data requirements
