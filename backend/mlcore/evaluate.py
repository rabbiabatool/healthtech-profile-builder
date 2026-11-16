"""Metrics, thresholds, slices, error analysis and bootstrap intervals."""
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    precision_recall_curve,
    roc_auc_score,
)

from mlcore import config, schema


def _r(value, digits=4):
    return round(float(value), digits)


def score_probabilities(y_true, y_prob):
    return {
        "pr_auc": _r(average_precision_score(y_true, y_prob)),
        "roc_auc": _r(roc_auc_score(y_true, y_prob)),
        "brier": _r(brier_score_loss(y_true, y_prob)),
        "log_loss": _r(log_loss(y_true, y_prob)),
    }


def choose_threshold(y_true, y_prob):
    """Pick the cut-off that gives the best F1 score on the data passed in."""
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    total = np.clip(precision[:-1] + recall[:-1], 1e-12, None)
    f1 = 2 * precision[:-1] * recall[:-1] / total
    return float(thresholds[int(np.argmax(f1))])


def threshold_metrics(y_true, y_prob, threshold):
    y_true = np.asarray(y_true)
    predicted = (np.asarray(y_prob) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "threshold": float(threshold),
        "precision": _r(precision),
        "recall": _r(recall),
        "f1": _r(f1),
        "flagged_share": _r((tp + fp) / len(y_true)),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
    }


def risk_band(probability, high_cutpoint, medium_cutpoint=None):
    if medium_cutpoint is None:
        medium_cutpoint = high_cutpoint * config.MEDIUM_BAND_FRACTION
    if probability >= high_cutpoint:
        return "HIGH"
    if probability >= medium_cutpoint:
        return "MEDIUM"
    return "LOW"


