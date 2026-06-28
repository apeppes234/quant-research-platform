from app.metrics.deflated_sharpe import compute_deflated_sharpe


def test_deflated_sharpe_penalizes_multiple_trials():
    one_trial = compute_deflated_sharpe([1.2], trials=1)
    many_trials = compute_deflated_sharpe([1.2, 0.8, 0.7, 0.5, 0.4], trials=5)

    assert one_trial.deflated_sharpe_ratio == 1.2
    assert many_trials.trials == 5
    assert many_trials.deflated_sharpe_ratio < many_trials.best_holdout_sharpe
