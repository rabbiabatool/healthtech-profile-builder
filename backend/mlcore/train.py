# """Train, compare, evaluate and save the no-show model:  python -m mlcore.train"""
# import hashlib
# import json
# import platform
# from datetime import datetime, timezone

# import joblib
# import numpy as np
# import pandas as pd
# import scipy
# import sklearn

# from mlcore import config, evaluate, figures, model_card, pipeline, schema, splits
# from mlcore.data_generation import dataset_hash, generate_appointments


# class QualityGateError(RuntimeError):
#     """Raised when the models do not meet the documented quality bar."""


# BASELINE_GRID = [{"C": c} for c in (0.1, 1.0, 10.0)]
# IMPROVED_GRID = [
#     {"learning_rate": rate, "max_leaf_nodes": leaves}
#     for rate in (0.05, 0.1)
#     for leaves in (8, 16, 31)
# ]


# def _xy(frame):
#     return pipeline.select_features(frame), frame[schema.TARGET_COLUMN].to_numpy()


# def _prob(model, X):
#     return model.predict_proba(X)[:, 1]


# def _file_sha256(path):
#     digest = hashlib.sha256()
#     with open(path, "rb") as handle:
#         for chunk in iter(lambda: handle.read(1024 * 1024), b""):
#             digest.update(chunk)
#     return digest.hexdigest()


# def select_and_fit(train_df, val_df, seed=config.SEED):
#     """Uses ONLY train and validation data. The test set is not passed in."""
#     X_train, y_train = _xy(train_df)
#     X_val, y_val = _xy(val_df)

#     # Create patient-grouped calibration folds using training data only.
#     folds = pipeline.make_calibration_folds(
#         y_train,
#         train_df[splits.GROUP_COLUMN].to_numpy(),
#         seed,
#     )

#     # Dummy model
#     models = {
#         "dummy": pipeline.build_dummy().fit(X_train, y_train)
#     }

#     # --------------------------------------------------
#     # 1. Select the best Logistic Regression baseline
#     # --------------------------------------------------
#     baseline_trials = []
#     baseline_models = []

#     for params in BASELINE_GRID:
#         candidate = pipeline.build_baseline(
#             seed=seed,
#             **params,
#         ).fit(X_train, y_train)

#         score = evaluate.score_probabilities(
#             y_val,
#             _prob(candidate, X_val),
#         )["pr_auc"]

#         baseline_trials.append({
#             "params": params,
#             "val_pr_auc": score,
#         })
#         baseline_models.append(candidate)

#     best_baseline_idx = int(
#         np.argmax([trial["val_pr_auc"] for trial in baseline_trials])
#     )

#     models["baseline"] = baseline_models[best_baseline_idx]
#     chosen_baseline = baseline_trials[best_baseline_idx]["params"]

#     # --------------------------------------------------
#     # 2. Select the best calibrated improved model
#     # --------------------------------------------------
#     improved_trials = []
#     improved_models = []

#     for params in IMPROVED_GRID:
#         candidate = pipeline.build_improved(
#             seed=seed,
#             calibration_folds=folds,
#             **params,
#         ).fit(X_train, y_train)

#         # Evaluate the calibrated candidate on validation data.
#         probabilities = _prob(candidate, X_val)

#         score = evaluate.score_probabilities(
#             y_val,
#             probabilities,
#         )["pr_auc"]

#         improved_trials.append({
#             "params": params,
#             "val_pr_auc": score,
#         })
#         improved_models.append(candidate)

#     best_improved_idx = int(
#         np.argmax([trial["val_pr_auc"] for trial in improved_trials])
#     )

#     # Reuse the best fitted candidate.
#     models["improved"] = improved_models[best_improved_idx]
#     chosen_improved = improved_trials[best_improved_idx]["params"]

#     # --------------------------------------------------
#     # 3. Calculate validation probabilities and thresholds
#     # --------------------------------------------------
#     val_probs = {
#         name: _prob(model, X_val)
#         for name, model in models.items()
#     }

