import pytest

from mlcore import schema, splits
from mlcore.data_generation import generate_appointments


@pytest.fixture(scope="module")
def full_df():
    return generate_appointments()


@pytest.fixture(scope="module")
def parts(full_df):
    return splits.make_splits(full_df)


def test_no_patient_appears_in_two_splits(parts):
    splits.assert_no_patient_overlap(parts)


def test_overlap_check_actually_catches_overlap(full_df):
    with pytest.raises(ValueError):
        splits.assert_no_patient_overlap({"a": full_df.iloc[:50], "b": full_df.iloc[:50]})


def test_every_row_lands_in_exactly_one_split(full_df, parts):
    ids = [i for frame in parts.values() for i in frame["appointment_id"]]
    assert len(ids) == len(full_df)
    assert set(ids) == set(full_df["appointment_id"])


def test_split_sizes_are_close_to_60_20_20(full_df, parts):
    n = len(full_df)
    assert abs(len(parts["train"]) / n - 0.60) < 0.03
    assert abs(len(parts["validation"]) / n - 0.20) < 0.03
    assert abs(len(parts["test"]) / n - 0.20) < 0.03


def test_class_balance_is_similar_in_every_split(full_df, parts):
    overall = full_df[schema.TARGET_COLUMN].mean()
    for frame in parts.values():
        assert abs(frame[schema.TARGET_COLUMN].mean() - overall) < 0.02


def test_split_is_repeatable(full_df, parts):
    again = splits.make_splits(full_df)
    for name in parts:
        assert list(parts[name]["appointment_id"]) == list(again[name]["appointment_id"])
