import numpy as np
import pytest

from mlcore import evaluate, pipeline, schema

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

def test_risk_bands():
    assert evaluate.risk_band(0.40, high_cutpoint=0.40, medium_cutpoint=0.20) == "HIGH"
    assert evaluate.risk_band(0.20, high_cutpoint=0.40, medium_cutpoint=0.20) == "MEDIUM"
    assert evaluate.risk_band(0.19, high_cutpoint=0.40, medium_cutpoint=0.20) == "LOW"


def test_band_cutpoints_come_from_validation_scores_and_never_overlap():
    probabilities = np.linspace(0.0, 1.0, 101)
    cuts = evaluate.band_cutpoints(probabilities, threshold=0.8)
    assert cuts["HIGH"] == 0.8
    assert cuts["MEDIUM"] == pytest.approx(0.35)
    assert evaluate.band_cutpoints(probabilities, threshold=0.2)["MEDIUM"] == 0.2


def test_band_table_counts_and_rates():
    y = np.array([0, 0, 1, 1, 1, 0])
    p = np.array([0.1, 0.2, 0.5, 0.6, 0.9, 0.4])
    rows = {r["band"]: r for r in evaluate.band_table(y, p, high_cutpoint=0.6, medium_cutpoint=0.3)}
    assert (rows["LOW"]["n"], rows["MEDIUM"]["n"], rows["HIGH"]["n"]) == (2, 2, 2)
    assert rows["LOW"]["no_show_rate"] == 0.0
    assert rows["MEDIUM"]["no_show_rate"] == 0.5
    assert rows["HIGH"]["no_show_rate"] == 1.0


def test_capacity_table_matches_a_hand_calculation():
    y = np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0])
    p = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])
    row = evaluate.capacity_table(y, p, shares=(0.2,))[0]
    assert row["flagged"] == 2
    assert row["precision"] == 0.5
    assert row["recall"] == 0.5
    assert row["lift"] == 2.5


def test_paired_difference_is_zero_for_identical_models_and_positive_for_a_better_one():
    y, p, groups = _toy_scores()
    same = evaluate.bootstrap_difference(y, p, p, groups, n_boot=50, seed=3)
    assert same["low"] == same["high"] == 0.0
    noise = np.random.default_rng(9).random(len(y))
    better = evaluate.bootstrap_difference(y, p, noise, groups, n_boot=100, seed=3)
    assert better["low"] > 0


def test_typical_ranges_come_from_training_data_and_stay_in_schema(small_parts):
    ranges = evaluate.typical_ranges(small_parts["train"])
    assert set(ranges) == set(schema.NUMERIC_FEATURES)
    for name, (low, high) in ranges.items():
        assert low <= high
        assert schema.NUMERIC_RANGES[name][0] <= low
        assert high <= schema.NUMERIC_RANGES[name][1]


def test_coefficient_table_lists_every_transformed_feature_largest_first(small_parts):
    train_frame = small_parts["train"]
    X = pipeline.select_features(train_frame)
    y = train_frame[schema.TARGET_COLUMN].to_numpy()
    model = pipeline.build_baseline().fit(X, y)
    rows = evaluate.coefficient_table(model)
    assert len(rows) == len(model.named_steps["model"].coef_[0])
    assert any(row["feature"] == "reminder_sent" for row in rows)
    sizes = [abs(row["coefficient"]) for row in rows]
    assert sizes == sorted(sizes, reverse=True)