"""Canonical Phase 4 define_outcome rubric."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RubricCriterion:
    id: str
    label: str
    pass_condition: str
    checked_from: str


DEFAULT_CRITERIA = [
    RubricCriterion(
        id="holdout_sharpe",
        label="Out-of-sample performance",
        pass_condition="Sealed-holdout Sharpe > 1.0",
        checked_from="results.json holdout segment",
    ),
    RubricCriterion(
        id="is_oos_gap",
        label="Overfit guard",
        pass_condition="Absolute difference between in-sample Sharpe and holdout Sharpe < 0.5",
        checked_from="results.json in_sample and holdout segments",
    ),
    RubricCriterion(
        id="look_ahead",
        label="Look-ahead audit",
        pass_condition="Zero look-ahead findings from the Risk auditor",
        checked_from="audit.json look_ahead_count and findings",
    ),
    RubricCriterion(
        id="deflated_sharpe",
        label="Multiple-testing correction",
        pass_condition="Deflated Sharpe Ratio > 0 after correcting for variants tried",
        checked_from="results.json and the data-snooping ledger",
    ),
    RubricCriterion(
        id="max_drawdown",
        label="Tail risk",
        pass_condition="Max drawdown < 25%",
        checked_from="results.json holdout metrics",
    ),
]


def default_rubric_markdown() -> str:
    rows = "\n".join(
        f"{index}. **{criterion.label}**: {criterion.pass_condition}. Checked from {criterion.checked_from}."
        for index, criterion in enumerate(DEFAULT_CRITERIA, start=1)
    )
    return (
        "# Quant strategy anti-overfit rubric\n\n"
        "A candidate is satisfied only if all five independently gradeable criteria pass.\n\n"
        f"{rows}\n\n"
        "Use max_iterations=3 unless more convergence room is explicitly requested. Every iteration that "
        "evaluates the sealed holdout must append a variant "
        "entry to the data-snooping ledger and count toward the Deflated Sharpe denominator."
    )
