"""Small Deflated Sharpe approximation for the Phase 4 snooping ledger."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist, pstdev

EULER_GAMMA = 0.5772156649015329


@dataclass(frozen=True)
class DeflatedSharpeSummary:
    best_holdout_sharpe: float
    trials: int
    expected_max_noise_sharpe: float
    deflated_sharpe_ratio: float


def compute_deflated_sharpe(holdout_sharpes: list[float], *, trials: int | None = None) -> DeflatedSharpeSummary:
    usable = [value for value in holdout_sharpes if isinstance(value, (int, float))]
    if not usable:
        return DeflatedSharpeSummary(0.0, 0, 0.0, 0.0)
    trial_count = max(trials or len(usable), len(usable), 1)
    best = max(usable)
    if trial_count <= 1:
        return DeflatedSharpeSummary(best, trial_count, 0.0, best)

    sigma = pstdev(usable) if len(usable) > 1 else 1.0
    sigma = sigma or 1.0
    normal = NormalDist()
    expected_max = sigma * (
        (1 - EULER_GAMMA) * normal.inv_cdf(1 - 1 / trial_count)
        + EULER_GAMMA * normal.inv_cdf(1 - 1 / (trial_count * 2.718281828459045))
    )
    return DeflatedSharpeSummary(
        best_holdout_sharpe=best,
        trials=trial_count,
        expected_max_noise_sharpe=expected_max,
        deflated_sharpe_ratio=best - expected_max,
    )
