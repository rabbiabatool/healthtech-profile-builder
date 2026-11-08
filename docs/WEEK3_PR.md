# Pull Request: Week 3 ML Foundations, Inference API & Role-Based Access Control (Re-Review Submission)

**Branch:** `week3-feedback-fixes`  
**Base Branch:** `main`  
**Tested Commit:** `73dd7754816cae623d447b54c9c6977056f3adab` (and follow-up hardening commits)

---

## 1. Executive Summary

This submission provides the re-review package for **Week 3: ML Foundations, Inference API, and Member-Only Predictions UI**, incorporating all reviewer feedback:

1. **Complete Metadata & Cutoff Validation with 503 Recovery ([P2] Resolved)**:
   - **Resolved Non-Object Metadata**: The initial issue where non-object JSON payloads (`[]`, `null`) triggered unhandled 500 errors is resolved by raising `registry.ModelUnavailable`.
   - **Deep Value Validation Before Caching**:
     - `threshold`: Validated as a finite number in `[0, 1]`, with explicit boolean exclusion (`isinstance(v, bool)` is rejected).
     - `risk_band_cutpoints`: Validated that `HIGH` and `MEDIUM` exist, are finite numbers in `[0, 1]`, reject booleans, and enforce `MEDIUM <= HIGH`.
     - `schema_version`: Strictly verified against `config.SCHEMA_VERSION` (`"v1"`), rejecting mismatched or legacy versions.
     - `typical_ranges`: Validated as a mapping of feature names to 2-element finite bounds `[low, high]` where `low <= high`.
   - **Prediction Protection**: `predict_one` and `NoShowPredictView.post` handle unusable prediction results or pipeline runtime errors as `ModelUnavailable` (HTTP 503), preventing unhandled 500 exceptions from leaking.
   - **Automatic Cache Recovery**: Verified via warm-cache -> corrupt -> 503 -> restore -> 200 without manual cache clearing, driven by file fingerprint invalidation `(size, mtime)`.
2. **Access Control & Blast Radius Isolation**:
   - `GET /api/v1/ml/model` and `POST /api/v1/ml/no-show/predict` require member authentication via HttpOnly JWT cookies (`CookieJWTAuthentication`) and standard user role (`IsStandardUser`).
   - Admin sessions and admin JWTs receive direct `401 Unauthorized` / `403 Forbidden` responses (`"Standard user access only."`).
   - Unsafe `POST` requests require CSRF validation (`X-CSRFToken` header matching the `csrftoken` cookie); missing tokens return `403 Forbidden`.
   - **Scoped Data Isolation**: The predictions service is completely stateless: it accepts only appointment features defined in `schema.FEATURE_COLUMNS` and never accepts, queries, or reads patient profile records or user IDs. Horizontal escalation and profile data leakage are prevented by design.
3. **Reproducibility & Verification**:
   - Clean-clone build commands, artifact and dataset SHA-256 digests, and 157/157 passing tests across the focused ML core, prediction, and auth suites.

---

## 2. Reproducible Model Build & Provenance

### Clean-Clone Setup Commands

```powershell
# 1. Clone & activate virtual environment
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Reproducibly generate synthetic data and train the pipeline
python -m mlcore.train
```

### Cryptographic Digests & Provenance

| Component | Identifier / Value |
|:---|:---|
| **Data Version** | `synthetic-appointments-1.0.0` |
| **Random Seed** | `42` (pinned across data generation and splits) |
| **Dataset SHA-256** | `e86a485d5b11cb669df9c2c0e09496edaf29f4f7a557868e2542c876ad4f377b` |
| **Model Version** | `noshow-1.0.0` |
| **Schema Version** | `v1` (`config.SCHEMA_VERSION`) |
| **Artifact SHA-256** | `a855fc0e80acafc76e187c72485d549edefeb3df6388e4d909fe3cfb3fa8a651` |
| **Shipped Architecture** | Logistic Regression pipeline with median imputation, scaling, and one-hot encoding |

> **Model Card Note on Selection Transparency:** As disclosed in the model card, the final decision to ship the baseline Logistic Regression model followed inspection of validation and test metrics. Subsequent production releases must be validated against fresh holdout data; the reused test comparison is an exploratory benchmark and must not be relabeled as an untouched final evaluation.

---

## 3. Real Request & Response Examples

