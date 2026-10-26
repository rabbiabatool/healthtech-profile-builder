import json
import shutil

import pytest

from mlcore import config, evaluate, registry

VALID_INPUT = {
    "age": 34,
    "lead_time_days": 45,
    "scheduled_hour": 16,
    "day_of_week": "MON",
    "appointment_type": "FOLLOW_UP",
    "reminder_sent": False,
    "previous_appointments": 6,
    "previous_no_shows": 2,
    "distance_km": 12.5,
}


@pytest.fixture(autouse=True)
def fresh_cache():
    registry.clear_cache()
    yield
    registry.clear_cache()


def _copy(small_artifact_dir, tmp_path):
    target = tmp_path / "copy"
    shutil.copytree(small_artifact_dir, target)
    return target


def test_valid_artifact_loads_and_is_cached(small_artifact_dir):
    first = registry.load_model(small_artifact_dir)
    assert type(first.pipeline).__name__ == "Pipeline"
    assert registry.load_model(small_artifact_dir) is first


def test_missing_artifact_gives_a_clear_error(tmp_path):
    with pytest.raises(registry.ModelUnavailable, match="not been built"):
        registry.load_model(tmp_path)


def test_a_tampered_file_is_refused(small_artifact_dir, tmp_path):
    target = _copy(small_artifact_dir, tmp_path)
    path = target / config.ARTIFACT_FILENAME
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0xFF
    path.write_bytes(bytes(data))
    with pytest.raises(registry.ModelUnavailable, match="integrity"):
        registry.load_model(target)


def test_a_file_changed_after_loading_is_noticed(small_artifact_dir, tmp_path):
    target = _copy(small_artifact_dir, tmp_path)
    registry.load_model(target)
    with open(target / config.ARTIFACT_FILENAME, "ab") as handle:
        handle.write(b"x")
    with pytest.raises(registry.ModelUnavailable, match="integrity"):
        registry.load_model(target)


def test_metadata_without_a_hash_is_refused(small_artifact_dir, tmp_path):
    target = _copy(small_artifact_dir, tmp_path)
    meta_path = target / config.METADATA_FILENAME
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    del metadata["artifact_sha256"]
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(registry.ModelUnavailable, match="integrity"):
        registry.load_model(target)


def test_prediction_has_the_documented_fields_and_a_consistent_band(small_artifact_dir):
    loaded = registry.load_model(small_artifact_dir)
    result = registry.predict_one(loaded, VALID_INPUT)
    assert set(result) == {
        "model_version", "schema_version", "probability", "risk_band",
        "threshold", "input_warnings", "disclaimer",
    }
    assert 0.0 <= result["probability"] <= 1.0
    cuts = loaded.metadata["risk_band_cutpoints"]
    assert result["risk_band"] == evaluate.risk_band(result["probability"], cuts["HIGH"], cuts["MEDIUM"])
    assert result["disclaimer"] == config.DISCLAIMER


def test_prediction_works_when_distance_is_missing(small_artifact_dir):
    loaded = registry.load_model(small_artifact_dir)
    result = registry.predict_one(loaded, {**VALID_INPUT, "distance_km": None})
    assert 0.0 <= result["probability"] <= 1.0


def test_unusual_inputs_are_flagged_and_missing_values_are_skipped():
    typical = {"age": [20, 80], "distance_km": [1.0, 50.0]}
    notes = registry.unusual_inputs({"age": 90, "distance_km": float("nan")}, typical)
    assert len(notes) == 1 and "age" in notes[0]
    assert registry.unusual_inputs({"age": 40, "distance_km": 10.0}, typical) == []


def test_public_info_hides_internal_details(small_artifact_dir):
    loaded = registry.load_model(small_artifact_dir)
    info = registry.public_model_info(loaded.metadata)
    assert "artifact_sha256" not in info
    assert "library_versions" not in info
    assert {"input_schema", "limitations", "disclaimer", "threshold", "model_type"} <= set(info)