#     thresholds = {
#         name: evaluate.choose_threshold(y_val, val_probs[name])
#         for name in ("baseline", "improved")
#     }

#     # --------------------------------------------------
#     # 4. Print validation results
#     # --------------------------------------------------
#     print("\n========== VALIDATION RESULTS ==========")

#     for name in models:
#         scores = evaluate.score_probabilities(y_val, val_probs[name])
#         print(f"{name.upper()} PR-AUC: {scores['pr_auc']:.4f}")

#     print("\nBaseline configurations:")
#     for trial in baseline_trials:
#         print(
#             f"  Parameters: {trial['params']}, "
#             f"PR-AUC: {trial['val_pr_auc']:.4f}"
#         )

#     print("\nImproved configurations (calibrated):")
#     for trial in improved_trials:
#         print(
#             f"  Parameters: {trial['params']}, "
#             f"PR-AUC: {trial['val_pr_auc']:.4f}"
#         )

#     print("\nSelected parameters:")
#     print(f"  Baseline: {chosen_baseline}")
#     print(f"  Improved: {chosen_improved}")
#     print("========================================\n")

#     # --------------------------------------------------
#     # 5. Return models and evaluation information
#     # --------------------------------------------------
#     return {
#         "models": models,
#         "thresholds": thresholds,
#         "validation": {
#             "scores": {
#                 name: evaluate.score_probabilities(y_val, probabilities)
#                 for name, probabilities in val_probs.items()
#             },
#             "baseline_trials": baseline_trials,
#             "improved_trials": improved_trials,
#             "chosen_params": {
#                 "baseline": chosen_baseline,
#                 "improved": chosen_improved,
#             },
#             "thresholds": thresholds,
#             "operating_point": {
#                 name: evaluate.threshold_metrics(
#                     y_val,
#                     val_probs[name],
#                     thresholds[name],
#                 )
#                 for name in thresholds
#             },
#             "permutation_importance": evaluate.permutation_summary(
#                 models["improved"],
#                 X_val,
#                 y_val,
#                 seed,
#             ),
#         },
#     }

# # def select_and_fit(train_df, val_df, seed=config.SEED):
# #     """Uses ONLY train and validation data. The test set is not passed in."""
# #     X_train, y_train = _xy(train_df)
# #     X_val, y_val = _xy(val_df)

# #     models = {"dummy": pipeline.build_dummy().fit(X_train, y_train)}

# #     baseline_trials, baseline_models = [], []
# #     for params in BASELINE_GRID:
# #         candidate = pipeline.build_baseline(seed=seed, **params).fit(X_train, y_train)
# #         score = evaluate.score_probabilities(y_val, _prob(candidate, X_val))["pr_auc"]
# #         baseline_trials.append({"params": params, "val_pr_auc": score})
# #         baseline_models.append(candidate)
# #     best = int(np.argmax([t["val_pr_auc"] for t in baseline_trials]))
# #     models["baseline"] = baseline_models[best]
# #     chosen_baseline = baseline_trials[best]["params"]

# #     improved_trials = []
# #     for params in IMPROVED_GRID:
# #         candidate = pipeline.build_improved(seed=seed, **params).fit(X_train, y_train)
# #         score = evaluate.score_probabilities(y_val, _prob(candidate, X_val))["pr_auc"]
# #         improved_trials.append({"params": params, "val_pr_auc": score})
# #     best = int(np.argmax([t["val_pr_auc"] for t in improved_trials]))
# #     chosen_improved = improved_trials[best]["params"]

# #     folds = pipeline.make_calibration_folds(y_train, train_df[splits.GROUP_COLUMN].to_numpy(), seed)
# #     models["improved"] = pipeline.build_improved(
# #         seed=seed, calibration_folds=folds, **chosen_improved
# #     ).fit(X_train, y_train)

# #     val_probs = {name: _prob(model, X_val) for name, model in models.items()}
# #     thresholds = {
# #         name: evaluate.choose_threshold(y_val, val_probs[name]) for name in ("baseline", "improved")
# #     }
   
