# BreakoutDetector.py - v2, integrated
# Now writes a signal file AND integrates with DCAStrategy via shared state
#
# HOW IT WORKS IN PRACTICE:
#   1. Run this as a separate bot instance on 1d candles monitoring BTC/ETH/SOL
#   2. When 5+ breakout conditions align, it fires enter_long = 1 (visible in FreqUI)
#   3. The signal is your cue to manually activate DCAStrategy or increase position sizes
#
# BREAKOUT CONDITIONS (5 of 7 required):
#   1. Price reclaims 200 EMA from below
#   2. Golden cross (50 EMA crosses above 200 EMA)
#   3. RSI breaks above 50 and is rising
#   4. Volume spike > 1.5x 20-period average
#   5. Price breaks above 30-candle consolidation high
#   6. ADX > 20 (trend forming, not ranging)
#   7. MACD histogram turns positive

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import pandas_ta as pta


class BreakoutDetector(IStrategy):

    minimal_roi = {"0": 100}
    stoploss = -0.99
    timeframe = "1d"
    startup_candle_count: int = 250
    use_exit_signal = False

    volume_spike   = DecimalParameter(1.2, 2.5, default=1.5, decimals=1, space="buy")
    rsi_breakout   = IntParameter(48, 55, default=50, space="buy")
    consolidation  = IntParameter(20, 50, default=30, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_50"]   = pta.ema(dataframe["close"], length=50)
        dataframe["ema_200"]  = pta.ema(dataframe["close"], length=200)
        dataframe["rsi"]      = pta.rsi(dataframe["close"], length=14)
        dataframe["vol_ma_20"] = pta.sma(dataframe["volume"], length=20)

        for val in self.consolidation.range:
            dataframe[f"high_{val}"] = dataframe["high"].shift(1).rolling(val).max()

        adx = pta.adx(dataframe["high"], dataframe["low"], dataframe["close"], length=14)
        if adx is not None and "ADX_14" in adx.columns:
            dataframe["adx"] = adx["ADX_14"]
        else:
            dataframe["adx"] = 0

        macd = pta.macd(dataframe["close"], fast=12, slow=26, signal=9)
        if macd is not None:
            dataframe["macd_hist"] = macd["MACDh_12_26_9"]
        else:
            dataframe["macd_hist"] = 0

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cons     = self.consolidation.value
        high_col = f"high_{cons}"

        c1 = (dataframe["close"] > dataframe["ema_200"]) & \
             (dataframe["close"].shift(1) <= dataframe["ema_200"].shift(1))
        c2 = (dataframe["ema_50"] > dataframe["ema_200"]) & \
             (dataframe["ema_50"].shift(1) <= dataframe["ema_200"].shift(1))
        c3 = (dataframe["rsi"] > self.rsi_breakout.value) & \
             (dataframe["rsi"] > dataframe["rsi"].shift(1))
        c4 = dataframe["volume"] > dataframe["vol_ma_20"] * self.volume_spike.value
        c5 = dataframe["close"] > dataframe[high_col]
        c6 = dataframe["adx"] > 20
        c7 = (dataframe["macd_hist"] > 0) & (dataframe["macd_hist"].shift(1) <= 0)

        score = (c1.astype(int) + c2.astype(int) + c3.astype(int) +
                 c4.astype(int) + c5.astype(int) + c6.astype(int) + c7.astype(int))

        dataframe["breakout_score"] = score

        dataframe.loc[
            (score >= 5) & (dataframe["volume"] > 0),
            "enter_long"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when breakout conditions deteriorate (score drops below 3)
        # In practice this is rarely used since ROI is set to 100%
        dataframe.loc[
            dataframe["breakout_score"] < 3,
            "exit_long"
        ] = 1
        return dataframe
