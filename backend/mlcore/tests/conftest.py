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


@pytest.fixture(scope="session")
def small_artifact_dir(tmp_path_factory, small_df):
    """A real (tiny) trained artifact in a temporary folder."""
    from mlcore import train

    directory = tmp_path_factory.mktemp("small_artifact")
    train.train(
        df=small_df,
        artifact_dir=directory,
        docs_dir=directory / "docs",
        n_boot=30,
        make_figures=False,
        enforce_gate=False,
        write_docs=False,
    )
    return directory
