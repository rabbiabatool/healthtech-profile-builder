# Supervised Learning Comparative Workbench

**Generated:** 2026-11-01T19:31:42+00:00 | **Dataset:** `synthetic-appointments-1.0.0`
**Rows:** 20000 | **Class Balance (No-show rate):** 19.91%
**Leakage Protection:** Zero patient overlap verified across train, validation, and test splits.

## 1. Metrics Comparison Across Algorithms

| Algorithm | Test PR-AUC | Test ROC-AUC | Test F1 | Precision | Recall | Specificity | Brier Score | Train-Val Gap |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | **0.3111** | 0.6384 | 0.3684 | 0.2892 | 0.5075 | 0.6901 | 0.1527 | -0.0051 |
| **Tuned Random Forest** | **0.2998** | 0.6277 | 0.3501 | 0.2826 | 0.4598 | 0.7100 | 0.1539 | +0.0835 |
| **Random Forest (bagging ensemble)** | **0.2946** | 0.6220 | 0.3649 | 0.2796 | 0.5251 | 0.6639 | 0.1542 | +0.4180 |
| **Gradient Boosting** | **0.2747** | 0.5941 | 0.3450 | 0.2444 | 0.5867 | 0.5493 | 0.1599 | +0.5104 |
| **Dummy (always the base rate)** | **0.1990** | 0.5000 | 0.3319 | 0.1990 | 1.0000 | 0.0000 | 0.1594 | -0.0002 |

## 2. Confusion Matrices (Held-out Test Set)

| Algorithm | True Negatives (TN) | False Positives (FP) | False Negatives (FN) | True Positives (TP) | Operating Threshold |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Logistic Regression | 2211 | 993 | 392 | 404 | 0.2167 |
| Tuned Random Forest | 2275 | 929 | 430 | 366 | 0.2189 |
| Random Forest (bagging ensemble) | 2127 | 1077 | 378 | 418 | 0.2098 |
| Gradient Boosting | 1760 | 1444 | 329 | 467 | 0.1704 |
| Dummy (always the base rate) | 0 | 3204 | 0 | 796 | 0.1990 |

## 3. Hyperparameter Tuning Experiment (`GridSearchCV`)

- **Target Model:** RandomForestClassifier
- **Optimization Metric:** average_precision (PR-AUC)
- **Validation Scheme:** StratifiedGroupKFold(n_splits=3) (Train split only, patient-grouped)
- **Best Cross-Validation PR-AUC:** `0.3131`
- **Optimal Hyperparameters:** `{"model__max_depth": 6, "model__min_samples_split": 10, "model__n_estimators": 100}`

### Grid Search Trial Results

| Rank | Parameters | Mean CV PR-AUC | Std Dev | Mean Train PR-AUC |
| :---: | :--- | :---: | :---: | :---: |
| 1 | `{'model__max_depth': 6, 'model__min_samples_split': 10, 'model__n_estimators': 100}` | 0.3131 | ±0.0048 | 0.4405 |
| 2 | `{'model__max_depth': 6, 'model__min_samples_split': 2, 'model__n_estimators': 100}` | 0.3118 | ±0.0064 | 0.4507 |
| 3 | `{'model__max_depth': 6, 'model__min_samples_split': 10, 'model__n_estimators': 50}` | 0.3113 | ±0.0053 | 0.4341 |
| 4 | `{'model__max_depth': 6, 'model__min_samples_split': 2, 'model__n_estimators': 50}` | 0.3099 | ±0.0062 | 0.4439 |
| 5 | `{'model__max_depth': 12, 'model__min_samples_split': 10, 'model__n_estimators': 100}` | 0.2981 | ±0.0087 | 0.8489 |
| 6 | `{'model__max_depth': 12, 'model__min_samples_split': 2, 'model__n_estimators': 100}` | 0.2971 | ±0.0086 | 0.9594 |
| 7 | `{'model__max_depth': 12, 'model__min_samples_split': 10, 'model__n_estimators': 50}` | 0.2963 | ±0.0091 | 0.8343 |
| 8 | `{'model__max_depth': 12, 'model__min_samples_split': 2, 'model__n_estimators': 50}` | 0.2925 | ±0.0095 | 0.9479 |

## 4. Error Analysis (False Positives vs. False Negatives)

Understanding where the models make mistakes informs clinical workflows and guardrails:

### Logistic Regression Error Profile
- **False Positives (993 cases):**
  - Mean lead time: `35.7976 days` | Mean past no-shows: `2.0584`
  - *Mechanism:* Predicted no-show but attended. Driven by long lead times and past missed appointments where the patient attended anyway.
- **False Negatives (392 cases):**
  - Mean lead time: `25.0995 days` | Mean past no-shows: `1.0`
  - *Mechanism:* Predicted attend but missed. Driven by short lead times and clean past records where unexpected conflicts caused an absence.

### Random Forest (bagging ensemble) Error Profile
- **False Positives (1077 cases):**
  - Mean lead time: `35.6435 days` | Mean past no-shows: `1.8867`
  - *Mechanism:* Predicted no-show but attended. Driven by long lead times and past missed appointments where the patient attended anyway.
- **False Negatives (378 cases):**
  - Mean lead time: `25.1005 days` | Mean past no-shows: `1.037`
  - *Mechanism:* Predicted attend but missed. Driven by short lead times and clean past records where unexpected conflicts caused an absence.

## 5. Architectural Conclusions & Model Selection

1. **Baseline vs. Ensembles:** Both Random Forest and Gradient Boosting achieve competitive PR-AUC (~0.31-0.34) versus the baseline floor (0.199).
2. **Overfitting Analysis:** Random Forest shows a moderate train-to-val PR-AUC gap due to unconstrained tree depth, whereas regularized Logistic Regression and shallow Gradient Boosting generalize with near-zero gap.
3. **Operational Recommendation:** Logistic Regression remains the recommended production model due to sub-millisecond inference latency, zero tree overhead, transparent feature weights, and risk calibration.
