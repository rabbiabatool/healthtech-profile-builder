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
    with pytest.raises(registry.ModelUnavailable, match="missing required field"):
        registry.load_model(target)


def test_non_object_metadata_is_refused_and_recovers(small_artifact_dir, tmp_path):
    """Reject non-dict metadata (e.g. list, null, int) without crashing with 500, and recover when fixed."""
    target = _copy(small_artifact_dir, tmp_path)
    meta_path = target / config.METADATA_FILENAME
    valid_text = meta_path.read_text(encoding="utf-8")

    for bad_content in ("[]", "null", '"just a string"', "123", "true"):
        meta_path.write_text(bad_content, encoding="utf-8")
        registry.clear_cache()
        with pytest.raises(registry.ModelUnavailable, match="JSON object"):
            registry.load_model(target)

    # Verify recovery after artifact is repaired
    meta_path.write_text(valid_text, encoding="utf-8")
    repaired = registry.load_model(target)
    assert repaired is not None
    assert isinstance(repaired.metadata, dict)
    assert repaired.metadata["model_version"] == config.MODEL_VERSION


def test_missing_required_metadata_fields_is_refused_and_recovers(small_artifact_dir, tmp_path):
    """Validate required metadata fields before caching, and recover when repaired."""
    target = _copy(small_artifact_dir, tmp_path)
    meta_path = target / config.METADATA_FILENAME
    valid_text = meta_path.read_text(encoding="utf-8")
    valid_data = json.loads(valid_text)

    # Missing threshold
    bad_data = dict(valid_data)
    del bad_data["threshold"]
    meta_path.write_text(json.dumps(bad_data), encoding="utf-8")
    registry.clear_cache()
    with pytest.raises(registry.ModelUnavailable, match="missing required field.*threshold"):
        registry.load_model(target)

    # Invalid risk_band_cutpoints
    bad_data = dict(valid_data)
    bad_data["risk_band_cutpoints"] = "not-a-dict"
    meta_path.write_text(json.dumps(bad_data), encoding="utf-8")
    registry.clear_cache()
    with pytest.raises(registry.ModelUnavailable, match="invalid risk_band_cutpoints"):
        registry.load_model(target)

    # Verify recovery after repair
    meta_path.write_text(valid_text, encoding="utf-8")
    repaired = registry.load_model(target)
    assert repaired is not None
    assert "threshold" in repaired.metadata


def test_invalid_cutpoint_values_are_refused(small_artifact_dir, tmp_path):
    """Validate HIGH and MEDIUM cutpoints: finite numbers in [0, 1], not booleans, and MEDIUM <= HIGH."""
    target = _copy(small_artifact_dir, tmp_path)
    meta_path = target / config.METADATA_FILENAME
    valid_data = json.loads(meta_path.read_text(encoding="utf-8"))

    invalid_cases = [
        ({"HIGH": "oops", "MEDIUM": 0.2}, "finite numbers in \\[0, 1\\]"),
        ({"HIGH": None, "MEDIUM": 0.2}, "finite numbers in \\[0, 1\\]"),
        ({"HIGH": True, "MEDIUM": 0.2}, "finite numbers in \\[0, 1\\]"),
        ({"HIGH": 0.8, "MEDIUM": False}, "finite numbers in \\[0, 1\\]"),
        ({"HIGH": float("nan"), "MEDIUM": 0.2}, "finite numbers in \\[0, 1\\]"),
        ({"HIGH": float("inf"), "MEDIUM": 0.2}, "finite numbers in \\[0, 1\\]"),
        ({"HIGH": 1.5, "MEDIUM": 0.2}, "finite numbers in \\[0, 1\\]"),
        ({"HIGH": 0.8, "MEDIUM": -0.1}, "finite numbers in \\[0, 1\\]"),
        ({"HIGH": 0.2, "MEDIUM": 0.8}, "MEDIUM must be <= HIGH"),
    ]

    for bad_cuts, match_pattern in invalid_cases:
        bad_meta = dict(valid_data, risk_band_cutpoints=bad_cuts)
        meta_path.write_text(json.dumps(bad_meta), encoding="utf-8")
        registry.clear_cache()
        with pytest.raises(registry.ModelUnavailable, match=match_pattern):
            registry.load_model(target)


