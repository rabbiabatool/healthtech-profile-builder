# Model card: no-show likelihood (noshow-1.0.0)

> Educational prototype trained on synthetic data. Not clinically validated, not medical advice, and not for decisions about anyone's care.

## Intended use
A teaching example of a scheduling-operations model: estimating how likely a fictional appointment is to be a no-show. It is not a medical model and never predicts illness.

## Not intended for
Clinical decisions, decisions about anyone's care, real patients, or any use that treats the probability as a fact about a person.

## Shipped model
Logistic Regression (baseline): LogisticRegression inside one scikit-learn Pipeline (median imputation with a missing flag, scaling, one-hot encoding).

## Data
Synthetic appointments, data version `synthetic-appointments-1.0.0`, seed 42, SHA-256 `e86a485d5b11cb669df9c2c0e09496edaf29f4f7a557868e2542c876ad4f377b`. See DATA_CARD.md. Splits keep every patient in one split only.

| Split | Rows | Patients | No-show rate |
|---|---|---|---|
| train | 11998 | 3466 | 0.199 |
| validation | 4002 | 1152 | 0.1992 |
| test | 4000 | 1147 | 0.199 |

## Models compared (test set, scored once at the end)
Hyperparameters and thresholds were chosen on the validation set. Intervals are 95% bootstrap ranges that resample whole patients.

| Model | PR-AUC (95% CI) | ROC-AUC (95% CI) | Brier | Log loss |
|---|---|---|---|---|
| Dummy (always the base rate) | 0.199 | 0.5 | 0.1594 | 0.499 |
| Logistic Regression (baseline) **(shipped)** | 0.3111 (0.2832 to 0.3453) | 0.6384 (0.6166 to 0.6601) | 0.1527 | 0.4794 |
| Gradient Boosting + calibration (improved) | 0.3047 (0.2778 to 0.3378) | 0.6302 (0.6086 to 0.6522) | 0.1533 | 0.4809 |

On the test set the improved model's PR-AUC is 0.0064 lower than the baseline's. The paired 95% interval for improved minus baseline is -0.018 to 0.006. It includes zero, so the two models are statistically tied on this test set.

## Model choice
Logistic Regression was chosen as the shipped model after the comparison. The gradient boosting challenger did not clearly beat it (see the paired comparison in the model card), so the simpler, faster and more explainable model was preferred. This choice was made after the test results had been seen, so the shipped model's test scores may be very slightly optimistic; the two models were within noise of each other.

## Operating point (threshold chosen on validation)
Lift is precision divided by the base no-show rate: 1.0 means no better than flagging at random.

| Model | Threshold | Precision | Recall | F1 | Share flagged | Lift |
|---|---|---|---|---|---|---|
| baseline | 0.2167 | 0.2892 | 0.5075 | 0.3684 | 0.3493 | 1.45 |
| improved | 0.1981 | 0.2766 | 0.5653 | 0.3714 | 0.4068 | 1.39 |

## Risk bands (shipped model)
HIGH at or above 0.2167 (the operating threshold). MEDIUM at or above 0.1508, the validation 35th percentile of scores. Otherwise LOW. The observed no-show rate should rise from LOW to HIGH:

| Band | Test rows | Share | Observed no-show rate |
|---|---|---|---|
| LOW | 1414 | 0.3535 | 0.1216 |
| MEDIUM | 1189 | 0.2973 | 0.185 |
| HIGH | 1397 | 0.3493 | 0.2892 |

## If staff can only act on the top X% of appointments (shipped model)
| Flag top | Appointments flagged | Precision | Recall | Lift |
|---|---|---|---|---|
| 10% | 400 | 0.37 | 0.1859 | 1.8593 |
| 20% | 800 | 0.3162 | 0.3178 | 1.5892 |
| 30% | 1200 | 0.3 | 0.4523 | 1.5075 |

## What drives the predictions
Logistic Regression weights (largest first). An odds ratio above 1 raises the estimated no-show likelihood. Numeric features are standardised, so their odds ratio is per one standard deviation. These describe the model, not real-world causes.

