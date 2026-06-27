# BinHV45_Regime_5m.py - v2
#
# IMPROVEMENTS OVER v1:
#
# 1. DOWNTREND vs CAPITULATION FILTER (30m informer)
#    A 30m informer checks the individual pair's short-term trend.
#    If the pair itself is making lower lows on 30m, we skip entry —
#    that's a downtrend, not capitulation. Capitulation needs a ranging
#    or mild uptrend context before the sharp drop.
#    Specifically blocks entry when ALL of:
#      - 30m close < 30m EMA20 (below short-term average)
#      - 30m EMA20 < 30m EMA50 (short-term average falling)
#      - 30m RSI < 45 (momentum already weak — not oversold bounce setup)
#
# 2. RSI DIVERGENCE CHECK (5m)
#    In a real capitulation, price makes a new low but RSI doesn't.
#    In a downtrend continuation, both make new lows together.
#    We check that RSI at the entry candle is HIGHER than RSI 3 candles
#    ago even though price is lower — bullish divergence signal.
#
# 3. COOLDOWN AFTER STOP LOSS (handled via stoploss_on_exchange + protection)
#    Uses Freqtrade's built-in CooldownPeriod protection — after any stop
#    loss on a pair, that pair is blocked for 12 candles (1 hour on 5m).
#    This directly fixes the POPCAT re-entry problem.
#
# 4. EXPANDED BLACKLIST (in config.json)
#    POPCAT, PUMP, IP, HOODX, XPL added to blacklist after live analysis.

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import pandas_ta as pta
import pandas as pd


class BinHV45_Regime_5m_test(IStrategy):

    minimal_roi = {"0": 0.02}   # +2% ROI (was 1.25%)
    stoploss = -0.03            # -3% stop loss (was -5%)
    timeframe = "5m"
    startup_candle_count: int = 250

    # ------------------------------------------------------------------ #
    # PROTECTIONS — cooldown after stop loss                               #
    # ------------------------------------------------------------------ #
    @property
    def protections(self):
        return [
            {
                # Block re-entry on a pair for 12 candles (1h) after stop loss
                "method": "CooldownPeriod",
                "stop_duration_candles": 12
            },
            {
                # If 3 of the last 4 trades on any pair were losses, block for 4h
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 2,
                "stop_duration_candles": 48,
                "only_per_pair": True
            }
        ]

    # ------------------------------------------------------------------ #
    # 1h INFORMER — market regime (bear vs not-bear)                      #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # 30m INFORMER — pair-level downtrend detection                       #
    # ------------------------------------------------------------------ #
    @informative('30m')
    def populate_indicators_30m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_20"] = pta.ema(dataframe["close"], length=20)
        dataframe["ema_50"] = pta.ema(dataframe["close"], length=50)
        dataframe["rsi"]    = pta.rsi(dataframe["close"], length=14)

        # in_downtrend = 1 means the pair itself is in a short-term downtrend
        # This catches POPCAT-style situations where the coin keeps making
        # lower lows on the 30m even as 5m shows "capitulation" signals
        dataframe["in_downtrend"] = (
            (dataframe["close"] < dataframe["ema_20"]) &
            (dataframe["ema_20"] < dataframe["ema_50"]) &
            (dataframe["rsi"] < 45)
        ).astype(int)

        return dataframe

    # ------------------------------------------------------------------ #
    # 5m INDICATORS                                                        #
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

        # RSI for divergence check
        dataframe["rsi"] = pta.rsi(dataframe["close"], length=14)

        return dataframe

    # ------------------------------------------------------------------ #
    # ENTRY                                                                #
    # ------------------------------------------------------------------ #
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # 1h: not in confirmed bear market
        if "1h_is_bear" in dataframe.columns:
            not_bear = dataframe["1h_is_bear"] == 0
        else:
            not_bear = pd.Series(True, index=dataframe.index)

        # 30m: pair not in its own short-term downtrend
        if "30m_in_downtrend" in dataframe.columns:
            not_downtrend = dataframe["30m_in_downtrend"] == 0
        else:
            not_downtrend = pd.Series(True, index=dataframe.index)

        # RSI bullish divergence: price lower than 3 candles ago
        # but RSI higher than 3 candles ago — classic capitulation signal
        rsi_divergence = (
            (dataframe["close"] < dataframe["close"].shift(3)) &
            (dataframe["rsi"] > dataframe["rsi"].shift(3))
        )

        dataframe.loc[
            (
                not_bear &
                not_downtrend &
                rsi_divergence &
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
    # EXIT                                                                 #
    # ------------------------------------------------------------------ #
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        return dataframe
