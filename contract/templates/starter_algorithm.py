"""Starter QuantConnect algorithm for the Phase 2 backtest spine.

The Modeling agent starts here, then the Backtest agent runs the in-sample
segment and the sealed holdout segment exactly once. Keep this file valid
Python: it is the validator fixture.
"""

from AlgorithmImports import *


TRAIN = ("2010-01-01", "2017-12-31")
VALIDATION = ("2018-01-01", "2019-12-31")
HOLDOUT = ("2020-01-01", "2023-12-31")

RUN_SEGMENT = "in_sample"
INITIAL_CASH = 100000
TARGET_TICKER = "SPY"


class StarterStrategy(QCAlgorithm):
    def initialize(self):
        start, end = self._segment_bounds(RUN_SEGMENT)
        self.set_start_date(*self._date_parts(start))
        self.set_end_date(*self._date_parts(end))
        self.set_cash(INITIAL_CASH)

        equity = self.add_equity(TARGET_TICKER, Resolution.DAILY)
        self._symbol = equity.symbol
        self._rsi = self.rsi(self._symbol, 14, MovingAverageType.WILDERS, Resolution.DAILY)
        self._sma = self.sma(self._symbol, 200, Resolution.DAILY)
        self.set_warm_up(200, Resolution.DAILY)

    def on_data(self, data):
        if self.is_warming_up:
            return
        if not self._rsi.is_ready or not self._sma.is_ready:
            return
        if not data.contains_key(self._symbol):
            return

        bar = data[self._symbol]
        invested = self.portfolio[self._symbol].invested
        price_above_trend = bar.close > self._sma.current.value
        oversold_recovery = self._rsi.current.value < 35
        risk_off = self._rsi.current.value > 68 or bar.close < self._sma.current.value

        if oversold_recovery and price_above_trend and not invested:
            self.set_holdings(self._symbol, 1.0)
        elif risk_off and invested:
            self.liquidate(self._symbol)

    def _segment_bounds(self, segment):
        if segment == "holdout":
            return HOLDOUT
        return (TRAIN[0], VALIDATION[1])

    def _date_parts(self, value):
        year, month, day = value.split("-")
        return int(year), int(month), int(day)
