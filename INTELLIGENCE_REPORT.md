# INTELLIGENCE_REPORT.md
# Accumulated knowledge from live trading, backtesting, and strategy development.
# Updated as new patterns, mistakes, and fixes are discovered.
# This file is the institutional memory of this bot.

---

## SESSION 1 — June 2026
### Initial Setup & Backtesting

---

### LESSON 1: Timeframe Selection

**What we tried:** Started with 1h candles on 3 pairs.
**What happened:** EMAcross lost -15% in the same period the market lost -18%. Not enough signal quality.
**What we learned:**
- 1h on 3 pairs = too few signals, too much noise per signal
- 4h dramatically reduced whipsaw — max drawdown dropped from 18% to 1.8% on EMAcross
- 5m on 40 pairs is the correct setup for BinHV45-style strategies — volume of signals matters
- Higher timeframes reduce fee drag as a % of profit

**Rule established:** Match timeframe to strategy type.
- Trend following → 4h minimum
- Mean reversion / capitulation → 5m with many pairs (40+)
- Regime detection → always use a higher TF informer (1h or 4h)

---

### LESSON 2: Regime Filter Is Essential

**What we tried:** Running EMAcross without a regime filter.
**What happened:** -15.33% over 6 months. 50 exit-signal losses averaging -2.16% each.
**What we learned:** Without knowing whether we're in a bull, bear, or ranging market, trend-following strategies enter at the wrong time constantly.

**Fix implemented:** `regime_filter.py` — classifies each candle as BULL, EARLY_BULL, BEAR, RANGING, or UNKNOWN using:
- Price vs 200 EMA
- 50 EMA vs 200 EMA (golden/death cross)
- RSI direction
- ADX strength

**Result:** EMAcross went from -15% to -0.7% in bear market after adding regime filter. DCAStrategy correctly made 0 trades in bear (sat out entirely).

**Rule established:** All long strategies must gate entries on regime. Never trade long in confirmed BEAR.

---

### LESSON 3: Exit Signal Problems

**What we tried:** EMAcross with EMA re-cross as the exit signal.
**What happened:** 50 exit-signal losses. The strategy was exiting at -2.16% average on whipsaws.
**What we learned:** On 1h candles in choppy markets, EMA crossovers fire both ways constantly. The exit signal became the biggest loss source — worse than the stop-loss.

**Fix implemented:** `use_exit_signal = False` on EMAcross and MeanReversion. Let ROI and stop-loss handle all exits.

**Rule established:** For trend and mean-reversion strategies, exit signals should be disabled unless they are a strict, high-confidence condition (e.g. returning to the middle Bollinger Band). Default to ROI + stoploss only.

---

### LESSON 4: Community Strategy Misuse

**What we tried:** Running BinHV45 and CombinedBinHAndCluc on 4h candles with 3-5 pairs.
**What happened:** BinHV45 lost -0.4% bull, -13.9% bear. CombinedBinH lost -19% bull, -34% bear.
**What we learned:**
- BinHV45 is a 1m/5m scalper designed for 40-80 pairs. Running it on 4h = completely wrong environment.
- CombinedBinH specifies max 2 open trades. We ran it with 5. Violated its design constraints.
- Never transplant a strategy to a timeframe or pair count it wasn't designed for without rethinking all parameters.

**Rule established:** Before running any community strategy, read and understand:
1. Its designed timeframe
2. Its recommended pair count
3. Its max open trades setting
4. Its ROI target (determines if fees are sustainable)

---

### LESSON 5: DCA in Bear Markets Is a Capital Trap

**What we tried:** DCAStrategy with EARLY_BULL regime (looser condition).
**What happened:** -55.3% in bear market. The EARLY_BULL condition allowed entries on bear bounces that then continued lower. Safety orders multiplied losses.
**What we learned:** DCA averages down. In a sustained downtrend, every safety order adds to a losing position. The -25% stoploss was too wide — one bad trade wiped 55% of wallet because safety orders kept adding stake.

**Fixes implemented:**
1. Reverted to strict BULL-only regime (no EARLY_BULL for DCA)
2. Added 4x stake cap — max total position = 4x initial stake
3. Tightened stoploss to -15%

**Rule established:** DCA strategies must only operate in confirmed bull markets. The safety order multiplier means losses compound. Always cap total stake per trade.

---

### LESSON 6: Pair Quality Is Critical for 5m Strategies

**What we tried:** VolumePairList with 80 pairs, min_value = 0, AgeFilter = 10 days.
**What happened:** Low-cap coins like CRCLX, SPCXX, HOODX, PUMP, IP entered the list. These produced immediate stop losses.
**What we learned:**
- Raw volume can be artificial (wash trading)
- Newly listed coins (< 30 days) are unpredictable
- Coins with X suffix on Bybit are often tokenised stocks — different behaviour
- PUMP and similar names are red flags for manipulation

