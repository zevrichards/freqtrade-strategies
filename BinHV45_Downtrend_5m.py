# BinHV45_Downtrend_5m.py - BACKTEST ONLY
# Tests: downtrend filter ONLY (no RSI divergence)
# Parameters: -3% stoploss, +2% ROI
# Purpose: isolate how much the 30m downtrend filter contributes

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import pandas_ta as pta
import pandas as pd


class BinHV45_Downtrend_5m(IStrategy):

    minimal_roi = {"0": 0.02}
    stoploss = -0.03
    timeframe = "5m"
    startup_candle_count: int = 250

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 12},
            {"method": "StoplossGuard", "lookback_period_candles": 24,
             "trade_limit": 2, "stop_duration_candles": 48, "only_per_pair": True}
        ]

    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_50"]  = pta.ema(dataframe["close"], length=50)
        dataframe["ema_200"] = pta.ema(dataframe["close"], length=200)
        dataframe["rsi"]     = pta.rsi(dataframe["close"], length=14)
        adx = pta.adx(dataframe["high"], dataframe["low"], dataframe["close"], length=14)
        if adx is not None and "ADX_14" in adx.columns:
            dataframe["adx"] = adx["ADX_14"]
        else:
            dataframe["adx"] = 0
        dataframe["is_bear"] = (
            (dataframe["close"] < dataframe["ema_200"]) &
            (dataframe["ema_50"] < dataframe["ema_200"]) &
            (dataframe["rsi"] < 50) &
            (dataframe["adx"] > 20)
        ).astype(int)
        return dataframe

    @informative('30m')
    def populate_indicators_30m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_20"] = pta.ema(dataframe["close"], length=20)
        dataframe["ema_50"] = pta.ema(dataframe["close"], length=50)
        dataframe["rsi"]    = pta.rsi(dataframe["close"], length=14)
        dataframe["in_downtrend"] = (
            (dataframe["close"] < dataframe["ema_20"]) &
            (dataframe["ema_20"] < dataframe["ema_50"]) &
            (dataframe["rsi"] < 45)
        ).astype(int)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bb40 = pta.bbands(dataframe["close"], length=40, std=2.0)
        if bb40 is not None:
            dataframe["bb40_lower"] = bb40["BBL_40_2.0"]
            dataframe["bb40_mid"]   = bb40["BBM_40_2.0"]
            dataframe["bb40_delta"] = (bb40["BBM_40_2.0"] - bb40["BBL_40_2.0"]).abs()
        dataframe["closedelta"]       = (dataframe["close"] - dataframe["close"].shift(1)).abs()
        dataframe["tail"]             = (dataframe["close"] - dataframe["low"]).abs()
        dataframe["volume_mean_slow"] = dataframe["volume"].rolling(window=30).mean()
        dataframe["rsi"]              = pta.rsi(dataframe["close"], length=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        not_bear = dataframe["1h_is_bear"] == 0 if "1h_is_bear" in dataframe.columns \
                   else pd.Series(True, index=dataframe.index)
        not_downtrend = dataframe["30m_in_downtrend"] == 0 if "30m_in_downtrend" in dataframe.columns \
                        else pd.Series(True, index=dataframe.index)

        # NO RSI divergence check here — downtrend filter only
        dataframe.loc[
            (
                not_bear &
                not_downtrend &
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

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        return dataframe
