# CHANGELOG.md
# Tracks every change made to strategies, config, and infrastructure.
# Format: newest first. Each entry includes what changed, why, and the result.

---

## [2026-06-27] BinHV45_Regime_5m v3 — CURRENT

### What changed
- **Removed:** RSI bullish divergence entry filter
- **Kept:** 30m pair-level downtrend filter
- **Changed:** Stop loss -5% → -3%
- **Changed:** ROI target +1.25% → +2%
- **Changed:** Global stoploss in config.json updated to -0.03

### Why
Isolation backtests proved RSI divergence blocked 99% of valid entries (3 trades
vs 314 with downtrend filter only). RSI divergence is valid on 4h+ timeframes
but too rare on 5m candles to be useful as a gate.

The -3%/+2% change drops break-even win rate from 80% to 60%, giving much more
margin. Backtest confirmed the math works even with a lower win rate.

### Backtest result
- Period: Dec 2025 – Jun 2026 (pure bear market), 40 pairs
- Total return: +22.53% (+$1,126 on 5,000 USDT)
- Trades: 314 | Win rate: 74.5% | Max drawdown: $242 (4.13%)

### Files changed
- `BinHV45_Regime_5m.py` — strategy rewrite
- `config.json` — stoploss updated to -0.03
- `README.md` — active strategy section updated
- `INTELLIGENCE_REPORT.md` — lessons 11, 12, 13 added

### Test strategies added (backtest only, not live)
- `BinHV45_Downtrend_5m.py` — downtrend filter only, -3%/+2%
- `BinHV45_RSIDivergence_5m.py` — RSI divergence only, -3%/+2%
- `BinHV45_Regime_5m_test.py` — both filters, -3%/+2%

---

## [2026-06-27] Config — Pair Filters Adjusted

### What changed
- `min_value`: $10M → $5M → $1M (stepped down to find viable pair count)
- `RangeStabilityFilter max_rate_of_change`: 0.35 → 0.70
- `AgeFilter min_days_listed`: 10 → 30

### Why
$10M and 35% max were too aggressive for current bear market volatility.
Legitimate coins (AAVE +39%, WLD +59%) were excluded. Pair count collapsed
from 40 to 5, causing zero trades for 16 hours.

### Result
33 active pairs at $1M threshold with 70% max change.

---

## [2026-06-27] Blacklist — `.*X/USDT` Wildcard Removed

### What changed
- Removed `.*X/USDT` wildcard
- Replaced with explicit named coins: NVDAX, NAVX, SPX, CRCLX, COINX, SPCXX,
  MPLX, MBX, MBOX, HTX, JUP, ZRX, WEMIX, APEX, ICX, GMX, SNX, DYDX
- Added: CC, PIEVERSE, ICNT, ASTER, LIT

### Why
`.*X/USDT` matched any ticker containing X — eliminated XRP, AAVE, LINK.
Pair count dropped from 40 to 5. Zero trades for 16 hours.

### Rule
Never use broad regex wildcards against ticker body. Safe patterns only:
`.*UP/USDT`, `.*DOWN/USDT`, `.*BULL/USDT`, `.*BEAR/USDT`

---

## [2026-06-26] BinHV45_Regime_5m v2

### What changed
- **Added:** 30m informer for pair-level downtrend detection
- **Added:** RSI bullish divergence check on 5m (later removed in v3)
- **Added:** CooldownPeriod — 12 candle block after stop loss
- **Added:** StoplossGuard — 2 losses in 24 candles → 4h block
- **Added to blacklist:** POPCAT, PUMP, IP, HOODX, XPL
- **Added to blacklist:** `.*X/USDT` wildcard (later removed — too broad)

### Why
Live v1 produced 5 stop losses nearly cancelling 21 ROI wins.
POPCAT entered 5 times. PUMP and IP were low-quality coins.

### Live v1 result (26 trades, June 23–26)
- Net P&L: +$13.73 | Win rate: 80.8% (21 wins / 5 losses)
- ROI exits: +$144.52 | Stop losses: -$130.80
- Worst: POPCAT -$25.29 | Best: XPL +$20.22