# #     print("\n========== VALIDATION RESULTS ==========")

# #     for name, model in models.items():
# #         scores = evaluate.score_probabilities(y_val, val_probs[name])
# #         print(f"{name.upper()} PR-AUC: {scores['pr_auc']:.4f}")

# #     print("\nBaseline configurations:")
# #     for trial in baseline_trials:
# #         print(f"  Parameters: {trial['params']}, "
# #               f"PR-AUC: {trial['val_pr_auc']:.4f}")

# #     print("\nImproved configurations:")
# #     for trial in improved_trials:
# #         print(f"  Parameters: {trial['params']}, "
# #               f"PR-AUC: {trial['val_pr_auc']:.4f}")

# #     print("\nSelected parameters:")
# #     print(f"  Baseline: {chosen_baseline}")
# #     print(f"  Improved: {chosen_improved}")

# #     print("========================================\n")

# #     return {
# #         "models": models,
# #         "thresholds": thresholds,
# #         "validation": {
# #             "scores": {name: evaluate.score_probabilities(y_val, p) for name, p in val_probs.items()},
# #             "baseline_trials": baseline_trials,
# #             "improved_trials": improved_trials,
# #             "chosen_params": {"baseline": chosen_baseline, "improved": chosen_improved},
# #             "thresholds": thresholds,
# #             "operating_point": {
# #                 name: evaluate.threshold_metrics(y_val, val_probs[name], thresholds[name])
# #                 for name in thresholds
# #             },
# #             "permutation_importance": evaluate.permutation_summary(models["improved"], X_val, y_val, seed),
# #         },
# #     }


# def check_quality_gate(validation_scores):
#     dummy = validation_scores["dummy"]["pr_auc"]
#     baseline = validation_scores["baseline"]["pr_auc"]
#     improved = validation_scores["improved"]["pr_auc"]
#     problems = []
#     if baseline <= dummy:
#         problems.append(f"baseline PR-AUC {baseline} does not beat the dummy {dummy}")
#     if improved <= baseline:
#         problems.append(f"improved PR-AUC {improved} does not beat the baseline {baseline}")
#     if problems:
#         raise QualityGateError("; ".join(problems))



# def final_evaluation(
#     fitted,
#     test_df,
#     seed=config.SEED,
#     n_boot=config.BOOTSTRAP_ROUNDS,
# ):
#     """The one and only look at the test set."""

#     X_test, y_test = _xy(test_df)
#     groups = test_df[splits.GROUP_COLUMN].to_numpy()

#     probs = {
#         name: _prob(model, X_test)
#         for name, model in fitted["models"].items()
#     }

#     thresholds = fitted["thresholds"]
#     improved_threshold = thresholds["improved"]

#     test_report = {
#         "scores": {
#             name: evaluate.score_probabilities(y_test, p)
#             for name, p in probs.items()
#         },
#         "confidence_intervals": {
#             name: evaluate.bootstrap_ci(
#                 y_test,
#                 probs[name],
#                 groups,
#                 n_boot,
#                 seed,
#             )
#             for name in ("baseline", "improved")
#         },
#         "paired_pr_auc_difference": (
#             evaluate.paired_bootstrap_pr_auc_difference(
#                 y_true=y_test,
#                 baseline_prob=probs["baseline"],
#                 improved_prob=probs["improved"],
#                 groups=groups,
#                 n_boot=n_boot,
#                 seed=seed,
#             )
#         ),
#         "operating_point": {
#             name: evaluate.threshold_metrics(
#                 y_test,
#                 probs[name],
#                 thresholds[name],
#             )
#             for name in thresholds
#         },
#         "calibration": evaluate.calibration_points(
#             y_test,
#             probs["improved"],
#         ),
#         "slices": evaluate.slice_metrics(
#             X_test,
#             y_test,
#             probs["improved"],
#             improved_threshold,
#         ),
#         "errors": evaluate.error_summary(
#             X_test,
#             y_test,
#             probs["improved"],
#             improved_threshold,
#         ),
#     }

