# freqtrade-strategies

Custom trading strategies for [Freqtrade](https://github.com/freqtrade/freqtrade), built and tested on Bybit spot markets.

See [INTELLIGENCE_REPORT.md](./INTELLIGENCE_REPORT.md) for accumulated lessons, live trading results, and the reasoning behind every major decision.

---

## Active Strategy

### `BinHV45_Regime_5m.py` ⭐ CURRENT LIVE BOT
**Best overall performer. +22.53% in pure bear market backtest (314 trades). Currently dry-running.**

- **Timeframe:** 5m (with 1h and 30m informers)
- **Pairs:** Top 40 by USDT volume (quality-filtered, $1M+ daily volume, 30+ days listed)
- **Based on:** BinHV45 community algorithm
- **Entry:** Sharp capitulation drop below 40-period Bollinger Band lower
- **Exit:** +2% ROI target or -3% stop loss
- **Regime protection:** 1h informer blocks entries in confirmed BEAR market
- **Downtrend protection:** 30m informer blocks entries when the individual pair is in its own downtrend
- **Re-entry protection:** CooldownPeriod (12 candles) + StoplossGuard (2 losses in 24 candles → 4h block)

#### Version History

**v3 (current) — June 27, 2026**
- Removed RSI bullish divergence check — backtest isolation proved it blocked 99% of valid entries (3 trades vs 314 with downtrend filter only). RSI divergence works on 4h+ but not as a 5m gate.
- Tightened stop loss: -5% → -3% (break-even win rate drops from 80% to 60%)
- Raised ROI target: +1.25% → +2% (each win earns 60% more)
- **Backtest result:** +22.53% over 6 months pure bear market, 314 trades, 74.5% win rate, 4.13% max drawdown

**v2 — June 26, 2026**
- Added 30m pair-level downtrend filter — blocks entry if pair's own 30m chart shows lower lows
- Added RSI bullish divergence check — price lower than 3 candles ago, RSI higher (later removed in v3)
- Added CooldownPeriod protection — 12 candle block after any stop loss on a pair
- Added StoplossGuard protection — 2 losses on same pair in 24 candles triggers 4h block
- Expanded blacklist: POPCAT, PUMP, IP, HOODX, XPL
- Raised min_value to $10M, tightened RangeStabilityFilter to 35% (later relaxed in config)
- **Problem discovered:** RSI divergence + downtrend together blocked 99% of entries (3 trades in 6 months)

**v1 — June 23, 2026**
- Initial deployment with 1h regime filter only
- 40 pairs, VolumePairList
- Live result: +$13.73 on 26 trades, 80.8% win rate, 5 stop losses
- Problem: POPCAT entered 5 times (2 stop losses), PUMP and IP slipped through filters

---

## Supporting Strategies (not currently active)

### `EMAcross_4h.py`
**Purpose:** Trend following in confirmed bull markets.

- **Timeframe:** 4h
- **Entry:** 20 EMA crosses above 50 EMA + RSI > 50, BULL regime only
- **Exit:** ROI (4%→3%→2%→1%) or -5% stop loss. Exit signal disabled.
- **Backtest:** +8.4% bull (Oct24–Oct25), -0.7% bear (Oct25–Jun26), 3.95% max drawdown

**Version History**

**v2 (current) — June 2026**
- Disabled exit signal (`use_exit_signal = False`) — EMA re-cross exit was causing 50 whipsaw losses averaging -2.16% each
- Added regime filter — BULL only
- Switched to 4h from 1h — max drawdown dropped from 18% to 1.8%

**v1 — June 2026**
- 1h timeframe, exit signal enabled
- Result: -15.33% — exit signal was the primary loss source

---

### `DCAStrategy_4h.py`
**Purpose:** Systematic accumulation on dips during confirmed bull markets.

- **Timeframe:** 4h
- **Entry:** RSI < 50 + price below EMA20, BULL regime only
- **Safety orders:** Buy more at -3%, -6%, -10% from entry (1.5x size multiplier)
- **Stake cap:** Max 4x initial stake per trade — prevents runaway losses
- **Exit:** 3% ROI or -15% stop loss
- **Backtest:** +25.9% bull, 0 trades bear (correctly sat out), 98% win rate

**Version History**

**v3 (current) — June 2026**
- Stake cap added at 4x initial (prevents wallet wipeout)
- Stoploss tightened from -25% to -15%
- Regime reverted to strict BULL only (removed EARLY_BULL)
- **Reason:** EARLY_BULL caused -55.3% bear result — safety orders multiplied losses on failed recoveries

**v2 — June 2026**
- EARLY_BULL added to catch start of bull runs earlier
- Result: -55.3% in bear — catastrophic. EARLY_BULL let entries on bear bounces that kept falling

**v1 — June 2026**
- BULL-only, no stake cap, -25% stoploss
- 0 trades in test period — BULL conditions never fully triggered

---

### `MeanReversion_4h.py`
**Purpose:** Oversold bounce trades in ranging (sideways) markets.

- **Timeframe:** 4h
- **Entry:** Price touches lower Bollinger Band (20-period) + RSI < 32, RANGING regime only
- **Regime gate:** ADX must be 12–25 (not dead, not trending) + price within 15% of 200 EMA
- **Exit:** ROI only, no exit signal
- **Backtest:** -5.3% bear. Has not been tested in a genuine ranging market yet.
- **Status:** Parked pending sideways market conditions

**Version History**

**v3 (current) — June 2026**
- RANGING-only (removed BULL from allowed regimes)
- Added ADX floor/ceiling (12–25) to enforce genuine sideways condition
- Added 15% price proximity to 200 EMA guard
- Exit signal disabled
- **Reason:** BinHV45-inspired v2 rewrite made bull performance worse (-27%). Reverted to tighter RANGING-only approach.

**v2 — June 2026**
- Rewrote using BinHV45's entry logic (bbdelta + closedelta + tail checks)
- Result: -27.9% bull, -8.0% bear. Worse than v1 in bull.

**v1 — June 2026**
- Basic BB + RSI, RANGING + BULL allowed
- Result: -34.94% over full period (slow bleeds in "ranging" were actually bear conditions)

---

### `BreakoutDetector_1d.py`
**Purpose:** Market analysis tool — NOT a trading strategy. Signals bear-to-bull transitions.

- **Timeframe:** 1d
- **Signal fires when 5 of 7 conditions align:**
  1. Price reclaims 200 EMA from below
  2. Golden cross (50 EMA crosses above 200 EMA)
  3. RSI breaks above 50 and is rising
  4. Volume spike > 1.5x 20-period average
  5. Price breaks above 30-candle consolidation high
  6. ADX > 20 (trend forming)
  7. MACD histogram turns positive
- **Backtest:** Fired twice in 16 months of data (both near Sept 2025 ATH)
- **Known limitation:** Not tested against 2022–2023 bear-to-bull data. The two signals it fired were at a market top, not a recovery.
- **Intended use:** When this fires, manually activate DCAStrategy_4h

---

## Shared Module

### `regime_filter.py`
Imported by all 4h strategies. Classifies each candle as BULL, EARLY_BULL, BEAR, RANGING, or UNKNOWN.

**BULL:** Price > 200 EMA + RSI > 50 + ADX > 20
**EARLY_BULL:** Price just crossed above 200 EMA with RSI rising (within last 5 candles)
**BEAR:** Price < 200 EMA + death cross + RSI < 50 + ADX > 20 (all four required)
**RANGING:** ADX < 20 OR price within 3% of 200 EMA
**UNKNOWN:** Insufficient warmup data

*Note: BinHV45_Regime_5m does NOT use this module. It computes its regime check inline in the 1h informer.*

---

## Pair Quality Filters (live config)

| Filter | Setting | Purpose |
|---|---|---|
| VolumePairList | Top 40, min $1M daily USDT | Only established liquid coins |
| AgeFilter | 30+ days listed | Exclude new/unknown tokens |
| RangeStabilityFilter | 1%–70% change over 10 days | Exclude dead coins and extreme pumps |
| PrecisionFilter | Auto | Exclude bad tick sizes |
| PriceFilter | Min 1% move | Exclude dust coins |
| SpreadFilter | Max 0.5% spread | Exclude illiquid pairs |

**Blacklist includes:** Stablecoins, wrapped tokens, leveraged tokens, POPCAT, PUMP, IP, HOODX, XPL, `.*X/USDT` wildcard (tokenised stocks)

---

## Backtesting

```bash
# BinHV45_Regime_5m — current live strategy (requires 5m, 30m, 1h data)
docker compose run --rm freqtrade backtesting \
  --config user_data/config_backtest_5m.json \
  --strategy BinHV45_Regime_5m \
  --timerange 20251225-20260620 -i 5m

# Compare all 5m variants side by side
docker compose run --rm freqtrade backtesting \
  --config user_data/config_backtest_5m.json \
  --strategy-list BinHV45 BinHV45_Regime_5m BinHV45_Downtrend_5m BinHV45_RSIDivergence_5m \
  --timerange 20251225-20260620 -i 5m

# 4h strategies — bull and bear periods
docker compose run --rm freqtrade backtesting \
  --config user_data/config_backtest.json \
  --strategy-list EMAcross_4h DCAStrategy_4h MeanReversion_4h \
  --timerange 20241001-20251001 -i 4h
```

**Data download (run before backtesting):**
```bash
# 5m strategies need 5m, 30m, and 1h data
docker compose run --rm freqtrade download-data \
  --config user_data/config_backtest_5m.json \
  --exchange bybit --days 180 -t 5m 30m 1h

# 4h strategies need 4h data
docker compose run --rm freqtrade download-data \
  --config user_data/config_backtest.json \
  --exchange bybit --days 730 -t 4h --prepend
```

**Configs:**
- `config_backtest_5m.json` — 40 pairs, StaticPairList, no global stoploss override
- `config_backtest.json` — 18 pairs, StaticPairList, 4h strategies

---

## Collaboration

Clone: `git clone https://github.com/zevrichards/freqtrade-strategies`

**Naming convention:**
- Files: `StrategyName_TIMEFRAME.py`
- Class: `class StrategyName_TIMEFRAME(IStrategy):`
- Suffixes: `_5m` `_15m` `_1h` `_4h` `_1d`

**Before pushing any strategy:**
1. Backtest over at least one bull AND one bear period
2. Check win rate, drawdown, and Sharpe ratio
3. Verify the exit reason breakdown — stop losses should not dominate
4. Document the version and changes in this README

---

## Disclaimer
For educational and research purposes. Not financial advice. Always validate in dry-run before live trading.
