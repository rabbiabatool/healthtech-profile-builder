# Pull Request: Week 3 ML Foundations, Inference API & Role-Based Access Control (Re-Review Submission)

**Branch:** `week3-feedback-fixes`  
**Base Branch:** `main` (or `phase-13-predictions-auth-fix`)

---

## 1. Executive Summary

This submission provides the re-review package for **Week 3: ML Foundations, Inference API, and Member-Only Predictions UI**, incorporating all reviewer feedback:

1. **Model Registry Hardening & 503 Recovery**:
   - Explicitly rejects non-object metadata payloads (e.g., JSON lists `[]`, `null`, numbers, strings) by raising `registry.ModelUnavailable` instead of allowing `AttributeError` to propagate as an unhandled 500 error.
   - Validates all mandatory metadata fields (`artifact_sha256`, `model_version`, `schema_version`, `threshold`, `risk_band_cutpoints`) *before* committing to cache.
   - Verifies automatic cache recovery: repairing the artifact file immediately allows subsequent requests to succeed with `200 OK` without requiring a server restart.
2. **Access Control & Blast Radius Isolation**:
   - `GET /api/v1/ml/model` and `POST /api/v1/ml/no-show/predict` strictly require member authentication via HttpOnly JWT cookies (`CookieJWTAuthentication`) and standard user role (`IsStandardUser`).
   - Admin sessions and admin JWTs receive a direct `401 Unauthorized` / `403 Forbidden` response (`"Standard user access only"`).
   - Horizontal privilege escalation and patient profile data leakage are impossible: the predictions service is completely stateless and never accepts or queries user IDs.
3. **Reproducibility & Verification**:
   - Clean-clone build commands, artifact and dataset SHA-256 digests, and 145/145 automated test suite passes.

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
| **Artifact SHA-256** | `a855fc0e80acafc76e187c72485d549edefeb3df6388e4d909fe3cfb3fa8a651` |
| **Shipped Architecture** | Logistic Regression pipeline with median imputation, scaling, and one-hot encoding |

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

**Response (200 OK):**
```json
{
  "model_version": "noshow-1.0.0",
  "schema_version": "1.0.0",
  "probability": 0.0842,
  "risk_band": "LOW",
  "threshold": 0.2167,
  "input_warnings": [],
  "disclaimer": "Educational prototype trained on synthetic data. Not clinically validated, not medical advice, and not for decisions about anyone's care."
}
```

---

### B. Direct Denied Request (Wrong Role: Admin)

**Request (Admin attempting to access member prediction route):**
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

---

### C. Malformed Metadata Failure & Immediate Recovery

**Simulated Failure:**
Metadata file `noshow-1.0.0.meta.json` replaced with invalid JSON list `[]` or missing `threshold`.

**Request:**
```http
GET /api/v1/ml/model HTTP/1.1
Host: localhost:8000
Cookie: access_token=<member_jwt_token>
```

**Response (503 Service Unavailable, NOT 500):**
```json
{
  "detail": "The model metadata is invalid: expected a JSON object."
}
```

**Recovery:**
Upon restoring valid metadata text, the subsequent request returns `200 OK` dynamically without server restart:
```json
{
  "model_version": "noshow-1.0.0",
  "threshold": 0.2167,
  "disclaimer": "Educational prototype trained on synthetic data..."
}
```

---

## 4. AI Workflow, Refinements & Debugging Example

### Before Refinement (The Bug)
```python
# Initial implementation in mlcore/registry.py:
metadata = json.loads(meta_path.read_text(encoding="utf-8"))
expected = metadata.get("artifact_sha256")  # Crashes if metadata is a list [] or null!
```
*Problem:* If a malformed or non-dict metadata file was placed in the artifact folder, `metadata.get()` raised `AttributeError: 'list' object has no attribute 'get'`. Because this was unhandled, Django converted it to an HTTP 500 Internal Server Error instead of the documented HTTP 503.

### After Refinement (The Fix)
```python
# Refined implementation:
metadata = json.loads(meta_path.read_text(encoding="utf-8"))
if not isinstance(metadata, dict):
    raise ModelUnavailable("The model metadata is invalid: expected a JSON object.")

missing_keys = [k for k in REQUIRED_METADATA_KEYS if k not in metadata]
if missing_keys:
    raise ModelUnavailable(f"The model metadata is missing required field(s): {', '.join(missing_keys)}.")

cutpoints = metadata.get("risk_band_cutpoints")
if not isinstance(cutpoints, dict) or "HIGH" not in cutpoints or "MEDIUM" not in cutpoints:
    raise ModelUnavailable("The model metadata has invalid risk_band_cutpoints: expected dict with HIGH and MEDIUM.")

try:
    float(metadata["threshold"])
except (TypeError, ValueError):
    raise ModelUnavailable("The model metadata has an invalid threshold: expected a numeric value.")
```

### Exact AI Prompt Used
> *"In the model registry, reject non-object metadata (such as a JSON list or null) and validate required fields before caching. Otherwise metadata.get can raise outside the handler and return a 500 instead of the documented 503. Add a regression test and verify recovery after the artifact is repaired."*

### Context Management & Blast-Radius Controls
1. **Context Management**: Inspected existing `registry.py` cache fingerprinting logic `(size, mtime)` to ensure cache invalidation triggers on repaired timestamps without stale object retention.
2. **Blast-Radius Controls**: Changes were strictly restricted to `backend/mlcore/registry.py` and test harnesses. No changes were made to authentication, database migrations, or user profiles.
3. **Verification**: Executed 145 backend tests across ML core, predictions serializers, and auth integration suites.

---

## 5. Automated Test Evidence

```powershell
backend/venv/Scripts/pytest.exe backend/mlcore/tests/ backend/predictions/tests/ backend/tests/test_predictions_auth.py -v
```

**Result:** `145 passed in 113.64s`
- `test_non_object_metadata_is_refused_and_recovers` PASSED
- `test_missing_required_metadata_fields_is_refused_and_recovers` PASSED
- `test_malformed_metadata_returns_503_not_500_and_recovers` PASSED
- `test_malformed_metadata_gives_503_and_recovers` PASSED
- `test_admin_user_with_jwt_is_forbidden_by_role` PASSED
- `test_admin_session_cannot_get_model_info` PASSED
