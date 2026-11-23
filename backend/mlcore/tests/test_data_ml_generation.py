import pytest

from mlcore import config, schema
from mlcore.data_generation import dataset_hash, generate_appointments


@pytest.fixture(scope="module")
def df():
    return generate_appointments()


def test_same_seed_gives_identical_data_and_different_seed_differs():
    a = generate_appointments(n_patients=300, n_appointments=1000, seed=7)
    b = generate_appointments(n_patients=300, n_appointments=1000, seed=7)
    c = generate_appointments(n_patients=300, n_appointments=1000, seed=8)
    assert dataset_hash(a) == dataset_hash(b)
    assert dataset_hash(a) != dataset_hash(c)


def test_columns_and_size_match_the_documented_schema(df):
    assert list(df.columns) == schema.RAW_COLUMNS
    assert len(df) == config.N_APPOINTMENTS
    assert 5500 <= df["patient_ref"].nunique() <= config.N_PATIENTS


@pytest.mark.parametrize("column,bounds", list(schema.NUMERIC_RANGES.items()))
def test_numeric_columns_stay_inside_their_ranges(df, column, bounds):
    low, high = bounds
    assert df[column].min() >= low
    assert df[column].max() <= high


@pytest.mark.parametrize("column,allowed", list(schema.CATEGORICAL_VALUES.items()))
def test_categorical_columns_only_use_allowed_values(df, column, allowed):
    assert set(df[column].unique()) <= set(allowed)


def test_target_is_binary_and_imbalance_is_as_documented(df):
    assert set(df[schema.TARGET_COLUMN].unique()) == {0, 1}
    assert 0.17 <= df[schema.TARGET_COLUMN].mean() <= 0.23


def test_only_distance_has_missing_values(df):
    rates = df[schema.FEATURE_COLUMNS].isna().mean()
    assert 0.06 <= rates["distance_km"] <= 0.10
    assert rates.drop("distance_km").sum() == 0


def test_previous_no_shows_never_exceed_previous_appointments(df):
    assert (df["previous_no_shows"] <= df["previous_appointments"]).all()


def test_leakage_column_exists_but_is_not_a_feature(df):
    column = schema.LEAKAGE_COLUMNS[0]
    assert column in df.columns
    assert column not in schema.FEATURE_COLUMNS
    assert (df[column].isna() == (df[schema.TARGET_COLUMN] == 1)).all()


def test_no_forbidden_columns_exist(df):
    assert set(schema.FORBIDDEN_COLUMNS).isdisjoint(df.columns)


def test_history_only_looks_backwards(df):
    for _, group in df.groupby("patient_ref"):
        if group["previous_appointments"].max() >= 60:
            continue  # capped patients are skipped
        growth = group["previous_no_shows"].diff().iloc[1:].to_numpy()
        earlier_outcomes = group[schema.TARGET_COLUMN].iloc[:-1].to_numpy()
        assert (growth == earlier_outcomes).all()