---

## [2026-06-23] BinHV45_Regime_5m v1 — Initial Deployment

### What changed
- Replaced EMAcross_4h as active strategy
- Wallet reset to 5,000 USDT
- Switched from 18 pairs/4h to 40 pairs/5m
- max_open_trades raised from 5 to 10

### Why
EMAcross_4h produced 2 stop losses totalling -$105 in first live test.
BinHV45_Regime_5m backtest showed +13.83% vs -0.7% for EMAcross_4h.

### Backtest result (at deployment)
- Period: Dec 2025 – Jun 2026, 40 pairs
- Total return: +13.83% | Trades: 192 | Win rate: 95.3% | Max drawdown: 2.32%

---

## [2026-06-22] EMAcross_4h — First Live Deployment (replaced)

### What changed
- First ever live bot deployment
- 18 pairs, 4h candles, 5,000 USDT wallet

### Result
- 2 trades, both stop losses: SOL -$52.22, ETH -$52.82. Total: -$105 in ~16h
- Replaced by BinHV45_Regime_5m

---

## [2026-06-22] Infrastructure — Initial Setup

### What was set up
- Freqtrade in Docker on Windows PC (CSI-MSI)
- FreqUI at http://localhost:8090 (port 8090 — avoids Viser conflict on 8081)
- Cloudflare Tunnel: freqtrade.richersimulations.com → localhost:8090
- Discord webhook notifications (Telegram unavailable in T&T)
- GitHub: github.com/zevrichards/freqtrade-strategies
- Strategies built: EMAcross_4h, DCAStrategy_4h, MeanReversion_4h, BreakoutDetector_1d
- Shared module: regime_filter.py

### Config files
- `config.json` — live/dry-run (VolumePairList)
- `config_backtest.json` — 4h backtest (StaticPairList, 18 pairs)
- `config_backtest_5m.json` — 5m backtest (StaticPairList, 40 pairs)

---

## Version Summary

| File | Current Version | Last Updated |
|---|---|---|
| BinHV45_Regime_5m.py | **v3** | Jun 27, 2026 |
| EMAcross_4h.py | v2 | Jun 2026 |
| DCAStrategy_4h.py | v3 | Jun 2026 |
| MeanReversion_4h.py | v3 | Jun 2026 |
| BreakoutDetector_1d.py | v2 | Jun 2026 |
| regime_filter.py | v2 | Jun 2026 |

---

## [2026-06-29] Stop Loss Slippage Investigation + stoploss_on_exchange

### What happened
MANTA/USDT stop loss fired at -4.23% instead of the configured -3%.
Investigation revealed ALL 7 stop losses exceeded -3% (range: -4.0% to -6.2%).

### Root cause: candle-close stop loss checking
Freqtrade checks stop loss at candle CLOSE, not tick-by-tick.
On 5m candles, price can crash through the -3% level mid-candle.
By the time the candle closes, the loss is already deeper than the target.
This is called "gap slippage" — inherent to candle-based stops.

### Fix applied: stoploss_on_exchange
Added to config.json:
  "stoploss_on_exchange": true,
  "stoploss_on_exchange_interval": 60

This places a native stop-limit order directly on Bybit when a trade opens.
Bybit monitors it tick-by-tick and closes at exactly -3%.

NOTE: stoploss_on_exchange only works in LIVE trading, not dry-run.
Dry-run will still show slippage. Effect will be real when going live.

### MANTA blacklisted
MANTA/USDT added to blacklist after -4.23% stop loss (Jun 28).
Low-cap L2 token — prone to sharp gap moves on 5m.

### Current overall stats (29 closed trades)
- Net P&L: -$15.51
- Win rate: 75.9% (22 wins / 7 losses)
- ROI exits: 22 trades, +$154.74, avg +1.49%
- Stop losses: 7 trades, -$170.25, avg -5.09% (all exceeded -3% due to slippage)
- Break-even at current parameters (-3%/+2%): 60% win rate needed
- Current 75.9% is above break-even but stop slippage is pushing actual losses higher

