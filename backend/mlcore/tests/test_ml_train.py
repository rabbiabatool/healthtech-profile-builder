import hashlib
import json

import joblib
import numpy as np
import pytest

from mlcore import config, evaluate, pipeline, schema, splits, train
from mlcore.data_generation import dataset_hash


def _run(directory, small_df):
    return train.train(
        df=small_df,
        artifact_dir=directory,
        docs_dir=directory / "docs",
        n_boot=30,
        make_figures=False,
        enforce_gate=False,
        write_docs=True,
    )


@pytest.fixture(scope="module")
def run_one(tmp_path_factory, small_df):
    return _run(tmp_path_factory.mktemp("run_one"), small_df)


@pytest.fixture(scope="module")
def run_two(tmp_path_factory, small_df):
    return _run(tmp_path_factory.mktemp("run_two"), small_df)


def test_artifact_and_metadata_are_written(run_one):
    metadata = json.loads(run_one["meta_path"].read_text(encoding="utf-8"))
    for key in ("model_version", "schema_version", "seed", "data_sha256", "threshold",
                "input_schema", "limitations", "disclaimer", "library_versions", "artifact_sha256"):
        assert key in metadata
    assert metadata["model_version"] == config.MODEL_VERSION
    assert metadata["disclaimer"] == config.DISCLAIMER


def test_recorded_hash_matches_the_artifact_file(run_one):
    metadata = json.loads(run_one["meta_path"].read_text(encoding="utf-8"))
    actual = hashlib.sha256(run_one["model_path"].read_bytes()).hexdigest()
    assert metadata["artifact_sha256"] == actual


def test_saved_artifact_is_one_pipeline_that_only_sees_allowlisted_columns(run_one, small_df):
    model = joblib.load(run_one["model_path"])
    assert type(model).__name__ == "Pipeline"
    seen = list(model.named_steps["prep"].feature_names_in_)
    assert seen == schema.FEATURE_COLUMNS
    assert set(seen).isdisjoint(schema.LEAKAGE_COLUMNS)
    probabilities = model.predict_proba(pipeline.select_features(small_df))[:, 1]
    assert probabilities.min() >= 0 and probabilities.max() <= 1


def test_training_twice_gives_the_same_data_metrics_and_predictions(run_one, run_two, small_df):
    assert run_one["report"]["data_sha256"] == run_two["report"]["data_sha256"] == dataset_hash(small_df)
    for name in ("dummy", "baseline", "improved"):
        first = run_one["report"]["test"]["scores"][name]
        second = run_two["report"]["test"]["scores"][name]
        assert first == pytest.approx(second)
    X = pipeline.select_features(small_df)
    one = joblib.load(run_one["model_path"]).predict_proba(X)
    two = joblib.load(run_two["model_path"]).predict_proba(X)
    np.testing.assert_allclose(one, two, atol=1e-9)


def test_threshold_was_chosen_on_validation_data(run_one, small_df):
    parts = splits.make_splits(small_df, config.SEED)
    X_val = pipeline.select_features(parts["validation"])
    y_val = parts["validation"][schema.TARGET_COLUMN].to_numpy()
    model = joblib.load(run_one["model_path"])
    expected = evaluate.choose_threshold(y_val, model.predict_proba(X_val)[:, 1])
    assert run_one["report"]["validation"]["thresholds"]["improved"] == pytest.approx(expected)


def test_model_selection_never_receives_the_test_set():
    import inspect
    parameters = inspect.signature(train.select_and_fit).parameters
    assert list(parameters) == ["train_df", "val_df", "seed"]


def test_report_split_sizes_add_up(run_one, small_df):
    total = sum(item["rows"] for item in run_one["report"]["splits"].values())
    assert total == len(small_df)


def test_quality_gate_blocks_a_model_that_does_not_beat_the_baseline():
    scores = {"dummy": {"pr_auc": 0.2}, "baseline": {"pr_auc": 0.4}, "improved": {"pr_auc": 0.39}}
    with pytest.raises(train.QualityGateError):
        train.check_quality_gate(scores)
    scores["improved"]["pr_auc"] = 0.45
    train.check_quality_gate(scores)


def test_docs_are_written_and_carry_the_disclaimer(run_one):
    docs = run_one["meta_path"].parent / "docs"
    assert (docs / "metrics.json").exists()
    card = (docs / "MODEL_CARD.md").read_text(encoding="utf-8")
    assert config.DISCLAIMER in card
    assert "Limitations" in card