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