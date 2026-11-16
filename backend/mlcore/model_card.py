"""Builds docs/ml/MODEL_CARD.md from the metrics report, so numbers are never typed by hand."""
from mlcore import config


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def _ci(intervals, metric):
    interval = (intervals or {}).get(metric)
    return "n/a" if not interval else f"{interval['low']} to {interval['high']}"


def _comparison_text(scores, diff):
    gain = round(scores["improved"]["pr_auc"] - scores["baseline"]["pr_auc"], 4)
    direction = "higher" if gain >= 0 else "lower"
    text = f"On the test set the improved model's PR-AUC is {abs(gain)} {direction} than the baseline's."
    if not diff:
        return text + " A paired interval could not be computed."
    text += f" The paired 95% interval for improved minus baseline is {diff['low']} to {diff['high']}."
    if diff["low"] > 0:
        text += " It stays above zero, so the improvement looks real on this synthetic data."
    elif diff["high"] < 0:
        text += " It stays below zero, so the baseline is better on this synthetic data."
    else:
        text += " It includes zero, so the two models are statistically tied on this test set."
    return text


def render(report):
    shipped = report["shipped_model"]
    val = report["validation"]
    test = report["test"]
    scores = test["scores"]
    ci = test["confidence_intervals"]
    val["thresholds"][shipped]
    cuts = val["band_cutpoints"]
    base_rate = report["splits"]["test"]["no_show_rate"]

    split_rows = [[n, s["rows"], s["patients"], s["no_show_rate"]] for n, s in report["splits"].items()]

    model_rows = []
    for key in ("dummy", "baseline", "improved"):
        s = scores[key]
        intervals = ci.get(key)
        label = config.MODEL_LABELS[key] + (" **(shipped)**" if key == shipped else "")
        if intervals:
            pr = f"{s['pr_auc']} ({_ci(intervals, 'pr_auc')})"
            roc = f"{s['roc_auc']} ({_ci(intervals, 'roc_auc')})"
        else:
            pr, roc = s["pr_auc"], s["roc_auc"]
        model_rows.append([label, pr, roc, s["brier"], s["log_loss"]])

    operating_rows = []
    for key in ("baseline", "improved"):
        o = test["operating_point"][key]
        lift = round(o["precision"] / base_rate, 2)
        operating_rows.append(
            [key, round(o["threshold"], 4), o["precision"], o["recall"], o["f1"], o["flagged_share"], lift]
        )

    band_rows = [
        [b["band"], b["n"], b["share"], b["no_show_rate"] if b["no_show_rate"] is not None else "n/a"]
        for b in test["bands"]
    ]
    capacity_rows = [
        [f"{round(r['flag_top_share'] * 100)}%", r["flagged"], r["precision"], r["recall"], r["lift"]]
        for r in test["capacity"]
    ]
    slice_rows = [
        [r["slice"], r["value"], r["n"], r["no_show_rate"], r["pr_auc"] if r["pr_auc"] is not None else "n/a",
         r["precision"], r["recall"]]
        for r in test["slices"]
    ]
    coefficient_rows = [
        [r["feature"], r["coefficient"], r["odds_ratio"]] for r in val["baseline_coefficients"][:8]
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
        "## Shipped model",
        f"{config.MODEL_LABELS[shipped]}: {config.MODEL_TYPES[shipped]}.",
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
        _comparison_text(scores, test["paired_difference"]),
        "",
        "## Model choice",
        config.SHIPPED_MODEL_REASON,
        "",
        "## Operating point (threshold chosen on validation)",
        "Lift is precision divided by the base no-show rate: 1.0 means no better than flagging at random.",
        "",
        _table(["Model", "Threshold", "Precision", "Recall", "F1", "Share flagged", "Lift"], operating_rows),
        "",
        "## Risk bands (shipped model)",
        f"HIGH at or above {round(cuts['HIGH'], 4)} (the operating threshold). MEDIUM at or above "
        f"{round(cuts['MEDIUM'], 4)}, the validation 35th percentile of scores. Otherwise LOW. "
        "The observed no-show rate should rise from LOW to HIGH:",
        "",
        _table(["Band", "Test rows", "Share", "Observed no-show rate"], band_rows),
        "",
        "## If staff can only act on the top X% of appointments (shipped model)",
        _table(["Flag top", "Appointments flagged", "Precision", "Recall", "Lift"], capacity_rows),
        "",
        "## What drives the predictions",
        "Logistic Regression weights (largest first). An odds ratio above 1 raises the estimated no-show "
        "likelihood. Numeric features are standardised, so their odds ratio is per one standard deviation. "
        "These describe the model, not real-world causes.",
        "",
        _table(["Feature", "Coefficient", "Odds ratio"], coefficient_rows),
        "",
        "Permutation importance on the validation set (how much PR-AUC drops when a feature is shuffled):",
        "",
        _table(["Feature", "Mean drop in PR-AUC"], importance_rows),
        "",
        "## Calibration",
        "See `figures/calibration.png`. Points near the diagonal mean the predicted probabilities "
        "are close to the observed no-show rates.",
        "",
        "## Error analysis (shipped model)",
        f"At the chosen threshold the model missed {errors['false_negatives']} no-shows "
        f"(false negatives) and raised {errors['false_positives']} false alarms (false positives) "
        "on the test set. `metrics.json` lists which appointment types, weekdays and reminder "
        "statuses these errors cluster in. See `figures/confusion_matrix.png`.",
        "",
        "## Performance by slice (shipped model, test set)",
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