def test_invalid_threshold_values_are_refused(small_artifact_dir, tmp_path):
    """Validate threshold: finite number in [0, 1], not boolean or string."""
    target = _copy(small_artifact_dir, tmp_path)
    meta_path = target / config.METADATA_FILENAME
    valid_data = json.loads(meta_path.read_text(encoding="utf-8"))

    invalid_thresholds = [
        "NaN",
        "Infinity",
        "oops",
        None,
        True,
        False,
        float("nan"),
        float("inf"),
        -0.05,
        1.05,
    ]

    for bad_thresh in invalid_thresholds:
        bad_meta = dict(valid_data, threshold=bad_thresh)
        meta_path.write_text(json.dumps(bad_meta), encoding="utf-8")
        registry.clear_cache()
        with pytest.raises(registry.ModelUnavailable, match="invalid threshold"):
            registry.load_model(target)


def test_invalid_schema_version_is_refused(small_artifact_dir, tmp_path):
    """Schema version must match config.SCHEMA_VERSION."""
    target = _copy(small_artifact_dir, tmp_path)
    meta_path = target / config.METADATA_FILENAME
    valid_data = json.loads(meta_path.read_text(encoding="utf-8"))

    for bad_version in ("1.0.0", "v2", "", None):
        bad_meta = dict(valid_data, schema_version=bad_version)
        meta_path.write_text(json.dumps(bad_meta), encoding="utf-8")
        registry.clear_cache()
        with pytest.raises(registry.ModelUnavailable, match="schema version.*does not match"):
            registry.load_model(target)


def test_invalid_typical_ranges_are_refused(small_artifact_dir, tmp_path):
    """Optional typical_ranges must be a dict mapping string features to [low, high] finite bounds with low <= high."""
    target = _copy(small_artifact_dir, tmp_path)
    meta_path = target / config.METADATA_FILENAME
    valid_data = json.loads(meta_path.read_text(encoding="utf-8"))

    invalid_ranges = [
        "not-a-dict",
        {"age": "not-a-list"},
        {"age": [10]},
        {"age": [10, 20, 30]},
        {"age": [80, 20]},  # low > high
        {"age": [float("nan"), 80]},
        {"age": [True, 80]},
    ]

    for bad_range in invalid_ranges:
        bad_meta = dict(valid_data, typical_ranges=bad_range)
        meta_path.write_text(json.dumps(bad_meta), encoding="utf-8")
        registry.clear_cache()
        with pytest.raises(registry.ModelUnavailable, match="invalid typical_ranges"):
            registry.load_model(target)


def test_unusable_prediction_raises_model_unavailable(small_artifact_dir):
    """If the pipeline generates a non-finite or out-of-range probability, predict_one raises ModelUnavailable."""
    class BrokenPipeline:
        def predict_proba(self, X):
            import numpy as np
            return np.array([[0.0, float("nan")]])

    loaded = registry.load_model(small_artifact_dir)
    broken_loaded = registry.LoadedModel(pipeline=BrokenPipeline(), metadata=loaded.metadata)

    with pytest.raises(registry.ModelUnavailable, match="usable prediction"):
        registry.predict_one(broken_loaded, VALID_INPUT)


def test_fingerprint_based_automatic_cache_recovery_without_clear_cache(small_artifact_dir, tmp_path):
    """Prove warm-cache -> corrupt -> 503/ModelUnavailable -> restore -> 200/LoadedModel with NO manual cache clearing.
    
    Uses deterministic os.utime timestamp updates to demonstrate file fingerprint-based invalidation.
    """
    import os, time

    target = _copy(small_artifact_dir, tmp_path)
    meta_path = target / config.METADATA_FILENAME
    valid_text = meta_path.read_text(encoding="utf-8")

    # Step 1: Warm cache
    base_time = time.time()
    os.utime(meta_path, (base_time, base_time))
    first_load = registry.load_model(target)
    assert first_load is not None
    # Subsequent read with unchanged timestamp returns the cached instance
    assert registry.load_model(target) is first_load

    # Step 2: Corrupt metadata with advanced timestamp (NO clear_cache called)
    corrupt_time = base_time + 10.0
    bad_data = json.loads(valid_text)
    bad_data["risk_band_cutpoints"] = {"HIGH": "invalid_string", "MEDIUM": 0.2}
    meta_path.write_text(json.dumps(bad_data), encoding="utf-8")
    os.utime(meta_path, (corrupt_time, corrupt_time))

    with pytest.raises(registry.ModelUnavailable, match="invalid risk_band_cutpoints"):
        registry.load_model(target)

    # Step 3: Restore valid metadata with another advanced timestamp (NO clear_cache called)
    restore_time = corrupt_time + 10.0
    meta_path.write_text(valid_text, encoding="utf-8")
    os.utime(meta_path, (restore_time, restore_time))

    recovered = registry.load_model(target)
    assert recovered is not None
    assert recovered is not first_load
    assert recovered.metadata["schema_version"] == config.SCHEMA_VERSION


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
