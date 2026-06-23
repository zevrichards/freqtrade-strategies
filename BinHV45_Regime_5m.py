# BinHV45_Regime.py - BinHV45 entry logic + 1h regime filter
#
# WHAT THIS ADDS TO BINHV45:
#   - 1h informer candles for regime detection
#   - Skips entries only in confirmed BEAR (price < 200 EMA + death cross + RSI < 50 + ADX > 20)
#   - Allows entries in BULL, EARLY_BULL, RANGING, and UNKNOWN
#   - All original BinHV45 entry conditions preserved exactly

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import pandas_ta as pta
import pandas as pd


class BinHV45_Regime_5m(IStrategy):

    minimal_roi = {"0": 0.0125}
    stoploss = -0.05
    timeframe = "5m"
    startup_candle_count: int = 250

    # ------------------------------------------------------------------ #
    # 1h INFORMER — compute regime indicators on higher timeframe          #
    # ------------------------------------------------------------------ #
    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA for regime
        dataframe["ema_50"]  = pta.ema(dataframe["close"], length=50)
        dataframe["ema_200"] = pta.ema(dataframe["close"], length=200)
        dataframe["rsi"]     = pta.rsi(dataframe["close"], length=14)

        adx = pta.adx(dataframe["high"], dataframe["low"], dataframe["close"], length=14)
        if adx is not None and "ADX_14" in adx.columns:
            dataframe["adx"] = adx["ADX_14"]
        else:
            dataframe["adx"] = 0

        # Compute bear flag directly — 1 = bear, 0 = not bear
        dataframe["is_bear"] = (
            (dataframe["close"] < dataframe["ema_200"]) &
            (dataframe["ema_50"] < dataframe["ema_200"]) &
            (dataframe["rsi"] < 50) &
            (dataframe["adx"] > 20)
        ).astype(int)

        return dataframe

    # ------------------------------------------------------------------ #
    # 5m INDICATORS — original BinHV45 logic                              #
    # ------------------------------------------------------------------ #
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bb40 = pta.bbands(dataframe["close"], length=40, std=2.0)
        if bb40 is not None:
            dataframe["bb40_lower"] = bb40["BBL_40_2.0"]
            dataframe["bb40_mid"]   = bb40["BBM_40_2.0"]
            dataframe["bb40_delta"] = (bb40["BBM_40_2.0"] - bb40["BBL_40_2.0"]).abs()

        dataframe["closedelta"]       = (dataframe["close"] - dataframe["close"].shift(1)).abs()
        dataframe["tail"]             = (dataframe["close"] - dataframe["low"]).abs()
        dataframe["volume_mean_slow"] = dataframe["volume"].rolling(window=30).mean()

        return dataframe

    # ------------------------------------------------------------------ #
    # ENTRY — BinHV45 conditions, blocked only when 1h is confirmed BEAR  #
    # ------------------------------------------------------------------ #
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # 1h informer column — 1 means confirmed bear, 0 means anything else
        # Column name after informative merge is '1h_is_bear'
        if "1h_is_bear" in dataframe.columns:
            not_bear = dataframe["1h_is_bear"] == 0
        else:
            not_bear = pd.Series(True, index=dataframe.index)

        dataframe.loc[
            (
                not_bear &
                (dataframe["bb40_delta"] > 0) &
                (dataframe["bb40_lower"].shift(1) > 0) &
                (dataframe["bb40_delta"] > dataframe["close"] * 0.007) &
                (dataframe["closedelta"] > dataframe["close"] * 0.0175) &
                (dataframe["tail"] < dataframe["bb40_delta"] * 0.25) &
                (dataframe["close"] < dataframe["bb40_lower"].shift(1)) &
                (dataframe["close"] <= dataframe["close"].shift(1)) &
                (dataframe["volume"] < dataframe["volume_mean_slow"].shift(1) * 20) &
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1

        return dataframe

    # ------------------------------------------------------------------ #
    # EXIT — let ROI handle it                                             #
    # ------------------------------------------------------------------ #
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        return dataframe
