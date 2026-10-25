import numpy as np
import pytest

from mlcore import evaluate, pipeline

Y = np.array([0, 0, 1, 1])
P = np.array([0.1, 0.4, 0.35, 0.8])


def test_scores_match_hand_calculated_values():
    scores = evaluate.score_probabilities(Y, P)
    assert scores["roc_auc"] == pytest.approx(0.75)
    assert scores["pr_auc"] == pytest.approx(0.8333, abs=1e-4)
    assert scores["brier"] == pytest.approx(0.1581, abs=1e-4)


def test_perfect_predictions_score_one():
    scores = evaluate.score_probabilities(Y, np.array([0.0, 0.1, 0.9, 1.0]))
    assert scores["pr_auc"] == 1.0
    assert scores["roc_auc"] == 1.0


def test_threshold_is_chosen_from_the_data_it_is_given():
    assert evaluate.choose_threshold(Y, P) == pytest.approx(0.35)


def test_threshold_metrics_count_outcomes_correctly():
    result = evaluate.threshold_metrics(Y, P, 0.35)
    assert (result["tp"], result["fp"], result["tn"], result["fn"]) == (2, 1, 1, 0)
    assert result["precision"] == pytest.approx(0.6667, abs=1e-4)
    assert result["recall"] == 1.0


def test_risk_bands():
    assert evaluate.risk_band(0.40, 0.40) == "HIGH"
    assert evaluate.risk_band(0.20, 0.40) == "MEDIUM"
    assert evaluate.risk_band(0.19, 0.40) == "LOW"


def _toy_scores():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    p = np.clip(y * 0.3 + rng.random(400) * 0.7, 0, 1)
    groups = np.repeat(np.arange(100), 4)
    return y, p, groups


def test_bootstrap_is_seeded_and_gives_a_sensible_interval():
    y, p, groups = _toy_scores()
    first = evaluate.bootstrap_ci(y, p, groups, n_boot=100, seed=5)
    second = evaluate.bootstrap_ci(y, p, groups, n_boot=100, seed=5)
    assert first == second
    assert first["pr_auc"]["low"] < first["pr_auc"]["high"]


def test_slices_cover_every_row_once_per_slice_column(small_parts):
    X = pipeline.select_features(small_parts["validation"])
    rng = np.random.default_rng(1)
    y = small_parts["validation"]["no_show"].to_numpy()
    p = rng.random(len(X))
    rows = evaluate.slice_metrics(X, y, p, threshold=0.5)
    for column in ("age_band", "lead_time_bucket", "appointment_type", "distance"):
        assert sum(r["n"] for r in rows if r["slice"] == column) == len(X)


def test_error_summary_counts_match_manual_counts(small_parts):
    X = pipeline.select_features(small_parts["validation"])
    y = small_parts["validation"]["no_show"].to_numpy()
    p = np.random.default_rng(2).random(len(X))
    summary = evaluate.error_summary(X, y, p, threshold=0.5)
    assert summary["false_negatives"] == int(((y == 1) & (p < 0.5)).sum())
    assert summary["false_positives"] == int(((y == 0) & (p >= 0.5)).sum())