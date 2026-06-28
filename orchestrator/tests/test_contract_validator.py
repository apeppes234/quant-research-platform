from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "contract" / "validator" / "validate.py"
STARTER_PATH = REPO_ROOT / "contract" / "templates" / "starter_algorithm.py"


def _validator_module():
    spec = importlib.util.spec_from_file_location("contract_validator", VALIDATOR_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_starter_algorithm_passes_contract_validator():
    validator = _validator_module()

    result = validator.validate_file(STARTER_PATH)

    assert result.ok is True
    assert result.findings == []


def test_validator_rejects_indicator_method_shadowing():
    validator = _validator_module()
    source = """
class BadStrategy:
    def initialize(self):
        self.rsi = self.rsi("SPY", 14)

    def on_data(self, data):
        if self.is_warming_up:
            return
        self.set_holdings("SPY", 1)
"""

    result = validator.validate(source)

    assert result.ok is False
    assert any(finding.rule == "indicator-name-shadowing" for finding in result.findings)


def test_validator_rejects_holdout_in_signal_logic():
    validator = _validator_module()
    source = """
HOLDOUT = ("2020-01-01", "2023-12-31")

class BadStrategy:
    def on_data(self, data):
        if self.is_warming_up:
            return
        if HOLDOUT:
            self.set_holdings("SPY", 1)
"""

    result = validator.validate(source)

    assert result.ok is False
    assert any(finding.rule == "holdout-seal" for finding in result.findings)
