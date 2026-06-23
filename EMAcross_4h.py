# EMAcross.py - Trend Following Strategy (exit signal fix)
#
# KEY FIX from v1:
#   Disabled exit_signal — the EMA re-cross exit was causing 22 loss exits
#   averaging -2.41% each, totalling -$531. ROI and stoploss are cleaner exits
#   for a trend-following strategy. We let winning trades run to ROI targets
#   and losing trades hit the hard stop.

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import pandas_ta as pta
from regime_filter import add_regime_indicators, get_regime, BULL


class EMAcross_4h(IStrategy):

    minimal_roi = {"0": 0.04, "60": 0.03, "120": 0.02, "240": 0.01}
    stoploss = -0.05
    timeframe = "4h"
    trailing_stop = False
    use_exit_signal = False   # disable — let ROI and stoploss do the work
    startup_candle_count: int = 210

    fast_period = IntParameter(10, 30, default=20, space="buy")
    slow_period = IntParameter(30, 80, default=50, space="buy")
    rsi_buy     = IntParameter(45, 60, default=50, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = add_regime_indicators(dataframe)
        for val in self.fast_period.range:
            dataframe[f"ema_fast_{val}"] = pta.ema(dataframe["close"], length=val)
        for val in self.slow_period.range:
            dataframe[f"ema_slow_{val}"] = pta.ema(dataframe["close"], length=val)
        dataframe["rsi"] = pta.rsi(dataframe["close"], length=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        fast   = f"ema_fast_{self.fast_period.value}"
        slow   = f"ema_slow_{self.slow_period.value}"
        regime = get_regime(dataframe)

        dataframe.loc[
            (
                (regime == BULL) &
                (dataframe[fast] > dataframe[slow]) &
                (dataframe[fast].shift(1) <= dataframe[slow].shift(1)) &
                (dataframe["rsi"] > self.rsi_buy.value) &
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        return dataframe
