# MeanReversion.py - BEST VERSION
# Bear: -5.3%, 7.77% drawdown (Oct 2025 - Jun 2026, 18 pairs, 4h)
# Bull: parked — no profitable bull version found yet
#
# KEY DECISIONS:
#   - RANGING-only regime — confirmed that BULL entries cause bull losses
#   - ADX floor/ceiling enforces genuine sideways condition (not trending)
#   - Price within 15% of 200 EMA — avoids structural breakdowns
#   - use_exit_signal = False — ROI and stoploss only, exit signal was a major loss source
#   - Stoploss -5% — tight, because if it's not bouncing quickly it's not ranging
#   - 4h timeframe — one candle = 4 hours, enough time for a real oversold bounce

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
import pandas_ta as pta
from regime_filter import add_regime_indicators, get_regime, RANGING


class MeanReversion(IStrategy):

    minimal_roi = {"0": 0.03, "60": 0.02, "180": 0.01, "360": 0.005}
    stoploss = -0.05
    timeframe = "4h"
    trailing_stop = False
    use_exit_signal = False
    startup_candle_count: int = 210

    bb_window     = IntParameter(15, 30, default=20, space="buy")
    bb_std        = DecimalParameter(1.5, 2.5, default=2.0, decimals=1, space="buy")
    rsi_oversold  = IntParameter(25, 40, default=32, space="buy")
    adx_min       = IntParameter(10, 20, default=12, space="buy")
    adx_max       = IntParameter(20, 30, default=25, space="buy")
    ema_proximity = DecimalParameter(0.05, 0.20, default=0.15, decimals=2, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = add_regime_indicators(dataframe)
        for window in self.bb_window.range:
            for std in self.bb_std.range:
                bb = pta.bbands(dataframe["close"], length=window, std=float(std))
                if bb is not None:
                    dataframe[f"bb_lower_{window}_{std}"] = bb[f"BBL_{window}_{float(std)}"]
                    dataframe[f"bb_mid_{window}_{std}"]   = bb[f"BBM_{window}_{float(std)}"]
        dataframe["rsi"]       = pta.rsi(dataframe["close"], length=14)
        dataframe["volume_ma"] = pta.sma(dataframe["volume"], length=20)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        w, std = self.bb_window.value, self.bb_std.value
        lower  = f"bb_lower_{w}_{std}"
        regime = get_regime(dataframe)

        near_ema   = dataframe["regime_price_vs_200"].abs() < (self.ema_proximity.value * 100)
        adx_ranging = (
            (dataframe["regime_adx"] > self.adx_min.value) &
            (dataframe["regime_adx"] < self.adx_max.value)
        )

        dataframe.loc[
            (
                (regime == RANGING) &
                near_ema &
                adx_ranging &
                (dataframe["close"] <= dataframe[lower]) &
                (dataframe["rsi"] < self.rsi_oversold.value) &
                (dataframe["volume"] > dataframe["volume_ma"]) &
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        return dataframe
