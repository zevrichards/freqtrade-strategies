# regime_filter.py - Shared market regime detection module (v2)
#
# CHANGES FROM v1:
#   - BULL now uses a tiered approach:
#       STRONG_BULL: all 4 original conditions (golden cross confirmed)
#       BULL: relaxed — price above 200 EMA + RSI > 50 + ADX > 20
#             (no golden cross required — catches earlier in the move)
#   - Added EARLY_BULL signal for DCA entry — price just reclaimed 200 EMA
#     with RSI turning upward even if golden cross hasn't formed yet
#   - BEAR tightened: requires all 4 conditions to avoid false negatives
#   - RANGING unchanged

import pandas as pd
from pandas import DataFrame
import pandas_ta as pta

BULL        = "bull"
EARLY_BULL  = "early_bull"
BEAR        = "bear"
RANGING     = "ranging"
UNKNOWN     = "unknown"


def add_regime_indicators(dataframe: DataFrame) -> DataFrame:
    dataframe["regime_ema_50"]  = pta.ema(dataframe["close"], length=50)
    dataframe["regime_ema_200"] = pta.ema(dataframe["close"], length=200)
    dataframe["regime_rsi"]     = pta.rsi(dataframe["close"], length=14)

    adx = pta.adx(dataframe["high"], dataframe["low"], dataframe["close"], length=14)
    if adx is not None and "ADX_14" in adx.columns:
        dataframe["regime_adx"] = adx["ADX_14"]
    else:
        dataframe["regime_adx"] = 0

    atr = pta.atr(dataframe["high"], dataframe["low"], dataframe["close"], length=20)
    if atr is not None:
        dataframe["regime_atr_pct"] = atr / dataframe["close"] * 100
    else:
        dataframe["regime_atr_pct"] = 0

    dataframe["regime_price_vs_200"] = (
        (dataframe["close"] - dataframe["regime_ema_200"])
        / dataframe["regime_ema_200"] * 100
    )

    # RSI direction (rising vs falling)
    dataframe["regime_rsi_rising"] = (
        dataframe["regime_rsi"] > dataframe["regime_rsi"].shift(3)
    )

    return dataframe


def get_regime(dataframe: DataFrame) -> pd.Series:
    """
    Returns a Series of regime labels per candle.

    BULL:       Price > 200 EMA + RSI > 50 + ADX > 20
                (no golden cross needed — catches bull moves earlier)
    EARLY_BULL: Price just crossed above 200 EMA with RSI rising
                (useful for DCA entry timing at start of recovery)
    BEAR:       Full confirmation — price < 200 EMA + death cross
                + RSI < 50 + ADX > 20
    RANGING:    ADX < 20 (no trend) OR price within 3% of 200 EMA
    UNKNOWN:    Insufficient warmup data
    """
    required = ["regime_ema_50", "regime_ema_200", "regime_rsi", "regime_adx"]
    for col in required:
        if col not in dataframe.columns:
            return pd.Series(UNKNOWN, index=dataframe.index)

    # BULL: price above 200 EMA + RSI showing momentum + ADX confirming trend
    bull_conditions = (
        (dataframe["close"] > dataframe["regime_ema_200"]) &
        (dataframe["regime_rsi"] > 50) &
        (dataframe["regime_adx"] > 20)
    )

    # EARLY_BULL: price just reclaimed 200 EMA within last 5 candles + RSI rising
    reclaimed_200 = (
        (dataframe["close"] > dataframe["regime_ema_200"]) &
        (dataframe["close"].shift(5) <= dataframe["regime_ema_200"].shift(5))
    )
    early_bull_conditions = (
        reclaimed_200 &
        dataframe["regime_rsi_rising"] &
        (dataframe["regime_rsi"] > 45)
    )

    # BEAR: full confirmation required — price below, death cross, RSI weak, trending
    bear_conditions = (
        (dataframe["close"] < dataframe["regime_ema_200"]) &
        (dataframe["regime_ema_50"] < dataframe["regime_ema_200"]) &
        (dataframe["regime_rsi"] < 50) &
        (dataframe["regime_adx"] > 20)
    )

    # RANGING: no trend direction
    ranging_conditions = (
        (dataframe["regime_adx"] < 20) |
        (dataframe["regime_price_vs_200"].abs() < 3)
    )

    regime = pd.Series(UNKNOWN, index=dataframe.index)
    regime[ranging_conditions]    = RANGING
    regime[bear_conditions]       = BEAR
    regime[bull_conditions]       = BULL
    regime[early_bull_conditions] = EARLY_BULL  # can override RANGING but not BEAR

    return regime