#     return test_report, {
#         "y_test": y_test,
#         "probs": probs,
#     }


#     # test_report = {
#     #     "scores": {name: evaluate.score_probabilities(y_test, p) for name, p in probs.items()},
#     #     "confidence_intervals": {
#     #         name: evaluate.bootstrap_ci(y_test, probs[name], groups, n_boot, seed)
#     #         for name in ("baseline", "improved")
#     #     },
#     #     "operating_point": {
#     #         name: evaluate.threshold_metrics(y_test, probs[name], thresholds[name]) for name in thresholds
#     #     },
#     #     "calibration": evaluate.calibration_points(y_test, probs["improved"]),
#     #     "slices": evaluate.slice_metrics(X_test, y_test, probs["improved"], improved_threshold),
#     #     "errors": evaluate.error_summary(X_test, y_test, probs["improved"], improved_threshold),
#     # }
    


# def _build_metadata(report, df):
#     threshold = report["validation"]["thresholds"]["improved"]
#     return {
#         "model_version": config.MODEL_VERSION,
#         "schema_version": config.SCHEMA_VERSION,
#         "model_type": "HistGradientBoostingClassifier with sigmoid calibration, inside one scikit-learn Pipeline",
#         "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
#         "seed": report["seed"],
#         "data_version": report["data_version"],
#         "data_sha256": report["data_sha256"],
#         "rows": int(len(df)),
#         "splits": report["splits"],
#         "class_balance": round(float(df[schema.TARGET_COLUMN].mean()), 4),
#         "threshold": threshold,
#         "risk_band_cutpoints": {"HIGH": threshold, "MEDIUM": threshold * config.MEDIUM_BAND_FRACTION},
#         "metrics_summary": {
#             "validation": report["validation"]["scores"]["improved"],
#             "test": report["test"]["scores"]["improved"],
#             "test_baseline": report["test"]["scores"]["baseline"],
#         },
#         "feature_columns": schema.FEATURE_COLUMNS,
#         "input_schema": {
#             "numeric_ranges": {name: list(bounds) for name, bounds in schema.NUMERIC_RANGES.items()},
#             "categorical_values": schema.CATEGORICAL_VALUES,
#             "boolean": schema.BOOLEAN_FEATURES,
#             "nullable": schema.NULLABLE_FEATURES,
#         },
#         "limitations": config.LIMITATIONS,
#         "disclaimer": config.DISCLAIMER,
#         "library_versions": {
#             "python": platform.python_version(),
#             "scikit-learn": sklearn.__version__,
#             "numpy": np.__version__,
#             "pandas": pd.__version__,
#             "scipy": scipy.__version__,
#             "joblib": joblib.__version__,
#         },
#     }


# def save_artifact(model, metadata, artifact_dir):
#     artifact_dir.mkdir(parents=True, exist_ok=True)
#     model_path = artifact_dir / config.ARTIFACT_FILENAME
#     joblib.dump(model, model_path)
#     metadata = dict(metadata)
#     metadata["artifact_file"] = model_path.name
#     metadata["artifact_sha256"] = _file_sha256(model_path)
#     meta_path = artifact_dir / config.METADATA_FILENAME
#     meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
#     return model_path, meta_path, metadata


# def train(
#     df=None,
#     seed=config.SEED,
#     artifact_dir=config.ARTIFACT_DIR,
#     docs_dir=config.DOCS_ML_DIR,
#     n_boot=config.BOOTSTRAP_ROUNDS,
#     make_figures=True,
#     enforce_gate=True,
#     write_docs=True,
# ):
#     if df is None:
#         df = generate_appointments(seed=seed)

#     parts = splits.make_splits(df, seed)
#     splits.assert_no_patient_overlap(parts)

#     fitted = select_and_fit(parts["train"], parts["validation"], seed)
#     if enforce_gate:
#         check_quality_gate(fitted["validation"]["scores"])

