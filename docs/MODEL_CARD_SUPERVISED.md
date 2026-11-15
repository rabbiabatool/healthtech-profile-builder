# Model Card: Supervised Appointment No-Show Predictor (Week 6 Final Capstone)

## Model Overview
- **Model Name**: HealthTech Appointment Attendance Risk Estimator
- **Model Version**: `v1.0.0-supervised`
- **Architecture**: Regularized Logistic Regression with Standard Scaler & One-Hot Categorical Encoding
- **Task**: Binary Classification (`0`: Attended, `1`: No-Show)
- **Primary Metrics**: Accuracy: `78.4%`, Precision: `74.2%`, Recall: `71.8%`, F1-score: `73.0%`, ROC-AUC: `0.825`
- **Threshold**: `0.217` (tuned for high sensitivity on missed appointments)

---

## Intended Use & Target Users
- **Primary Use**: Educational and operational demonstration for healthcare administration to illustrate how lead times and reminder notifications impact patient attendance.
- **Target Users**: Administrative clinic staff, schedulers, and healthcare technology developers.
- **Out-of-Scope & Prohibited Use**: **NOT A CLINICAL DIAGNOSTIC TOOL.** Under no circumstances should this model be used to deny clinical care, prioritize emergency interventions, or profile individual patients for insurance coverage.

---

## Input Features & Schema Boundaries

| Feature Name | Type | Unit / Range | Description |
| :--- | :--- | :--- | :--- |
| `age` | Integer | `[0, 120]` | Patient chronological age |
| `lead_time_days` | Integer | `[0, 365]` | Calendar days between scheduling and appointment |
| `scheduled_hour` | Integer | `[7, 19]` | Hour of day when appointment was booked (24h) |
| `day_of_week` | Categorical | `MON, TUE, WED, THU, FRI, SAT` | Day of scheduled appointment |
| `appointment_type` | Categorical | `CONSULTATION, FOLLOW_UP, PROCEDURE, LAB` | Care category |
| `reminder_sent` | Boolean | `True / False` | SMS / Email notification sent |
| `previous_appointments` | Integer | `[0, 100]` | Total historical booked appointments |
| `previous_no_shows` | Integer | `[0, 100]` | Total historical missed appointments |
| `distance_km` | Float | `[0.0, 300.0]` | Estimated travel distance to medical center |

---

## Training Data & Provenance
- **Dataset**: Synthetic clinic appointment dataset ($N = 10,000$ records) generated via reproducible probability distributions (`mlcore/data.py`).
- **Data Preprocessing**: Median imputation for missing continuous features, zero-imputation for distance where unknown, standard scaling, and one-hot encoding for categorical variables.
- **Cross-Validation**: 5-fold stratified cross-validation preserving class balance across splits.

---

## Calibration & Risk Bands
The raw model probability $p \in [0, 1]$ is mapped to 3 operational risk tiers based on validated empirical cutpoints:
- **LOW Risk**: $p < 0.20$ (Routine digital appointment reminder)
- **MEDIUM Risk**: $0.20 \le p < 0.45$ (Automated reminder SMS 24 hours in advance)
- **HIGH Risk**: $p \ge 0.45$ (Staff confirmation call and flexible rescheduling option)

---

## Limitations, Biases & Mitigation
1. **Synthetic Nature**: All training data is generated from parametric models. Does not account for sudden weather anomalies, regional transport strikes, or complex health disparities.
2. **Deterministic Fallbacks**: If model artifacts are corrupted or missing, the API fails closed with HTTP 503 (`ModelUnavailable`), preventing silent inference corruption.
3. **Non-Clinical Disclaimer**: Every model response mandates an explicit legal disclaimer: *"Educational prototype on synthetic data: not clinically validated and not medical advice."*
