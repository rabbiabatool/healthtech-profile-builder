"""Preprocessing and models. Each model is ONE Pipeline: preprocessing + estimator,
so the two are always saved, loaded and applied together."""
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
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


def build_random_forest(n_estimators=100, max_depth=None, min_samples_split=2, seed=config.SEED):
    """Random Forest classifier with median imputation, scaling, and one-hot encoding."""
    return Pipeline([
        ("prep", build_baseline_preprocessor()),
        (
            "model",
            RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=min_samples_split,
                random_state=seed,
                n_jobs=-1,
            ),
        ),
    ])


def build_tree_preprocessor():
    """Gradient boosting needs no scaling and handles empty values itself."""
    return ColumnTransformer(
        [
            ("numeric", "passthrough", schema.NUMERIC_FEATURES),
            (
                "categorical",
                OrdinalEncoder(categories=_category_lists(), handle_unknown="error"),
                schema.CATEGORICAL_FEATURES,
            ),
            ("boolean", "passthrough", schema.BOOLEAN_FEATURES),
        ],
        remainder="drop",
    )


def make_calibration_folds(y, groups, seed=config.SEED, n_splits=3):
    """Patient-grouped folds, so no patient is on both sides of a calibration fold."""
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return list(splitter.split(np.zeros((len(y), 1)), y, groups))


def build_improved(learning_rate=0.1, max_leaf_nodes=31, seed=config.SEED, calibration_folds=None):
    first_category = len(schema.NUMERIC_FEATURES)
    category_positions = list(range(first_category, first_category + len(schema.CATEGORICAL_FEATURES)))
    booster = HistGradientBoostingClassifier(
        learning_rate=learning_rate,
        max_leaf_nodes=max_leaf_nodes,
        max_iter=200,
        l2_regularization=1.0,
        categorical_features=category_positions,
        early_stopping=False,
        random_state=seed,
    )
    if calibration_folds is not None:
        booster = CalibratedClassifierCV(estimator=booster, method="sigmoid", cv=calibration_folds)
    return Pipeline([("prep", build_tree_preprocessor()), ("model", booster)])