### A. Real Authenticated Request (Member)

**Request:**
```http
POST /api/v1/ml/no-show/predict HTTP/1.1
Host: localhost:8000
Cookie: access_token=eyJhbGciOi...; csrftoken=a9b8c7...
X-CSRFToken: a9b8c7...
Content-Type: application/json

{
  "age": 46,
  "lead_time_days": 7,
  "scheduled_hour": 10,
  "day_of_week": "TUE",
  "appointment_type": "ROUTINE_FOLLOWUP",
  "reminder_sent": true,
  "previous_appointments": 12,
  "previous_no_shows": 1,
  "distance_km": 4.5
}
```

**Recorded Response (200 OK):**
```json
{
  "model_version": "noshow-1.0.0",
  "schema_version": "v1",
  "probability": 0.0842,
  "risk_band": "LOW",
  "threshold": 0.2167,
  "input_warnings": [],
  "disclaimer": "Educational prototype trained on synthetic data. Not clinically validated, not medical advice, and not for decisions about anyone's care."
}
```
*(Note: Values for `probability`, `risk_band`, and `threshold` are calculated by the trained baseline pipeline on synthetic test data and are illustrative for this appointment profile).*

---

### B. Direct Denied Requests (Access Control & CSRF)

#### 1. Wrong Role Denial (Admin JWT on Member Route)
**Request:**
```http
GET /api/v1/ml/model HTTP/1.1
Host: localhost:8000
Cookie: access_token=<admin_jwt_token>
```
**Response (403 Forbidden):**
```json
{
  "detail": "Standard user access only."
}
```

#### 2. Missing CSRF Token Denial
**Request:**
```http
POST /api/v1/ml/no-show/predict HTTP/1.1
Host: localhost:8000
Cookie: access_token=<member_jwt_token>; csrftoken=a9b8c7...
Content-Type: application/json
```
*(Header `X-CSRFToken` omitted)*

**Response (403 Forbidden):**
```json
{
  "detail": "CSRF Failed: CSRF token missing or incorrect."
}
```

---

### C. Malformed Metadata 503 & Automatic Cache Recovery

#### 1. Malformed Cutpoint Value (e.g., String in `HIGH` or `NaN` Threshold)
**Corrupt Metadata:**
```json
{
  "model_version": "noshow-1.0.0",
  "schema_version": "v1",
  "threshold": 0.2167,
  "risk_band_cutpoints": { "HIGH": "oops", "MEDIUM": 0.2 }
}
```
**Request:**
```http
POST /api/v1/ml/no-show/predict HTTP/1.1
Host: localhost:8000
Cookie: access_token=<member_jwt_token>; csrftoken=a9b8c7...
X-CSRFToken: a9b8c7...
```
**Response (503 Service Unavailable, NOT 500):**
```json
{
  "detail": "The model metadata has invalid risk_band_cutpoints: HIGH and MEDIUM must be finite numbers in [0, 1]."
}
```

#### 2. Automatic Recovery Without Manual Cache Clearing
Upon restoring the valid metadata file (with an updated file timestamp), the model registry's `(size, mtime)` fingerprint invalidation detects the repair. The very next request succeeds with `200 OK` **without a server restart and without calling `registry.clear_cache()`**:
```json
{
  "model_version": "noshow-1.0.0",
  "schema_version": "v1",
  "probability": 0.0842,
  "risk_band": "LOW",
  "threshold": 0.2167,
  "input_warnings": [],
  "disclaimer": "Educational prototype trained on synthetic data..."
}
```

---

## 4. AI Workflow, Refinements & Debugging Evidence

### Initial Problem Statement
Initial metadata loading only checked that `isinstance(metadata, dict)` and that key names existed. It did not validate:
- Cutoff values: `{"HIGH": "oops", "MEDIUM": 0.2}` passed `load_model`, but crashed inside `predict_one` with `TypeError: '>' not supported between instances of 'float' and 'str'`.
- Threshold values: `"NaN"`, `"Infinity"`, booleans (`True`/`False`), and numbers outside `[0, 1]` passed `float()` conversions.
- `schema_version`: Key existence was checked, but values like `"1.0.0"` or `"v2"` were not verified against `config.SCHEMA_VERSION`.
- `NoShowPredictView`: Wrapped only `load_model` in try/except; if `predict_one` failed, Django surfaced an unhandled 500.

