# freqtrade-strategies

Custom trading strategies for [Freqtrade](https://github.com/freqtrade/freqtrade), built and tested on Bybit spot markets.

## Setup

All strategies expect Freqtrade running with:
- **Timeframe:** 4h
- **Exchange:** Bybit (spot)
- **Pairs:** 18 major USDT pairs via VolumePairList
- **Stake:** unlimited (auto-sized per trade)

## Strategies

### `EMAcross.py` — Trend Following
**Best overall. Profitable in both bull and bear markets.**

- Enters when the 20 EMA crosses above the 50 EMA with RSI confirmation
- Regime-gated: only trades in confirmed BULL market conditions
- Exits via ROI targets (4%→3%→2%→1%) or 5% stoploss
- Backtest: +8.4% bull (Oct24–Oct25), -0.7% bear (Oct25–Jun26), max drawdown ~4%

### `DCAStrategy.py` — Bull Market Accumulator
**Best bull market strategy. Sits out entirely in bear markets.**

- Enters on pullbacks (RSI < 50, price below EMA20) in confirmed BULL regime
- Adds to position at -3%, -6%, -10% drops (safety orders)
- Stake capped at 4x initial to limit max exposure
- Backtest: +25.9% bull, 0 trades bear, 98% win rate

### `MeanReversion.py` — Ranging Market Strategy
**Designed for sideways markets. Parks itself in trending conditions.**

- Enters when price touches lower Bollinger Band (20-period, 2std) with RSI oversold
- Regime-gated: only trades in RANGING conditions (ADX 12–25, price within 15% of 200 EMA)
- Exits via ROI or 5% stoploss (no exit signal — avoids whipsaw)
- Backtest: -5.3% bear, needs clean ranging period to validate properly

### `BreakoutDetector.py` — Bear-to-Bull Transition Signal
**Not a trading strategy — a market analysis tool.**

- Runs on 1d candles, generates signals when 5+ of 7 breakout conditions align
- Conditions: 200 EMA reclaim, golden cross, RSI > 50, volume spike, consolidation breakout, ADX trending, MACD turning positive
- Use to time activation of DCAStrategy at the start of a bull run

## Shared Module

### `regime_filter.py`
Imported by all strategies. Classifies each candle as BULL, EARLY_BULL, BEAR, RANGING, or UNKNOWN based on:
- Price vs 200 EMA
- 50/200 EMA relationship
- RSI direction
- ADX strength

## Backtesting

```bash
# Bull period
docker compose run --rm freqtrade backtesting \
  --config user_data/config_backtest.json \
  --strategy-list EMAcross DCAStrategy MeanReversion \
  --timerange 20241001-20251001 -i 4h

# Bear period
docker compose run --rm freqtrade backtesting \
  --config user_data/config_backtest.json \
  --strategy-list EMAcross DCAStrategy MeanReversion \
  --timerange 20251001-20260601 -i 4h
```

## Notes

- All strategies import `regime_filter.py` — keep it in the same folder
- `config_backtest.json` uses StaticPairList (required for backtesting)
- `config.json` uses VolumePairList (for live/dry-run)
- Never run DCAStrategy without the regime filter — it will average down into bear markets indefinitely

## Disclaimer

For educational and research purposes. Not financial advice. Always run dry-run before live trading.
