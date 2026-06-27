# Starter QuantConnect algorithm — the Modeling agent begins here (contract workflow step 2).
# Compiling skeleton with the train/validation/SEALED-HOLDOUT split wired and signal hooks stubbed.
# Rules enforced by validator/validate.py + the authoring contract (docs/11). This is a TEMPLATE: it must
# remain valid Python and pass the validator (used as a CI fixture).
#
# QC idioms (docs/04): subclass QCAlgorithm; set dates/cash/universe in initialize; trade in on_data;
# NEVER overwrite indicator method names (use self._rsi = self.rsi(...), not self.rsi = ...).

# from AlgorithmImports import *   # provided by the QuantConnect/LEAN runtime


# --- Time splits ---------------------------------------------------------------
# The Modeling/Feature agents may use TRAIN + VALIDATION only. HOLDOUT is sealed during design and
# evaluated exactly once by the Backtest agent. The validator checks these dates are not referenced
# during feature construction.
TRAIN      = ("2010-01-01", "2017-12-31")
VALIDATION = ("2018-01-01", "2019-12-31")
HOLDOUT    = ("2020-01-01", "2023-12-31")   # SEALED — do not read during design


class StarterStrategy:  # subclass QCAlgorithm in the real file: class StarterStrategy(QCAlgorithm):
    def initialize(self):
        # self.set_start_date(*[int(x) for x in TRAIN[0].split("-")])   # set per the segment being run
        # self.set_end_date(...)
        # self.set_cash(100_000)
        # self._symbol = self.add_equity("SPY", Resolution.DAILY).symbol
        # CORRECT indicator idiom (do NOT write self.rsi = ...):
        # self._rsi = self.rsi(self._symbol, 14)
        ...

    def on_data(self, data):
        # Entry/exit logic ONLY uses information available at/before the current bar (no look-ahead).
        # if not self._rsi.is_ready: return
        # if self._rsi.current.value < 30 and not self.portfolio.invested:
        #     self.set_holdings(self._symbol, 1.0)
        # elif self._rsi.current.value > 70 and self.portfolio.invested:
        #     self.liquidate(self._symbol)
        ...

    # The run harness evaluates TRAIN+VALIDATION (in-sample) then HOLDOUT once, and writes
    # /workspace/results.json with both segments (sharpe, max_drawdown, equity_curve). See the contract.
