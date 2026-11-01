"""Central settings for the ML code. Nothing in mlcore imports Django."""
from pathlib import Path

SEED = 42

DATA_VERSION = "synthetic-appointments-1.0.0"
N_PATIENTS = 6000
N_APPOINTMENTS = 20000
TARGET_NO_SHOW_RATE = 0.20
LABEL_FLIP_RATE = 0.03
DISTANCE_MISSING_RATE = 0.08

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "ml_data"
ARTIFACT_DIR = BACKEND_DIR / "ml_artifacts"
DOCS_ML_DIR = REPO_DIR / "docs" / "ml"
EDA_DIR = DOCS_ML_DIR / "eda"

DISCLAIMER = (
    "Educational prototype trained on synthetic data. Not clinically validated, "
    "not medical advice, and not for decisions about anyone's care."
)


# --- Added in Phase 10 -----------------------------------------------------
MODEL_NAME = "noshow"
MODEL_VERSION = "noshow-1.0.0"
SCHEMA_VERSION = "v1"
ARTIFACT_FILENAME = f"{MODEL_VERSION}.joblib"
METADATA_FILENAME = f"{MODEL_VERSION}.meta.json"
SUPERVISED_COMPARISON_FILENAME = "supervised_comparison.json"
BOOTSTRAP_ROUNDS = 1000
MEDIUM_BAND_FRACTION = 0.5
LOW_BAND_QUANTILE = 0.35

LIMITATIONS = [
    "Trained on synthetic data whose labels come from invented rules, so the metrics measure how well the model recovers those rules, not real-world performance.",
    "Not clinically validated, not medical advice, and not for decisions about anyone's care.",
    "Age and history effects are assumptions and could cause unfair outcomes if used to overbook or deprioritise people.",
    "No drift monitoring, no retraining service and no rate limiting on the prediction endpoint.",
]


# --- Phase 10.2 & Week 4: which model is shipped and model taxonomy --------
SHIPPED_MODEL = "baseline"

MODEL_LABELS = {
    "dummy": "Dummy (always the base rate)",
    "baseline": "Logistic Regression (baseline)",
    "random_forest": "Random Forest (bagging ensemble)",
    "improved": "HistGradientBoosting + calibration (boosting)",
    "tuned_rf": "Tuned Random Forest (GridSearchCV)",
}

MODEL_TYPES = {
    "baseline": "LogisticRegression inside one scikit-learn Pipeline (median imputation with a missing flag, scaling, one-hot encoding)",
    "random_forest": "RandomForestClassifier inside one scikit-learn Pipeline (median imputation, scaling, one-hot encoding)",
    "improved": "HistGradientBoostingClassifier with sigmoid calibration, inside one scikit-learn Pipeline",
    "tuned_rf": "RandomForestClassifier tuned with StratifiedGroupKFold GridSearchCV inside one scikit-learn Pipeline",
}

SHIPPED_MODEL_REASON = (
    "Logistic Regression was chosen as the shipped model after the comparison. The gradient boosting "
    "challenger did not clearly beat it (see the paired comparison in the model card), so the simpler, "
    "faster and more explainable model was preferred. This choice was made after the test results had "
    "been seen, so the shipped model's test scores may be very slightly optimistic; the two models were "
    "within noise of each other."
)
