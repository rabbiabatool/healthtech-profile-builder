"""Safe loading and use of the saved model. No Django imports.

Pickle-based files can run code when loaded, so we only ever load the file our
own training script produced, and only after its SHA-256 matches the metadata.
"""
import hashlib
import io
import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from mlcore import config, evaluate, schema

PUBLIC_INFO_KEYS = [
    "model_version", "schema_version", "shipped_model", "model_type", "selection_note",
    "trained_at", "seed", "data_version", "rows", "class_balance", "threshold",
    "risk_band_cutpoints", "metrics_summary", "input_schema", "typical_ranges",
    "limitations", "disclaimer",
]

REQUIRED_METADATA_KEYS = (
    "artifact_sha256",
    "model_version",
    "schema_version",
    "threshold",
    "risk_band_cutpoints",
)


def _is_valid_probability(val: object) -> bool:
    """Checks if val is a finite numeric float/int in [0.0, 1.0], strictly excluding booleans."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    try:
        f = float(val)
        return math.isfinite(f) and (0.0 <= f <= 1.0)
    except (TypeError, ValueError):
        return False


class ModelUnavailable(RuntimeError):
    """The model cannot be used right now. The message is safe to show to callers."""


@dataclass(frozen=True)
class LoadedModel:
    pipeline: object
    metadata: dict


_lock = threading.Lock()
_cache = {}


def clear_cache():
    with _lock:
        _cache.clear()


def load_model(artifact_dir=None):
    directory = Path(artifact_dir) if artifact_dir else Path(config.ARTIFACT_DIR)
    model_path = directory / config.ARTIFACT_FILENAME
    meta_path = directory / config.METADATA_FILENAME
    if not model_path.is_file() or not meta_path.is_file():
        raise ModelUnavailable("The model has not been built yet. Run: python -m mlcore.train")

    fingerprint = (model_path.stat().st_size, model_path.stat().st_mtime_ns, meta_path.stat().st_mtime_ns)
    key = str(directory.resolve())

    with _lock:
        cached = _cache.get(key)
        if cached is not None and cached[0] == fingerprint:
            return cached[1]
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            model_bytes = model_path.read_bytes()
        except (OSError, ValueError) as error:
            raise ModelUnavailable("The model files could not be read.") from error

        if not isinstance(metadata, dict):
            raise ModelUnavailable("The model metadata is invalid: expected a JSON object.")

        missing_keys = [k for k in REQUIRED_METADATA_KEYS if k not in metadata]
        if missing_keys:
            raise ModelUnavailable(
                f"The model metadata is missing required field(s): {', '.join(missing_keys)}."
            )

        if metadata.get("schema_version") != config.SCHEMA_VERSION:
            raise ModelUnavailable(
                f"The model schema version '{metadata.get('schema_version')}' does not match expected '{config.SCHEMA_VERSION}'."
            )

        threshold = metadata.get("threshold")
        if not _is_valid_probability(threshold):
            raise ModelUnavailable(
                "The model metadata has an invalid threshold: expected a finite number in [0, 1]."
            )

        cutpoints = metadata.get("risk_band_cutpoints")
        if not isinstance(cutpoints, dict) or "HIGH" not in cutpoints or "MEDIUM" not in cutpoints:
            raise ModelUnavailable(
                "The model metadata has invalid risk_band_cutpoints: expected dict with HIGH and MEDIUM."
            )
        high_cut = cutpoints.get("HIGH")
        med_cut = cutpoints.get("MEDIUM")
        if not _is_valid_probability(high_cut) or not _is_valid_probability(med_cut):
            raise ModelUnavailable(
                "The model metadata has invalid risk_band_cutpoints: HIGH and MEDIUM must be finite numbers in [0, 1]."
            )
        if float(med_cut) > float(high_cut):
            raise ModelUnavailable(
                "The model metadata has invalid risk_band_cutpoints: MEDIUM must be <= HIGH."
            )

        typical_ranges = metadata.get("typical_ranges")
        if typical_ranges is not None:
            if not isinstance(typical_ranges, dict):
                raise ModelUnavailable(
                    "The model metadata has invalid typical_ranges: expected a dict."
                )
            for feat_name, bounds in typical_ranges.items():
                if not isinstance(feat_name, str):
                    raise ModelUnavailable(
                        "The model metadata has invalid typical_ranges: feature names must be strings."
                    )
                if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                    raise ModelUnavailable(
                        f"The model metadata has invalid typical_ranges for '{feat_name}': expected [low, high]."
                    )
                low, high = bounds
                if (
                    isinstance(low, bool)
                    or isinstance(high, bool)
                    or not isinstance(low, (int, float))
                    or not isinstance(high, (int, float))
                    or not math.isfinite(low)
                    or not math.isfinite(high)
                    or low > high
                ):
                    raise ModelUnavailable(
                        f"The model metadata has invalid typical_ranges for '{feat_name}': bounds must be finite numbers with low <= high."
                    )

        expected = metadata.get("artifact_sha256")
        if not expected or hashlib.sha256(model_bytes).hexdigest() != expected:
            raise ModelUnavailable("The model file failed its integrity check and was not loaded.")
        if metadata.get("model_version") != config.MODEL_VERSION:
            raise ModelUnavailable("The model version does not match this code version.")
        try:
            pipeline = joblib.load(io.BytesIO(model_bytes))
        except Exception as error:
            raise ModelUnavailable("The model file could not be loaded.") from error

        loaded = LoadedModel(pipeline=pipeline, metadata=metadata)
        _cache[key] = (fingerprint, loaded)
        return loaded


def public_model_info(metadata):
    """Only the facts that are safe and useful to show to a signed-in user."""
    return {key: metadata[key] for key in PUBLIC_INFO_KEYS if key in metadata}


def unusual_inputs(row, typical_ranges):
    notes = []
    for name, (low, high) in typical_ranges.items():
        value = row.get(name)
        if value is None or value != value:  # missing, or NaN
            continue
        if value < low or value > high:
            notes.append(
                f"{name} = {value} is unusual compared with the training data (typical range {low} to {high})."
            )
    return notes


def predict_one(loaded, features):
    metadata = loaded.metadata
    row = {name: features[name] for name in schema.FEATURE_COLUMNS}
    if row["distance_km"] is None:
        row["distance_km"] = float("nan")
    frame = pd.DataFrame([row], columns=schema.FEATURE_COLUMNS)

    try:
        raw_prob = float(loaded.pipeline.predict_proba(frame)[0, 1])
        if not math.isfinite(raw_prob) or not (0.0 <= raw_prob <= 1.0):
            raise ValueError("Prediction probability is non-finite or outside [0, 1].")
        probability = round(raw_prob, 4)
        cuts = metadata["risk_band_cutpoints"]
        band = evaluate.risk_band(probability, float(cuts["HIGH"]), float(cuts["MEDIUM"]))
        thresh = round(float(metadata["threshold"]), 4)
        warnings = unusual_inputs(row, metadata.get("typical_ranges", {}))
    except Exception as error:
        raise ModelUnavailable(f"The model could not generate a usable prediction: {error}") from error

    return {
        "model_version": metadata["model_version"],
        "schema_version": metadata["schema_version"],
        "probability": probability,
        "risk_band": band,
        "threshold": thresh,
        "input_warnings": warnings,
        "disclaimer": config.DISCLAIMER,
    }