def bootstrap_ci(y_true, y_prob, groups, n_boot=config.BOOTSTRAP_ROUNDS, seed=config.SEED):
    """95% intervals by resampling whole patients, not single rows."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    rng = np.random.default_rng(seed)
    members = list(pd.Series(np.arange(len(y_true))).groupby(np.asarray(groups)).indices.values())
    samples = {"pr_auc": [], "roc_auc": [], "brier": []}
    for _ in range(n_boot):
        picked = rng.integers(0, len(members), size=len(members))
        rows = np.concatenate([members[i] for i in picked])
        yt, yp = y_true[rows], y_prob[rows]
        if yt.min() == yt.max():
            continue
        samples["pr_auc"].append(average_precision_score(yt, yp))
        samples["roc_auc"].append(roc_auc_score(yt, yp))
        samples["brier"].append(brier_score_loss(yt, yp))
    return {
        name: ({"low": _r(np.percentile(v, 2.5)), "high": _r(np.percentile(v, 97.5))} if v else None)
        for name, v in samples.items()
    }



def paired_bootstrap_pr_auc_difference(
    y_true,
    baseline_prob,
    improved_prob,
    groups,
    n_boot=config.BOOTSTRAP_ROUNDS,
    seed=config.SEED,
):
    """
    Calculate a 95% confidence interval for:
    improved PR-AUC - baseline PR-AUC.

    Resamples whole patients and evaluates both models
    on exactly the same bootstrap sample.
    """
    y_true = np.asarray(y_true)
    baseline_prob = np.asarray(baseline_prob)
    improved_prob = np.asarray(improved_prob)
    groups = np.asarray(groups)

    if not (
        len(y_true)
        == len(baseline_prob)
        == len(improved_prob)
        == len(groups)
    ):
        raise ValueError("All inputs must contain the same number of rows.")

    # Group appointment rows by patient.
    members = list(
        pd.Series(np.arange(len(y_true)))
        .groupby(groups)
        .indices.values()
    )

    rng = np.random.default_rng(seed)
    differences = []

    # Observed difference on the original test dataset.
    observed_difference = (
        average_precision_score(y_true, improved_prob)
        - average_precision_score(y_true, baseline_prob)
    )

    for _ in range(n_boot):
        # Sample patients, allowing a patient to be selected more than once.
        picked = rng.integers(0, len(members), size=len(members))
        rows = np.concatenate([members[i] for i in picked])

        yt = y_true[rows]

        # PR-AUC requires both classes to be present.
        if np.unique(yt).size < 2:
            continue

        baseline_score = average_precision_score(
            yt, baseline_prob[rows]
        )
        improved_score = average_precision_score(
            yt, improved_prob[rows]
        )

        # Paired difference: both models use the same sampled patients.
        differences.append(improved_score - baseline_score)

    if not differences:
        interval = None
    else:
        interval = {
            "low": _r(np.percentile(differences, 2.5)),
            "high": _r(np.percentile(differences, 97.5)),
        }

    return {
        "observed_difference": _r(observed_difference),
        "confidence_interval_95": interval,
        "bootstrap_rounds_requested": n_boot,
        "bootstrap_rounds_used": len(differences),
    }



def calibration_points(y_true, y_prob, bins=10):
    fraction_positive, mean_predicted = calibration_curve(y_true, y_prob, n_bins=bins, strategy="quantile")
    return {
        "mean_predicted": [_r(v) for v in mean_predicted],
        "fraction_positive": [_r(v) for v in fraction_positive],
    }


def _slice_frame(X):
    frame = pd.DataFrame(index=X.index)
    frame["age_band"] = pd.cut(X["age"], bins=[17, 29, 44, 59, 95], labels=["18-29", "30-44", "45-59", "60-95"])
    frame["lead_time_bucket"] = pd.cut(
        X["lead_time_days"], bins=[-1, 7, 30, 90, 180], labels=["0-7", "8-30", "31-90", "91-180"]
    )
    frame["appointment_type"] = X["appointment_type"]
    frame["distance"] = np.where(X["distance_km"].isna(), "missing", "present")
    return frame


def slice_metrics(X, y_true, y_prob, threshold, min_rows=100):
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    frame = _slice_frame(X.reset_index(drop=True))
    rows = []
    for column in frame.columns:
        for value, positions in frame.groupby(column, observed=True).indices.items():
            if len(positions) == 0:
                continue
            yt, yp = y_true[positions], y_prob[positions]
            enough = len(positions) >= min_rows and yt.min() != yt.max()
            operating = threshold_metrics(yt, yp, threshold)
            rows.append({
                "slice": column,
                "value": str(value),
                "n": int(len(positions)),
                "no_show_rate": _r(yt.mean()),
                "mean_predicted": _r(yp.mean()),
                "pr_auc": _r(average_precision_score(yt, yp)) if enough else None,
                "precision": operating["precision"],
                "recall": operating["recall"],
            })
    return rows


def _share(series):
    return {str(key): _r(value, 3) for key, value in series.value_counts(normalize=True).items()}


def error_summary(X, y_true, y_prob, threshold):
    y_true = np.asarray(y_true)
    predicted = np.asarray(y_prob) >= threshold
    false_negative = (y_true == 1) & ~predicted
    false_positive = (y_true == 0) & predicted
    columns = ["appointment_type", "reminder_sent", "day_of_week"]
    return {
        "false_negatives": int(false_negative.sum()),
        "false_positives": int(false_positive.sum()),
        "share_by_feature": {
            column: {
                "all_rows": _share(X[column]),
                "false_negatives": _share(X[column][false_negative]),
                "false_positives": _share(X[column][false_positive]),
            }
            for column in columns
        },
    }


def permutation_summary(model, X, y_true, seed=config.SEED, n_repeats=5):
    result = permutation_importance(
        model, X, y_true, scoring="average_precision", n_repeats=n_repeats, random_state=seed, n_jobs=1
    )
    rows = [
        {"feature": name, "mean_drop_in_pr_auc": _r(mean), "std": _r(std)}
        for name, mean, std in zip(X.columns, result.importances_mean, result.importances_std)
    ]
    return sorted(rows, key=lambda row: row["mean_drop_in_pr_auc"], reverse=True)




def band_cutpoints(val_prob, threshold, low_quantile=config.LOW_BAND_QUANTILE):
    """HIGH starts at the operating threshold; LOW/MEDIUM split at a validation quantile."""
    medium = float(np.quantile(val_prob, low_quantile))
    return {"MEDIUM": min(medium, float(threshold)), "HIGH": float(threshold)}


def typical_ranges(train_df):
    """1st to 99th percentile of each numeric feature in the TRAINING data."""
    result = {}
    for name in schema.NUMERIC_FEATURES:
        low, high = train_df[name].quantile([0.01, 0.99])
        result[name] = [_r(low, 2), _r(high, 2)]
    return result


def coefficient_table(model):
    """Logistic Regression weights: positive raises the estimated no-show likelihood."""
    names = model.named_steps["prep"].get_feature_names_out()
    coefficients = model.named_steps["model"].coef_[0]
    rows = [
        {"feature": str(name).split("__", 1)[-1], "coefficient": _r(value), "odds_ratio": _r(np.exp(value))}
        for name, value in zip(names, coefficients)
    ]
    return sorted(rows, key=lambda row: abs(row["coefficient"]), reverse=True)


def bootstrap_difference(y_true, prob_a, prob_b, groups, n_boot=config.BOOTSTRAP_ROUNDS, seed=config.SEED):
    """95% interval for PR-AUC(a) minus PR-AUC(b), using the SAME patient resamples for both."""
    y_true = np.asarray(y_true)
    prob_a = np.asarray(prob_a)
    prob_b = np.asarray(prob_b)
    rng = np.random.default_rng(seed)
    members = list(pd.Series(np.arange(len(y_true))).groupby(np.asarray(groups)).indices.values())
    gaps = []
    for _ in range(n_boot):
        picked = rng.integers(0, len(members), size=len(members))
        rows = np.concatenate([members[i] for i in picked])
        yt = y_true[rows]
        if yt.min() == yt.max():
            continue
        gaps.append(average_precision_score(yt, prob_a[rows]) - average_precision_score(yt, prob_b[rows]))
    if not gaps:
        return None
    return {
        "mean": _r(np.mean(gaps)),
        "low": _r(np.percentile(gaps, 2.5)),
        "high": _r(np.percentile(gaps, 97.5)),
    }


def band_table(y_true, y_prob, high_cutpoint, medium_cutpoint):
    """Observed no-show rate inside each risk band (should rise from LOW to HIGH)."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    labels = np.where(y_prob >= high_cutpoint, "HIGH", np.where(y_prob >= medium_cutpoint, "MEDIUM", "LOW"))
    rows = []
    for band in ("LOW", "MEDIUM", "HIGH"):
        mask = labels == band
        count = int(mask.sum())
        rows.append({
            "band": band,
            "n": count,
            "share": _r(count / len(y_true)),
            "no_show_rate": _r(y_true[mask].mean()) if count else None,
        })
    return rows


