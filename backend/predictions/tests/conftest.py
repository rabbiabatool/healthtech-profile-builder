import shutil

import pytest

from mlcore import config, registry, train
from mlcore.data_generation import generate_appointments


@pytest.fixture(scope="session")
def artifact_dir(tmp_path_factory):
    """A real, tiny trained model in a temporary folder."""
    directory = tmp_path_factory.mktemp("api_artifact")
    df = generate_appointments(n_patients=600, n_appointments=2500, seed=11)
    train.train(
        df=df,
        artifact_dir=directory,
        docs_dir=directory / "docs",
        n_boot=30,
        make_figures=False,
        enforce_gate=False,
        write_docs=False,
    )
    return directory


@pytest.fixture
def model_ready(monkeypatch, artifact_dir):
    monkeypatch.setattr(config, "ARTIFACT_DIR", artifact_dir)
    registry.clear_cache()
    yield
    registry.clear_cache()


@pytest.fixture
def no_model(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ARTIFACT_DIR", tmp_path)
    registry.clear_cache()
    yield
    registry.clear_cache()


@pytest.fixture
def tampered_model(monkeypatch, tmp_path, artifact_dir):
    target = tmp_path / "tampered"
    shutil.copytree(artifact_dir, target)
    path = target / config.ARTIFACT_FILENAME
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0xFF
    path.write_bytes(bytes(data))
    monkeypatch.setattr(config, "ARTIFACT_DIR", target)
    registry.clear_cache()
    yield
    registry.clear_cache()
