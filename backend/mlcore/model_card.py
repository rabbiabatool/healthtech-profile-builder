"""Builds docs/ml/MODEL_CARD.md from the metrics report, so numbers are never typed by hand."""
from mlcore import config


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def _ci(intervals, metric):
    interval = (intervals or {}).get(metric)
    return "n/a" if not interval else f"{interval['low']} to {interval['high']}"


def render(report):
    val = report["validation"]
    test = report["test"]
    scores = test["scores"]
    ci = test["confidence_intervals"]
    threshold = val["thresholds"]["improved"]

    split_rows = [[n, s["rows"], s["patients"], s["no_show_rate"]] for n, s in report["splits"].items()]

    model_rows = []
    for key, label in (
        ("dummy", "Dummy (always the base rate)"),
        ("baseline", "Logistic Regression (baseline)"),
        ("improved", "Gradient Boosting + calibration (improved)"),
    ):
        s = scores[key]
        intervals = ci.get(key)
        if intervals:
            pr = f"{s['pr_auc']} ({_ci(intervals, 'pr_auc')})"
            roc = f"{s['roc_auc']} ({_ci(intervals, 'roc_auc')})"
        else:
            pr, roc = s["pr_auc"], s["roc_auc"]
        model_rows.append([label, pr, roc, s["brier"], s["log_loss"]])

    base_ci = ci["baseline"]["pr_auc"]
    new_ci = ci["improved"]["pr_auc"]
    gain = round(scores["improved"]["pr_auc"] - scores["baseline"]["pr_auc"], 4)
    if base_ci and new_ci and new_ci["low"] > base_ci["high"]:
        verdict = "The 95% intervals do not overlap, so the improvement looks real on this synthetic data."
    else:
        verdict = "The 95% intervals overlap, so the difference may not be meaningful."

    operating_rows = []
    for key in ("baseline", "improved"):
        o = test["operating_point"][key]
        operating_rows.append([key, round(o["threshold"], 4), o["precision"], o["recall"], o["f1"], o["flagged_share"]])

    slice_rows = [
        [r["slice"], r["value"], r["n"], r["no_show_rate"], r["pr_auc"] if r["pr_auc"] is not None else "n/a",
         r["precision"], r["recall"]]
        for r in test["slices"]
    ]
    importance_rows = [[r["feature"], r["mean_drop_in_pr_auc"]] for r in val["permutation_importance"][:5]]
    errors = test["errors"]

    lines = [
        f"# Model card: no-show likelihood ({config.MODEL_VERSION})",
        "",
        f"> {config.DISCLAIMER}",
        "",
        "## Intended use",
        "A teaching example of a scheduling-operations model: estimating how likely a fictional "
        "appointment is to be a no-show. It is not a medical model and never predicts illness.",
        "",
        "## Not intended for",
        "Clinical decisions, decisions about anyone's care, real patients, or any use that "
        "treats the probability as a fact about a person.",
        "",
        "## Data",
        f"Synthetic appointments, data version `{report['data_version']}`, seed {report['seed']}, "
        f"SHA-256 `{report['data_sha256']}`. See DATA_CARD.md. Splits keep every patient in one split only.",
        "",
        _table(["Split", "Rows", "Patients", "No-show rate"], split_rows),
        "",
        "## Models compared (test set, scored once at the end)",
        "Hyperparameters and thresholds were chosen on the validation set. "
        "Intervals are 95% bootstrap ranges that resample whole patients.",
        "",
        _table(["Model", "PR-AUC (95% CI)", "ROC-AUC (95% CI)", "Brier", "Log loss"], model_rows),
        "",
        f"The improved model's PR-AUC is {gain} higher than the baseline. {verdict}",
        "",
        "## Operating point (threshold chosen on validation)",
        _table(["Model", "Threshold", "Precision", "Recall", "F1", "Share flagged"], operating_rows),
        "",
        f"Risk bands for the improved model: HIGH at or above {round(threshold, 4)}, "
        f"MEDIUM at or above {round(threshold * config.MEDIUM_BAND_FRACTION, 4)}, otherwise LOW.",
        "",
        "## Calibration",
        "See `figures/calibration.png`. Points near the diagonal mean the predicted probabilities "
        "are close to the observed no-show rates.",
        "",
        "## Error analysis",
        f"At the chosen threshold the improved model missed {errors['false_negatives']} no-shows "
        f"(false negatives) and raised {errors['false_positives']} false alarms (false positives) "
        "on the test set. `metrics.json` lists which appointment types, weekdays and reminder "
        "statuses these errors cluster in. See `figures/confusion_matrix.png`.",
        "",
        "Features the model relies on most (validation permutation importance; describes the model's "
        "behaviour, not real-world causes):",
        "",
        _table(["Feature", "Mean drop in PR-AUC"], importance_rows),
        "",
        "## Performance by slice (improved model, test set)",
        "Slices with fewer than 100 rows show n/a for PR-AUC.",
        "",
        _table(["Slice", "Value", "Rows", "No-show rate", "PR-AUC", "Precision", "Recall"], slice_rows),
        "",
        "## Imbalance and fairness",
        "About one appointment in five is a no-show, so accuracy alone would mislead; PR-AUC is the "
        "primary metric. Age is a model input and a fairness risk, so metrics are reported by age band. "
        "Gender, ethnicity, religion, disability and neighbourhood are not used.",
        "",
        "## Limitations",
    ]
    lines += [f"- {item}" for item in config.LIMITATIONS]
    lines += [
        "",
        "## Reproduce",
        "From the `backend` folder: `python -m mlcore.train`. Library versions are pinned in "
        "`requirements-ml.txt` and recorded in the artifact metadata.",
        "",
    ]
    return "\n".join(lines)


def write(report, path):
    path.write_text(render(report), encoding="utf-8")