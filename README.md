# freqtrade-strategies

Custom trading strategies for [Freqtrade](https://github.com/freqtrade/freqtrade), built and tested on Bybit spot markets.

## Setup

All strategies expect Freqtrade running with:
- **Exchange:** Bybit (spot)
- **Pairs:** 18–40 major USDT pairs
- **Stake:** unlimited (auto-sized per trade)

---

## Active Strategy

### `BinHV45_Regime_5m.py` ⭐ CURRENT LIVE BOT
**Best overall. +13.83% in pure bear market (Dec 2025–Jun 2026), 95.3% win rate.**

- **Timeframe:** 5m
- Based on the proven BinHV45 community algorithm
- Adds a 1h regime informer — blocks entries only during confirmed BEAR conditions
- Entry: sharp capitulation drop below 40-period Bollinger Band lower with volume confirmation
- Exit: 1.25% ROI target
- Stoploss: -5%
- Backtest (Dec 2025–Jun 2026, 40 pairs, bear market): +13.83%, 192 trades, 95.3% win rate, 2.32% max drawdown

---

## Supporting Strategies

### `EMAcross_4h.py`
- **Timeframe:** 4h
- Trend following: 20 EMA crosses above 50 EMA with RSI confirmation
- BULL regime only
- Backtest: +8.4% bull, -0.7% bear, 3.95% max drawdown

### `DCAStrategy_4h.py`
- **Timeframe:** 4h
- Systematic accumulation on pullbacks in BULL regime only
- Safety orders at -3%, -6%, -10% with 4x stake cap
- Backtest: +25.9% bull, 0 trades bear

### `MeanReversion_4h.py`
- **Timeframe:** 4h
- Bollinger Band oversold bounces in RANGING regime only
- Backtest: -5.3% bear (best suited to genuine sideways markets)

### `BreakoutDetector_1d.py`
- **Timeframe:** 1d
- Market analysis tool — not a trading strategy
- Signals bear-to-bull transitions when 5 of 7 conditions align
- Use to time activation of DCAStrategy_4h

---

## Shared Module

### `regime_filter.py`
Imported by all strategies. Classifies each candle as BULL, EARLY_BULL, BEAR, RANGING, or UNKNOWN.

---

## Backtesting

```bash
# BinHV45_Regime_5m — bear period
docker compose run --rm freqtrade backtesting \
  --config user_data/config_backtest_5m.json \
  --strategy BinHV45_Regime_5m \
  --timerange 20251225-20260601 -i 5m

# 4h strategies — bull period
docker compose run --rm freqtrade backtesting \
  --config user_data/config_backtest.json \
  --strategy-list EMAcross_4h DCAStrategy_4h MeanReversion_4h \
  --timerange 20241001-20251001 -i 4h
```

## Disclaimer
For educational and research purposes. Not financial advice. Always run dry-run before live trading.
