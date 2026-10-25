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

from mlcore import config


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


def risk_band(probability, threshold):
    if probability >= threshold:
        return "HIGH"
    if probability >= threshold * config.MEDIUM_BAND_FRACTION:
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