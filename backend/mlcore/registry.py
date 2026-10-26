"""Safe loading and use of the saved model. No Django imports.

Pickle-based files can run code when loaded, so we only ever load the file our
own training script produced, and only after its SHA-256 matches the metadata.
"""
import hashlib
import io
import json
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

    probability = round(float(loaded.pipeline.predict_proba(frame)[0, 1]), 4)
    cuts = metadata["risk_band_cutpoints"]
    return {
        "model_version": metadata["model_version"],
        "schema_version": metadata["schema_version"],
        "probability": probability,
        "risk_band": evaluate.risk_band(probability, cuts["HIGH"], cuts["MEDIUM"]),
        "threshold": round(float(metadata["threshold"]), 4),
        "input_warnings": unusual_inputs(row, metadata.get("typical_ranges", {})),
        "disclaimer": config.DISCLAIMER,
    }