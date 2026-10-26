import pytest

from mlcore import splits
from mlcore.data_generation import generate_appointments


@pytest.fixture(scope="session")
def small_df():
    """A small synthetic dataset so tests run in seconds."""
    return generate_appointments(n_patients=600, n_appointments=2500, seed=11)


@pytest.fixture(scope="session")
def small_parts(small_df):
    return splits.make_splits(small_df, seed=11)