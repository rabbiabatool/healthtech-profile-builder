"""Preprocessing and models. Each model is ONE Pipeline: preprocessing + estimator,
so the two are always saved, loaded and applied together."""
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from mlcore import config, schema


def select_features(df):
    """The allowlist: only these columns can ever reach a model."""
    return df[schema.FEATURE_COLUMNS].copy()


def _category_lists():
    return [schema.CATEGORICAL_VALUES[name] for name in schema.CATEGORICAL_FEATURES]


def build_dummy():
    """The floor: always predicts the base no-show rate it saw in training."""
    return Pipeline([("model", DummyClassifier(strategy="prior"))])


def build_baseline_preprocessor():
    numeric = Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
    ])
    return ColumnTransformer(
        [
            ("numeric", numeric, schema.NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(categories=_category_lists(), handle_unknown="error", sparse_output=False),
                schema.CATEGORICAL_FEATURES,
            ),
            ("boolean", "passthrough", schema.BOOLEAN_FEATURES),
        ],
        remainder="drop",
    )


def build_baseline(C=1.0, seed=config.SEED):
    return Pipeline([
        ("prep", build_baseline_preprocessor()),
        ("model", LogisticRegression(C=C, max_iter=1000, random_state=seed)),
    ])