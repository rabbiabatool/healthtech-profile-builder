"""Train, compare, evaluate and save the no-show model:  python -m mlcore.train"""
import hashlib
import json
import platform
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn

from mlcore import config, evaluate, figures, model_card, pipeline, schema, splits
from mlcore.data_generation import dataset_hash, generate_appointments


class QualityGateError(RuntimeError):
    """Raised when the models do not meet the documented quality bar."""


BASELINE_GRID = [{"C": c} for c in (0.1, 1.0, 10.0)]
IMPROVED_GRID = [
    {"learning_rate": rate, "max_leaf_nodes": leaves}
    for rate in (0.05, 0.1)
    for leaves in (8, 16, 31)
]


def _xy(frame):
    return pipeline.select_features(frame), frame[schema.TARGET_COLUMN].to_numpy()


def _prob(model, X):
    return model.predict_proba(X)[:, 1]


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_and_fit(train_df, val_df, seed=config.SEED):
    """Uses ONLY train and validation data. The test set is not passed in."""
    X_train, y_train = _xy(train_df)
    X_val, y_val = _xy(val_df)

    models = {"dummy": pipeline.build_dummy().fit(X_train, y_train)}

    baseline_trials, baseline_models = [], []
    for params in BASELINE_GRID:
        candidate = pipeline.build_baseline(seed=seed, **params).fit(X_train, y_train)
        score = evaluate.score_probabilities(y_val, _prob(candidate, X_val))["pr_auc"]
        baseline_trials.append({"params": params, "val_pr_auc": score})
        baseline_models.append(candidate)
    best = int(np.argmax([t["val_pr_auc"] for t in baseline_trials]))
    models["baseline"] = baseline_models[best]
    chosen_baseline = baseline_trials[best]["params"]

    improved_trials = []
    for params in IMPROVED_GRID:
        candidate = pipeline.build_improved(seed=seed, **params).fit(X_train, y_train)
        score = evaluate.score_probabilities(y_val, _prob(candidate, X_val))["pr_auc"]
        improved_trials.append({"params": params, "val_pr_auc": score})
    best = int(np.argmax([t["val_pr_auc"] for t in improved_trials]))
    chosen_improved = improved_trials[best]["params"]

    folds = pipeline.make_calibration_folds(y_train, train_df[splits.GROUP_COLUMN].to_numpy(), seed)
    models["improved"] = pipeline.build_improved(
        seed=seed, calibration_folds=folds, **chosen_improved
    ).fit(X_train, y_train)

    val_probs = {name: _prob(model, X_val) for name, model in models.items()}
    thresholds = {
        name: evaluate.choose_threshold(y_val, val_probs[name]) for name in ("baseline", "improved")
    }
    return {
        "models": models,
        "thresholds": thresholds,
        "validation": {
            "scores": {name: evaluate.score_probabilities(y_val, p) for name, p in val_probs.items()},
            "baseline_trials": baseline_trials,
            "improved_trials": improved_trials,
            "chosen_params": {"baseline": chosen_baseline, "improved": chosen_improved},
            "thresholds": thresholds,
            "operating_point": {
                name: evaluate.threshold_metrics(y_val, val_probs[name], thresholds[name])
                for name in thresholds
            },
            "permutation_importance": evaluate.permutation_summary(models["improved"], X_val, y_val, seed),
        },
    }


def check_quality_gate(validation_scores):
    dummy = validation_scores["dummy"]["pr_auc"]
    baseline = validation_scores["baseline"]["pr_auc"]
    improved = validation_scores["improved"]["pr_auc"]
    problems = []
    if baseline <= dummy:
        problems.append(f"baseline PR-AUC {baseline} does not beat the dummy {dummy}")
    if improved <= baseline:
        problems.append(f"improved PR-AUC {improved} does not beat the baseline {baseline}")
    if problems:
        raise QualityGateError("; ".join(problems))


def final_evaluation(fitted, test_df, seed=config.SEED, n_boot=config.BOOTSTRAP_ROUNDS):
    """The one and only look at the test set."""
    X_test, y_test = _xy(test_df)
    groups = test_df[splits.GROUP_COLUMN].to_numpy()
    probs = {name: _prob(model, X_test) for name, model in fitted["models"].items()}
    thresholds = fitted["thresholds"]
    improved_threshold = thresholds["improved"]

    test_report = {
        "scores": {name: evaluate.score_probabilities(y_test, p) for name, p in probs.items()},
        "confidence_intervals": {
            name: evaluate.bootstrap_ci(y_test, probs[name], groups, n_boot, seed)
            for name in ("baseline", "improved")
        },
        "operating_point": {
            name: evaluate.threshold_metrics(y_test, probs[name], thresholds[name]) for name in thresholds
        },
        "calibration": evaluate.calibration_points(y_test, probs["improved"]),
        "slices": evaluate.slice_metrics(X_test, y_test, probs["improved"], improved_threshold),
        "errors": evaluate.error_summary(X_test, y_test, probs["improved"], improved_threshold),
    }
    return test_report, {"y_test": y_test, "probs": probs}