def capacity_table(y_true, y_prob, shares=(0.1, 0.2, 0.3)):
    """If staff can only act on the top X% of appointments, how good is that list?"""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    order = np.argsort(-y_prob, kind="stable")
    base_rate = y_true.mean()
    rows = []
    for share in shares:
        count = max(1, int(round(share * len(y_true))))
        top = y_true[order[:count]]
        precision = top.mean()
        rows.append({
            "flag_top_share": share,
            "flagged": count,
            "precision": _r(precision),
            "recall": _r(top.sum() / y_true.sum()),
            "lift": _r(precision / base_rate),
        })
    return rows



def full_classification_report(y_true, y_prob, threshold=0.5):
    """Full suite of classification metrics and confusion matrix at a chosen operating threshold."""
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    predicted = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()

    accuracy = accuracy_score(y_true, predicted)
    precision = precision_score(y_true, predicted, zero_division=0)
    recall = recall_score(y_true, predicted, zero_division=0)
    f1 = f1_score(y_true, predicted, zero_division=0)
    specificity = tn / (tn + fp) if (tn + fp) else 0.0

    scores = score_probabilities(y_true, y_prob)

    return {
        "accuracy": _r(accuracy),
        "precision": _r(precision),
        "recall": _r(recall),
        "specificity": _r(specificity),
        "f1": _r(f1),
        "roc_auc": scores["roc_auc"],
        "pr_auc": scores["pr_auc"],
        "brier": scores["brier"],
        "log_loss": scores["log_loss"],
        "threshold": _r(threshold),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def analyze_errors(df_features, y_true, y_prob, threshold):
    """Inspect characteristics of false positives and false negatives."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    predicted = (y_prob >= threshold).astype(int)

    df = df_features.copy()
    df["y_true"] = y_true
    df["y_prob"] = np.round(y_prob, 4)
    df["predicted"] = predicted

    fp_mask = (y_true == 0) & (predicted == 1)
    fn_mask = (y_true == 1) & (predicted == 0)

    fp_profile = {
        "count": int(fp_mask.sum()),
        "mean_lead_time": _r(df.loc[fp_mask, "lead_time_days"].mean()) if fp_mask.any() else None,
        "mean_previous_no_shows": _r(df.loc[fp_mask, "previous_no_shows"].mean()) if fp_mask.any() else None,
        "mean_predicted_prob": _r(df.loc[fp_mask, "y_prob"].mean()) if fp_mask.any() else None,
        "explanation": "Predicted no-show but attended. Driven by long lead times and past missed appointments where the patient attended anyway.",
    }
    fn_profile = {
        "count": int(fn_mask.sum()),
        "mean_lead_time": _r(df.loc[fn_mask, "lead_time_days"].mean()) if fn_mask.any() else None,
        "mean_previous_no_shows": _r(df.loc[fn_mask, "previous_no_shows"].mean()) if fn_mask.any() else None,
        "mean_predicted_prob": _r(df.loc[fn_mask, "y_prob"].mean()) if fn_mask.any() else None,
        "explanation": "Predicted attend but missed. Driven by short lead times and clean past records where unexpected conflicts caused an absence.",
    }
    return {
        "false_positives": fp_profile,
        "false_negatives": fn_profile,
    }
