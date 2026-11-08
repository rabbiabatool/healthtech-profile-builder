import joblib
import numpy as np
import pytest

from mlcore import pipeline, schema


def test_select_features_returns_exactly_the_allowlist(small_parts):
    X = pipeline.select_features(small_parts["train"])
    assert list(X.columns) == schema.FEATURE_COLUMNS
    for banned in schema.ID_COLUMNS + schema.LEAKAGE_COLUMNS + [schema.TARGET_COLUMN]:
        assert banned not in X.columns


def _xy(frame):
    return pipeline.select_features(frame), frame[schema.TARGET_COLUMN].to_numpy()


def test_dummy_predicts_the_training_base_rate(small_parts):
    X, y = _xy(small_parts["train"])
    model = pipeline.build_dummy().fit(X, y)
    probabilities = model.predict_proba(X)[:, 1]
    assert np.allclose(probabilities, y.mean())


def test_baseline_gives_valid_probabilities(small_parts):
    X, y = _xy(small_parts["train"])
    X_val, _ = _xy(small_parts["validation"])
    model = pipeline.build_baseline().fit(X, y)
    probabilities = model.predict_proba(X_val)[:, 1]
    assert probabilities.min() >= 0 and probabilities.max() <= 1


def test_baseline_only_sees_allowlisted_columns(small_parts):
    X, y = _xy(small_parts["train"])
    model = pipeline.build_baseline().fit(X, y)
    seen = list(model.named_steps["prep"].feature_names_in_)
    assert seen == schema.FEATURE_COLUMNS


def test_baseline_imputer_learns_from_training_data_only(small_parts):
    X, y = _xy(small_parts["train"])
    model = pipeline.build_baseline().fit(X, y)
    numeric = model.named_steps["prep"].named_transformers_["numeric"]
    learned = numeric.named_steps["impute"].statistics_
    expected = X[schema.NUMERIC_FEATURES].median().to_numpy()
    np.testing.assert_allclose(learned, expected)


def test_baseline_handles_missing_distance(small_parts):
    X, y = _xy(small_parts["train"])
    model = pipeline.build_baseline().fit(X, y)
    row = X.iloc[[0]].copy()
    row["distance_km"] = np.nan
    assert np.isfinite(model.predict_proba(row)[0, 1])


def test_baseline_rejects_unknown_categories(small_parts):
    X, y = _xy(small_parts["train"])
    model = pipeline.build_baseline().fit(X, y)
    row = X.iloc[[0]].copy()
    row["day_of_week"] = "SUN"
    with pytest.raises(ValueError):
        model.predict_proba(row)


def test_baseline_pipeline_survives_save_and_load(small_parts, tmp_path):
    X, y = _xy(small_parts["train"])
    model = pipeline.build_baseline().fit(X, y)
    joblib.dump(model, tmp_path / "m.joblib")
    reloaded = joblib.load(tmp_path / "m.joblib")
    assert np.allclose(model.predict_proba(X), reloaded.predict_proba(X))



def test_improved_pipeline_gives_valid_probabilities(small_parts):
    X, y = _xy(small_parts["train"])
    X_val, _ = _xy(small_parts["validation"])
    model = pipeline.build_improved().fit(X, y)
    probabilities = model.predict_proba(X_val)[:, 1]
    assert probabilities.min() >= 0 and probabilities.max() <= 1


def test_calibration_folds_never_mix_patients(small_parts):
    train = small_parts["train"]
    folds = pipeline.make_calibration_folds(
        train[schema.TARGET_COLUMN].to_numpy(), train["patient_ref"].to_numpy()
    )
    groups = train["patient_ref"].to_numpy()
    assert len(folds) == 3
    for fit_rows, calibrate_rows in folds:
        assert set(groups[fit_rows]).isdisjoint(set(groups[calibrate_rows]))


def test_calibrated_improved_model_is_one_pipeline_that_survives_saving(small_parts, tmp_path):
    train = small_parts["train"]
    X, y = _xy(train)
    folds = pipeline.make_calibration_folds(y, train["patient_ref"].to_numpy())
    model = pipeline.build_improved(calibration_folds=folds).fit(X, y)

    assert type(model).__name__ == "Pipeline"
    assert list(model.named_steps["prep"].feature_names_in_) == schema.FEATURE_COLUMNS
    assert type(model.named_steps["model"]).__name__ == "CalibratedClassifierCV"

    joblib.dump(model, tmp_path / "m.joblib")
    reloaded = joblib.load(tmp_path / "m.joblib")
    assert np.allclose(model.predict_proba(X), reloaded.predict_proba(X))


def test_improved_handles_missing_distance_and_rejects_unknown_categories(small_parts):
    X, y = _xy(small_parts["train"])
    model = pipeline.build_improved().fit(X, y)
    row = X.iloc[[0]].copy()
    row["distance_km"] = np.nan
    assert np.isfinite(model.predict_proba(row)[0, 1])
    row["appointment_type"] = "SURGERY"
    with pytest.raises(ValueError):
        model.predict_proba(row)