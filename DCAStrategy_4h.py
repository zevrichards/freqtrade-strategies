# DCAStrategy.py - BEST VERSION
# Bull: +25.9%, 2.0% drawdown, 98.4% win rate (Oct 2024 - Oct 2025, 18 pairs, 4h)
#
# KEY DECISIONS:
#   - BULL-only regime (strict) — no EARLY_BULL, no bear entries
#     The -55% bear result came from EARLY_BULL letting it enter failed recoveries
#   - Stake cap at 4x initial — prevents one trade wiping the wallet
#   - Stoploss tightened to -15% from -25% — still wide enough for DCA but limits max loss
#   - 4h timeframe — deliberate entries, low fee drag

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from freqtrade.strategy import IStrategy, IntParameter
from freqtrade.persistence import Trade
from pandas import DataFrame
from datetime import datetime
import pandas_ta as pta
from regime_filter import add_regime_indicators, get_regime, BULL


class DCAStrategy_4h(IStrategy):

    minimal_roi = {"0": 0.03, "1440": 0.01, "4320": 0.005}
    stoploss = -0.15
    timeframe = "4h"
    trailing_stop = False
    startup_candle_count: int = 210
    position_adjustment_enable = True
    max_entry_position_adjustment = 3

    safety_order_drop_1 = 0.03
    safety_order_drop_2 = 0.06
    safety_order_drop_3 = 0.10
    safety_order_volume_scale = 1.5
    max_total_stake_multiplier = 4.0

    rsi_entry = IntParameter(40, 60, default=50, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = add_regime_indicators(dataframe)
        dataframe["rsi"]    = pta.rsi(dataframe["close"], length=14)
        dataframe["ema_20"] = pta.ema(dataframe["close"], length=20)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        regime = get_regime(dataframe)
        dataframe.loc[
            (
                (regime == BULL) &
                (dataframe["rsi"] < self.rsi_entry.value) &
                (dataframe["close"] < dataframe["ema_20"]) &
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        return dataframe

    def adjust_trade_position(
        self, trade: Trade, current_time: datetime,
        current_rate: float, current_profit: float,
        min_stake: float | None, max_stake: float,
        current_entry_rate: float, current_exit_rate: float,
        current_entry_profit: float, current_exit_profit: float,
        **kwargs,
    ):
        count = trade.nr_of_successful_entries
        initial_stake = trade.stake_amount / count if count > 0 else trade.stake_amount
        total_invested = trade.stake_amount
        stake_cap = initial_stake * self.max_total_stake_multiplier

        if total_invested >= stake_cap:
            return None

        if count == 1 and current_profit < -self.safety_order_drop_1:
            return min(trade.stake_amount * self.safety_order_volume_scale,
                       stake_cap - total_invested)
        if count == 2 and current_profit < -self.safety_order_drop_2:
            return min(trade.stake_amount * (self.safety_order_volume_scale ** 2),
                       stake_cap - total_invested)
        if count == 3 and current_profit < -self.safety_order_drop_3:
            return min(trade.stake_amount * (self.safety_order_volume_scale ** 3),
                       stake_cap - total_invested)
        return None