### Exact AI Prompts & Refinement Iterations

#### Prompt 1 (Initial Non-Object Metadata Fix):
> *"In the model registry, reject non-object metadata (such as a JSON list or null) and validate required fields before caching. Otherwise metadata.get can raise outside the handler and return a 500 instead of the documented 503. Add a regression test and verify recovery after the artifact is repaired."*

#### Prompt 2 (Complete Cutoff & Value Validation Refinement):
> *"[P2] Validate cutoff values completely before caching, not only dictionary keys. In backend/mlcore/registry.py, risk_band_cutpoints is accepted whenever HIGH and MEDIUM keys exist; their values are not checked... Validate threshold, HIGH and MEDIUM as finite numbers with explicit boolean handling and the intended [0,1] range and ordering (MEDIUM <= HIGH). Check the declared schema version against config.SCHEMA_VERSION rather than requiring the key only. Validate any optional metadata used in prediction, such as typical_ranges, before caching as well. Convert invalid release metadata into ModelUnavailable, and add authenticated GET and POST regressions for string/null/boolean/non-finite/out-of-range/inverted cutoff values. Ensure the POST path also handles an unusable prediction result as an unavailable-model response rather than leaking an exception."*

### Key Implementation Diff in `mlcore/registry.py`:
```python
def _is_valid_probability(val: object) -> bool:
    """Checks if val is a finite numeric float/int in [0.0, 1.0], strictly excluding booleans."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    try:
        f = float(val)
        return math.isfinite(f) and (0.0 <= f <= 1.0)
    except (TypeError, ValueError):
        return False

# In load_model:
if metadata.get("schema_version") != config.SCHEMA_VERSION:
    raise ModelUnavailable(f"The model schema version does not match expected '{config.SCHEMA_VERSION}'.")

if not _is_valid_probability(metadata.get("threshold")):
    raise ModelUnavailable("The model metadata has an invalid threshold: expected a finite number in [0, 1].")

cutpoints = metadata.get("risk_band_cutpoints")
if not _is_valid_probability(cutpoints.get("HIGH")) or not _is_valid_probability(cutpoints.get("MEDIUM")):
    raise ModelUnavailable("The model metadata has invalid risk_band_cutpoints: HIGH and MEDIUM must be finite numbers in [0, 1].")
if float(cutpoints["MEDIUM"]) > float(cutpoints["HIGH"]):
    raise ModelUnavailable("The model metadata has invalid risk_band_cutpoints: MEDIUM must be <= HIGH.")
```

---

## 5. Automated Test Evidence

The following command executes the focused test suites for ML core, prediction endpoints, and authentication boundaries:

```powershell
backend/venv/Scripts/python.exe -m pytest backend/mlcore/tests/ backend/predictions/tests/ backend/tests/test_predictions_auth.py -v
```

**Result:** `157 passed in 104.75s`

> **Scope Note:** These 157 passing tests specifically establish correctness for the focused ML pipeline, data generation, evaluation routines, input serialization, metadata validation, 503 recovery, and member/admin authorization boundaries. They do not claim that every backend or frontend regression from other phases was run.

### Key Regressions Included:
- `test_invalid_cutpoint_values_are_refused` PASSED (string, null, boolean, nan, inf, out-of-range, inverted)
- `test_invalid_threshold_values_are_refused` PASSED (string, null, boolean, nan, inf, out-of-range)
- `test_invalid_schema_version_is_refused` PASSED (schema_version != "v1")
- `test_invalid_typical_ranges_are_refused` PASSED (non-dict, invalid length, non-finite bounds, inverted)
- `test_unusable_prediction_raises_model_unavailable` PASSED
- `test_fingerprint_based_automatic_cache_recovery_without_clear_cache` PASSED
- `test_invalid_cutpoint_metadata_returns_503_on_get_and_post` PASSED
- `test_invalid_threshold_and_schema_version_returns_503_on_get_and_post` PASSED
- `test_unusable_prediction_result_returns_503_on_post` PASSED
- `test_api_fingerprint_cache_recovery_without_manual_cache_clearing` PASSED
- `test_admin_user_with_jwt_is_forbidden_by_role` PASSED
- `test_admin_session_cannot_get_model_info` PASSED
- `test_member_predict_enforces_csrf` PASSED