#     test_report, arrays = final_evaluation(fitted, parts["test"], seed, n_boot)

#     report = {
#         "model_version": config.MODEL_VERSION,
#         "schema_version": config.SCHEMA_VERSION,
#         "data_version": config.DATA_VERSION,
#         "seed": seed,
#         "data_sha256": dataset_hash(df),
#         "splits": splits.describe_splits(parts),
#         "validation": fitted["validation"],
#         "test": test_report,
#         "quality_gate_enforced": enforce_gate,
#     }

#     metadata = _build_metadata(report, df)
#     model_path, meta_path, metadata = save_artifact(fitted["models"]["improved"], metadata, artifact_dir)

#     if write_docs:
#         docs_dir.mkdir(parents=True, exist_ok=True)
#         (docs_dir / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
#         model_card.write(report, docs_dir / "MODEL_CARD.md")
#         if make_figures:
#             figures.make_all(report, arrays, docs_dir / "figures")

#     return {"report": report, "metadata": metadata, "model_path": model_path, "meta_path": meta_path}


# def main():
#     try:
#         outcome = train()
#     except QualityGateError as error:
#         raise SystemExit(f"Quality gate failed, nothing was saved: {error}")
#     report = outcome["report"]
#     scores = report["test"]["scores"]
#     intervals = report["test"]["confidence_intervals"]
#     print(f"Model version : {config.MODEL_VERSION}")
#     print(f"Artifact      : {outcome['model_path']}")
#     print(f"Artifact hash : {outcome['metadata']['artifact_sha256']}")
#     print(f"Threshold     : {report['validation']['thresholds']['improved']:.4f} (chosen on validation)")
#     for name in ("dummy", "baseline", "improved"):
#         print(f"Test PR-AUC {name:9s}: {scores[name]['pr_auc']}")
#     print(f"Improved PR-AUC 95% interval: {intervals['improved']['pr_auc']}")
#     comparison = report["test"]["paired_pr_auc_difference"]

#     print(
#         "Improved - baseline PR-AUC difference: "
#         f"{comparison['observed_difference']}"
#     )
#     print(
#         "Paired difference 95% confidence interval: "
#         f"{comparison['confidence_interval_95']}"
#     )
#     print(
#         "Bootstrap samples used: "
#         f"{comparison['bootstrap_rounds_used']}"
#     )


# if __name__ == "__main__":
#     main()

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
    """Raised when the shipped model does not meet the documented quality bar."""


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
    shipped = config.SHIPPED_MODEL
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
    band_cutpoints = evaluate.band_cutpoints(val_probs[shipped], thresholds[shipped])
    return {
        "models": models,
        "thresholds": thresholds,
        "validation": {
            "shipped_model": shipped,
            "scores": {name: evaluate.score_probabilities(y_val, p) for name, p in val_probs.items()},
            "baseline_trials": baseline_trials,
            "improved_trials": improved_trials,
            "chosen_params": {"baseline": chosen_baseline, "improved": chosen_improved},
            "band_cutpoints": band_cutpoints,
            "thresholds": thresholds,
            "operating_point": {
                name: evaluate.threshold_metrics(y_val, val_probs[name], thresholds[name])
                for name in thresholds
            },
            "baseline_coefficients": evaluate.coefficient_table(models["baseline"]),
            "permutation_importance": evaluate.permutation_summary(models[shipped], X_val, y_val, seed),
        },
    }


def check_quality_gate(validation_scores, shipped=None):
    """The model we ship must at least beat the always-the-base-rate dummy on validation."""
    shipped = shipped or config.SHIPPED_MODEL
    dummy = validation_scores["dummy"]["pr_auc"]
    candidate = validation_scores[shipped]["pr_auc"]
    if candidate <= dummy:
        raise QualityGateError(f"{shipped} PR-AUC {candidate} does not beat the dummy {dummy}")


