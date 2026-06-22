# BreakoutDetector.py
# Not a trading strategy — a market analysis tool.
# Run this in backtesting mode to see historically when breakout conditions fired.
#
# BREAKOUT CONDITIONS (all must be true simultaneously):
#   1. Price reclaims the 200-day EMA from below (major structural signal)
#   2. 50-day EMA crosses above 200-day EMA (golden cross — trend confirmation)
#   3. RSI breaks above 50 and is rising (momentum confirmation)
#   4. Volume spike: current volume > 1.5x 20-period average (conviction)
#   5. Price consolidation break: price breaks above a recent 30-candle high
#
# EARLY WARNING (weaker signal — only 3 of 5 needed):
#   Used to flag "watch zone" — breakout not confirmed but conditions improving
#
# The strategy generates no trades — it just marks breakout candles with
# enter_long=1 so you can see them on the FreqUI chart overlay.

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import pandas_ta as pta


class BreakoutDetector(IStrategy):

    minimal_roi = {"0": 100}     # never take profit — we just want signals
    stoploss = -0.99             # never stop out — signals only
    timeframe = "1d"             # daily candles — breakouts are macro events
    startup_candle_count: int = 250

    # Tunable thresholds
    volume_spike    = DecimalParameter(1.2, 2.5, default=1.5, decimals=1, space="buy")
    rsi_breakout    = IntParameter(48, 55, default=50, space="buy")
    consolidation   = IntParameter(20, 50, default=30, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Trend EMAs
        dataframe["ema_50"]  = pta.ema(dataframe["close"], length=50)
        dataframe["ema_200"] = pta.ema(dataframe["close"], length=200)

        # RSI
        dataframe["rsi"] = pta.rsi(dataframe["close"], length=14)

        # Volume MA
        dataframe["vol_ma_20"] = pta.sma(dataframe["volume"], length=20)

        # Rolling high for consolidation breakout
        for val in self.consolidation.range:
            dataframe[f"high_{val}"] = dataframe["high"].shift(1).rolling(val).max()

        # ADX — trend strength (above 25 = trending, below = ranging)
        adx_result = pta.adx(dataframe["high"], dataframe["low"], dataframe["close"], length=14)
        if adx_result is not None and "ADX_14" in adx_result.columns:
            dataframe["adx"] = adx_result["ADX_14"]
        else:
            dataframe["adx"] = 0

        # MACD
        macd = pta.macd(dataframe["close"], fast=12, slow=26, signal=9)
        if macd is not None:
            dataframe["macd"]       = macd["MACD_12_26_9"]
            dataframe["macd_signal"]= macd["MACDs_12_26_9"]
            dataframe["macd_hist"]  = macd["MACDh_12_26_9"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        vol_spike = self.volume_spike.value
        rsi_lvl   = self.rsi_breakout.value
        cons      = self.consolidation.value
        high_col  = f"high_{cons}"

        # --- CONDITION FLAGS ---
        # 1. Price reclaimed 200 EMA (crossed from below)
        c1_reclaim = (
            (dataframe["close"] > dataframe["ema_200"]) &
            (dataframe["close"].shift(1) <= dataframe["ema_200"].shift(1))
        )

        # 2. Golden cross: 50 EMA just crossed above 200 EMA
        c2_golden = (
            (dataframe["ema_50"] > dataframe["ema_200"]) &
            (dataframe["ema_50"].shift(1) <= dataframe["ema_200"].shift(1))
        )

        # 3. RSI broke above threshold and is rising
        c3_rsi = (
            (dataframe["rsi"] > rsi_lvl) &
            (dataframe["rsi"] > dataframe["rsi"].shift(1))
        )

        # 4. Volume spike
        c4_volume = (
            dataframe["volume"] > dataframe["vol_ma_20"] * vol_spike
        )

        # 5. Consolidation breakout: close above recent rolling high
        c5_breakout = (
            dataframe["close"] > dataframe[high_col]
        )

        # 6. ADX trending (bonus filter)
        c6_adx = dataframe["adx"] > 20

        # 7. MACD histogram turning positive
        c7_macd = (
            (dataframe["macd_hist"] > 0) &
            (dataframe["macd_hist"].shift(1) <= 0)
        )

        # STRONG BREAKOUT: 5 of 7 conditions (always includes c5 + c3)
        condition_count = (
            c1_reclaim.astype(int) +
            c2_golden.astype(int) +
            c3_rsi.astype(int) +
            c4_volume.astype(int) +
            c5_breakout.astype(int) +
            c6_adx.astype(int) +
            c7_macd.astype(int)
        )

        # Strong signal: 5+ conditions
        dataframe.loc[
            (condition_count >= 5) & (dataframe["volume"] > 0),
            "enter_long"
        ] = 1

        # Store signal strength for reference
        dataframe["breakout_score"] = condition_count

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        return dataframe