| Feature | Coefficient | Odds ratio |
|---|---|---|
| reminder_sent | -0.6301 | 0.5326 |
| appointment_type_LAB_TEST | -0.4407 | 0.6436 |
| previous_no_shows | 0.3543 | 1.4252 |
| day_of_week_THU | -0.3394 | 0.7122 |
| appointment_type_VACCINATION | -0.2712 | 0.7624 |
| day_of_week_WED | -0.2081 | 0.8121 |
| day_of_week_TUE | -0.1708 | 0.843 |
| appointment_type_FOLLOW_UP | -0.1633 | 0.8494 |

Permutation importance on the validation set (how much PR-AUC drops when a feature is shuffled):

| Feature | Mean drop in PR-AUC |
|---|---|
| previous_no_shows | 0.0809 |
| reminder_sent | 0.0528 |
| lead_time_days | 0.0156 |
| appointment_type | 0.0151 |
| distance_km | 0.0104 |

## Calibration
See `figures/calibration.png`. Points near the diagonal mean the predicted probabilities are close to the observed no-show rates.

## Error analysis (shipped model)
At the chosen threshold the model missed 392 no-shows (false negatives) and raised 993 false alarms (false positives) on the test set. `metrics.json` lists which appointment types, weekdays and reminder statuses these errors cluster in. See `figures/confusion_matrix.png`.

## Performance by slice (shipped model, test set)
Slices with fewer than 100 rows show n/a for PR-AUC.

| Slice | Value | Rows | No-show rate | PR-AUC | Precision | Recall |
|---|---|---|---|---|---|---|
| age_band | 18-29 | 621 | 0.2512 | 0.3683 | 0.3028 | 0.6346 |
| age_band | 30-44 | 1140 | 0.2105 | 0.3413 | 0.3105 | 0.5667 |
| age_band | 45-59 | 1445 | 0.1862 | 0.2767 | 0.2893 | 0.4721 |
| age_band | 60-95 | 794 | 0.165 | 0.2493 | 0.2176 | 0.3206 |
| lead_time_bucket | 0-7 | 585 | 0.1829 | 0.2582 | 0.2483 | 0.3458 |
| lead_time_bucket | 8-30 | 1881 | 0.1866 | 0.2699 | 0.2746 | 0.4131 |
| lead_time_bucket | 31-90 | 1437 | 0.2129 | 0.3563 | 0.3021 | 0.6438 |
| lead_time_bucket | 91-180 | 97 | 0.3299 | n/a | 0.3676 | 0.7812 |
| appointment_type | CHECKUP | 984 | 0.2012 | 0.2858 | 0.2755 | 0.5455 |
| appointment_type | FOLLOW_UP | 1179 | 0.2231 | 0.3568 | 0.3235 | 0.4563 |
| appointment_type | LAB_TEST | 613 | 0.1501 | 0.2465 | 0.2294 | 0.2717 |
| appointment_type | SPECIALIST | 626 | 0.2093 | 0.3544 | 0.2671 | 0.687 |
| appointment_type | VACCINATION | 598 | 0.1873 | 0.3086 | 0.3245 | 0.5446 |
| distance | missing | 327 | 0.1957 | 0.2707 | 0.2991 | 0.5469 |
| distance | present | 3673 | 0.1993 | 0.3162 | 0.2883 | 0.5041 |

## Imbalance and fairness
About one appointment in five is a no-show, so accuracy alone would mislead; PR-AUC is the primary metric. Age is a model input and a fairness risk, so metrics are reported by age band. Gender, ethnicity, religion, disability and neighbourhood are not used.

## Limitations
- Trained on synthetic data whose labels come from invented rules, so the metrics measure how well the model recovers those rules, not real-world performance.
- Not clinically validated, not medical advice, and not for decisions about anyone's care.
- Age and history effects are assumptions and could cause unfair outcomes if used to overbook or deprioritise people.
- No drift monitoring, no retraining service and no rate limiting on the prediction endpoint.

## Reproduce
From the `backend` folder: `python -m mlcore.train`. Library versions are pinned in `requirements-ml.txt` and recorded in the artifact metadata.