def final_evaluation(fitted, test_df, seed=config.SEED, n_boot=config.BOOTSTRAP_ROUNDS):
    """The one and only look at the test set."""
    shipped = config.SHIPPED_MODEL
    X_test, y_test = _xy(test_df)
    groups = test_df[splits.GROUP_COLUMN].to_numpy()
    probs = {name: _prob(model, X_test) for name, model in fitted["models"].items()}
    thresholds = fitted["thresholds"]
    cuts = fitted["validation"]["band_cutpoints"]
    shipped_threshold = thresholds[shipped]

    test_report = {
        "shipped_model": shipped,
        "scores": {name: evaluate.score_probabilities(y_test, p) for name, p in probs.items()},
        "confidence_intervals": {
            name: evaluate.bootstrap_ci(y_test, probs[name], groups, n_boot, seed)
            for name in ("baseline", "improved")
        },
        "operating_point": {
            name: evaluate.threshold_metrics(y_test, probs[name], thresholds[name]) for name in thresholds
        },
        "calibration": evaluate.calibration_points(y_test, probs[shipped]),
        "slices": evaluate.slice_metrics(X_test, y_test, probs[shipped], shipped_threshold),
        "errors": evaluate.error_summary(X_test, y_test, probs[shipped], shipped_threshold),
        "bands": evaluate.band_table(y_test, probs[shipped], cuts["HIGH"], cuts["MEDIUM"]),
        "capacity": evaluate.capacity_table(y_test, probs[shipped]),
        "paired_difference": evaluate.bootstrap_difference(
            y_test, probs["improved"], probs["baseline"], groups, n_boot, seed
        ),
    }
    return test_report, {"y_test": y_test, "probs": probs}


def _build_metadata(report, df):
    shipped = report["shipped_model"]
    threshold = report["validation"]["thresholds"][shipped]
    return {
        "model_version": config.MODEL_VERSION,
        "schema_version": config.SCHEMA_VERSION,
        "shipped_model": shipped,
        "model_type": config.MODEL_TYPES[shipped],
        "selection_note": config.SHIPPED_MODEL_REASON,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": report["seed"],
        "data_version": report["data_version"],
        "data_sha256": report["data_sha256"],
        "rows": int(len(df)),
        "splits": report["splits"],
        "class_balance": round(float(df[schema.TARGET_COLUMN].mean()), 4),
        "threshold": threshold,
        "risk_band_cutpoints": report["validation"]["band_cutpoints"],
        "typical_ranges": report["typical_ranges"],
        "metrics_summary": {
            "validation": report["validation"]["scores"][shipped],
            "test": report["test"]["scores"][shipped],
            "test_dummy": report["test"]["scores"]["dummy"],
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
    shipped = config.SHIPPED_MODEL
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
        "shipped_model": shipped,
        "seed": seed,
        "data_sha256": dataset_hash(df),
        "splits": splits.describe_splits(parts),
        "validation": fitted["validation"],
        "test": test_report,
        "quality_gate_enforced": enforce_gate,
        "typical_ranges": evaluate.typical_ranges(parts["train"]),
    }

    metadata = _build_metadata(report, df)
    model_path, meta_path, metadata = save_artifact(fitted["models"][shipped], metadata, artifact_dir)

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
    shipped = report["shipped_model"]
    scores = report["test"]["scores"]
    intervals = report["test"]["confidence_intervals"]
    print(f"Model version : {config.MODEL_VERSION}")
    print(f"Shipped model : {shipped} ({config.MODEL_LABELS[shipped]})")
    print(f"Artifact      : {outcome['model_path']}")
    print(f"Artifact hash : {outcome['metadata']['artifact_sha256']}")
    print(f"Threshold     : {report['validation']['thresholds'][shipped]:.4f} (chosen on validation)")
    for name in ("dummy", "baseline", "improved"):
        print(f"Test PR-AUC {name:9s}: {scores[name]['pr_auc']}")
    print(f"Shipped model PR-AUC 95% interval: {intervals[shipped]['pr_auc']}")
    print(f"Improved minus baseline PR-AUC (paired 95%): {report['test']['paired_difference']}")


if __name__ == "__main__":
    main()