**Fixes implemented:**
- Reduced to 40 pairs
- AgeFilter raised to 30 days
- min_value raised to $10M daily USDT volume
- RangeStabilityFilter max tightened from 50% to 35%
- Explicit blacklist: POPCAT, PUMP, IP, HOODX, XPL, `.*X/USDT` wildcard

**Rule established:** For live trading, add any coin that produces a stop loss to the blacklist and investigate why before re-adding it.

---

### LESSON 7: Downtrend vs Capitulation — The Core 5m Problem

**What we tried:** BinHV45_Regime_5m v1 — only blocked confirmed BEAR on 1h.
**What happened:** POPCAT entered 5 times. Two stop losses on POPCAT alone (-$54). The 5m capitulation signal fired repeatedly on a coin in a sustained downtrend.
**What we learned:**
- A 5m "sharp drop" looks identical whether it's a capitulation bounce or a downtrend continuation
- The 1h regime filter checks the market broadly — it doesn't check the individual pair's short-term trend
- A coin can be in its own downtrend even when the broader market is RANGING or BULL
- After a stop loss, re-entering the same coin immediately is the biggest mistake possible

**Three-layer fix implemented in v2:**

**Layer 1 — 30m pair-level downtrend filter:**
Added 30m informer checking each pair individually.
Blocks entry if: close < EMA20 AND EMA20 < EMA50 AND RSI < 45 on 30m.
This catches "capitulation" signals that are actually pauses in a coin's own downtrend.

**Layer 2 — RSI bullish divergence:**
In a real capitulation: price makes new low, RSI does NOT.
In a downtrend: both price and RSI make new lows.
Now requires: close < close(3 candles ago) AND RSI > RSI(3 candles ago).
This is the most reliable 5m-level capitulation vs continuation distinguisher.

**Layer 3 — CooldownPeriod + StoplossGuard protections:**
- CooldownPeriod: 12 candle block on a pair after any stop loss (1 hour on 5m)
- StoplossGuard: 2 losses on same pair within 24 candles → 4-hour block
Directly prevents POPCAT-style repeated re-entry after losses.

**Rule established:** For 5m mean-reversion strategies, always add:
1. A higher TF informer checking the individual pair's short-term trend
2. RSI divergence confirmation
3. CooldownPeriod and StoplossGuard protections

---

## LIVE TRADING RESULTS — June 23-26, 2026

### Bot: BinHV45_Regime_5m v1
**Period:** June 23 – June 26, 2026
**Wallet:** 5,000 USDT (dry-run)
**Pairs:** 40 (VolumePairList)

| Metric | Value |
|---|---|
| Closed trades | 26 |
| Net P&L | +$13.73 |
| Win rate | 80.8% (21 wins / 5 losses) |
| ROI exits | 21 trades, +$144.52 total, avg +1.45% |
| Stop loss exits | 5 trades, -$130.80 total, avg -5.48% |
| Best pair | XPL/USDT (+$20.22, 3 trades, all ROI) |
| Worst pair | POPCAT/USDT (-$25.29, 5 trades, 2 stop losses) |

**Key finding:** ROI exits and stop losses nearly cancelled out. 5 losses almost wiped 21 wins. This is the fundamental tension of the strategy — many small wins vs few large losses.

**Backtest vs live comparison:**
- Backtest win rate: 95.3%
- Live win rate: 80.8%
- Gap caused by: low-quality coins in live pairlist, no downtrend filter, no RSI divergence requirement

**Coins that caused losses:**
- POPCAT — entered 5x, 2 stop losses. Coin was in sustained downtrend.
- PUMP — 1 stop loss. Suspicious coin name, likely manipulation.
- IP — 1 stop loss. Low quality, thin liquidity.
- GRASS — 3 entries, 1 stop loss. Acceptable but watch list.

---

## OPEN QUESTIONS / FUTURE INVESTIGATIONS

1. **Does the 30m downtrend filter over-filter?** — Need to backtest v2 to confirm signal count stays reasonable. If it blocks too many entries, loosen the RSI threshold from 45 to 40.

2. **Optimal cooldown duration?** — 12 candles = 1 hour. May need to increase to 24 (2 hours) if re-entries are still problematic on fast-moving coins.

3. **Should GRASS stay blacklisted?** — 1 loss from 3 entries is within acceptable range. Monitor another week before deciding.

4. **BreakoutDetector validation** — The detector has only been backtested on 2024-2026 data. It needs 2022-2023 bear-to-bull data to validate the core bear recovery logic. The two signals it fired were near the Sept 2025 ATH, not during a bear recovery.

5. **Hyperopt** — None of our strategies have been parameter-optimised. Running Hyperopt on BinHV45_Regime_5m's BB thresholds (0.007, 0.0175, 0.25) could meaningfully improve performance.

6. **MeanReversion_4h** — Never tested in a genuine ranging market. 2024-2026 data was either bull or bear. Need a sideways period to validate.

7. **VPS migration** — Bot is running on a home Windows PC. Needs move to Linux VPS for 24/7 reliability and live trading readiness.
