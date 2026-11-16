"""Group-aware, stratified train/validation/test split (about 60/20/20)."""
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from mlcore import config, schema

GROUP_COLUMN = "patient_ref"


def make_splits(df, seed=config.SEED):
    y = df[schema.TARGET_COLUMN].to_numpy()
    groups = df[GROUP_COLUMN].to_numpy()
    placeholder = np.zeros((len(df), 1))

    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    trainval_pos, test_pos = next(outer.split(placeholder, y, groups))

    inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=seed)
    train_rel, val_rel = next(
        inner.split(placeholder[trainval_pos], y[trainval_pos], groups[trainval_pos])
    )

    return {
        "train": df.iloc[trainval_pos[train_rel]].reset_index(drop=True),
        "validation": df.iloc[trainval_pos[val_rel]].reset_index(drop=True),
        "test": df.iloc[test_pos].reset_index(drop=True),
    }


def assert_no_patient_overlap(parts):
    names = list(parts)
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            shared = set(parts[first][GROUP_COLUMN]) & set(parts[second][GROUP_COLUMN])
            if shared:
                raise ValueError(f"{len(shared)} patients appear in both {first} and {second}")


def describe_splits(parts):
    return {
        name: {
            "rows": int(len(frame)),
            "patients": int(frame[GROUP_COLUMN].nunique()),
            "no_show_rate": round(float(frame[schema.TARGET_COLUMN].mean()), 4),
        }
        for name, frame in parts.items()
    }