def _build_metadata(report, df):
    threshold = report["validation"]["thresholds"]["improved"]
    return {
        "model_version": config.MODEL_VERSION,
        "schema_version": config.SCHEMA_VERSION,
        "model_type": "HistGradientBoostingClassifier with sigmoid calibration, inside one scikit-learn Pipeline",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": report["seed"],
        "data_version": report["data_version"],
        "data_sha256": report["data_sha256"],
        "rows": int(len(df)),
        "splits": report["splits"],
        "class_balance": round(float(df[schema.TARGET_COLUMN].mean()), 4),
        "threshold": threshold,
        "risk_band_cutpoints": {"HIGH": threshold, "MEDIUM": threshold * config.MEDIUM_BAND_FRACTION},
        "metrics_summary": {
            "validation": report["validation"]["scores"]["improved"],
            "test": report["test"]["scores"]["improved"],
            "test_baseline": report["test"]["scores"]["baseline"],
        },
        "feature_columns": schema.FEATURE_COLUMNS,
        "input_schema": {
            "numeric_ranges": {name: list(bounds) for name, bounds in schema.NUMERIC_RANGES.items()},
            "categorical_values": schema.CATEGORICAL_VALUES,
            "boolean": schema.BOOLEAN_FEATURES,
            "nullable": schema.NULLABLE_FEATURES,
        },
        "limitations": config.LIMITATIONS,
        "disclaimer": config.DISCLAIMER,
        "library_versions": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "joblib": joblib.__version__,
        },
    }


def save_artifact(model, metadata, artifact_dir):
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / config.ARTIFACT_FILENAME
    joblib.dump(model, model_path)
    metadata = dict(metadata)
    metadata["artifact_file"] = model_path.name
    metadata["artifact_sha256"] = _file_sha256(model_path)
    meta_path = artifact_dir / config.METADATA_FILENAME
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return model_path, meta_path, metadata


def train(
    df=None,
    seed=config.SEED,
    artifact_dir=config.ARTIFACT_DIR,
    docs_dir=config.DOCS_ML_DIR,
    n_boot=config.BOOTSTRAP_ROUNDS,
    make_figures=True,
    enforce_gate=True,
    write_docs=True,
):
    if df is None:
        df = generate_appointments(seed=seed)

    parts = splits.make_splits(df, seed)
    splits.assert_no_patient_overlap(parts)

    fitted = select_and_fit(parts["train"], parts["validation"], seed)
    if enforce_gate:
        check_quality_gate(fitted["validation"]["scores"])

    test_report, arrays = final_evaluation(fitted, parts["test"], seed, n_boot)

    report = {
        "model_version": config.MODEL_VERSION,
        "schema_version": config.SCHEMA_VERSION,
        "data_version": config.DATA_VERSION,
        "seed": seed,
        "data_sha256": dataset_hash(df),
        "splits": splits.describe_splits(parts),
        "validation": fitted["validation"],
        "test": test_report,
        "quality_gate_enforced": enforce_gate,
    }

    metadata = _build_metadata(report, df)
    model_path, meta_path, metadata = save_artifact(fitted["models"]["improved"], metadata, artifact_dir)

    if write_docs:
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        model_card.write(report, docs_dir / "MODEL_CARD.md")
        if make_figures:
            figures.make_all(report, arrays, docs_dir / "figures")

    return {"report": report, "metadata": metadata, "model_path": model_path, "meta_path": meta_path}


def main():
    try:
        outcome = train()
    except QualityGateError as error:
        raise SystemExit(f"Quality gate failed, nothing was saved: {error}")
    report = outcome["report"]
    scores = report["test"]["scores"]
    intervals = report["test"]["confidence_intervals"]
    print(f"Model version : {config.MODEL_VERSION}")
    print(f"Artifact      : {outcome['model_path']}")
    print(f"Artifact hash : {outcome['metadata']['artifact_sha256']}")
    print(f"Threshold     : {report['validation']['thresholds']['improved']:.4f} (chosen on validation)")
    for name in ("dummy", "baseline", "improved"):
        print(f"Test PR-AUC {name:9s}: {scores[name]['pr_auc']}")
    print(f"Improved PR-AUC 95% interval: {intervals['improved']['pr_auc']}")


if __name__ == "__main__":
    main()