# Week 2 Verification Evidence Index

This directory contains empirical verification records, command outputs, test run logs, execution plans, and catalog inspection outputs collected during the implementation of Week 2 feedback on branch `week2-feedback-implementation`.

---

## Evidence Inventory

| File | Command / Source | Description | Status |
| :--- | :--- | :--- | :--- |
| [`environment-and-versions.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/environment-and-versions.txt) | Python / Django runtime introspection | Python 3.12.5, Django 5.2.18, DRF 3.18.3, PostgreSQL 18.1 on Windows | **PASS** |
| [`git-status.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/git-status.txt) | `git status`, `git log -5 --oneline` | Verifies branch `week2-feedback-implementation`, unmodified `main` | **PASS** |
| [`profile-lifecycle-tests.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/profile-lifecycle-tests.txt) | `pytest tests/test_profile_lifecycle.py -v` | 24 tests covering root create (201), duplicate (409), delete (204), read-only GET (404), root PATCH (405), account preservation, audit retention, and recreation | **PASS** (24/24) |
| [`concurrency-tests.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/concurrency-tests.txt) | `pytest tests/test_concurrency.py -v` | Genuine PostgreSQL multithreaded concurrency test with controlled barriers. Verifies member write rejection upon concurrent admin deactivation | **PASS** (3/3) |
| [`privilege-matrix-tests.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/privilege-matrix-tests.txt) | `pytest tests/test_privilege_matrix.py -v` | Full privilege matrix across Anonymous, Member A, Member B, and Admin, including new lifecycle routes | **PASS** |
| [`csrf-rejection-and-acceptance.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/csrf-rejection-and-acceptance.txt) | `pytest tests/test_csrf_evidence.py -v` | Explicit evidence of rejection without CSRF token (403) and acceptance with valid token (200) for both member and admin flows | **PASS** (4/4) |
| [`pg-catalog-constraints-indexes.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/pg-catalog-constraints-indexes.txt) | `information_schema` & `pg_constraint` catalog queries | Physical verification of foreign keys, unique constraints, check constraints (including `PROFILE_CREATED` / `PROFILE_DELETED`), indexes, and table row counts | **PASS** |
| [`profile-5004-investigation.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/profile-5004-investigation.txt) | SQL inspection of row 5004 | Verifies profile ID 5004 schema state, relational joins, and zero data corruption | **PASS** |
| [`recalculate-completion-dry-run.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/recalculate-completion-dry-run.txt) | `recalculate_completion --dry-run` | Verifies 0 mismatches across all 5,004 database profiles | **PASS** (0 updates) |
| [`explain-admin-list-with-index.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/explain-admin-list-with-index.txt) | `explain_admin_list` | Execution plan using `idx_profile_status_created_id` | **PASS** |
| [`explain-admin-list-without-index.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/explain-admin-list-without-index.txt) | `explain_admin_list --without-index` | Execution plan without composite index (dropped in rollback transaction) | **PASS** |
| [`explain-audit-timeline-with-index.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/explain-audit-timeline-with-index.txt) | `explain_audit_timeline` | Audit event timeline execution plan using `idx_audit_profile_newest` (~0.98 ms) | **PASS** |
| [`explain-audit-timeline-without-index.txt`](file:///c:/Users/Super/Documents/healthtech-profile-builder/docs/evidence/week2/explain-audit-timeline-without-index.txt) | `explain_audit_timeline --without-index` | Audit event timeline sequential scan plan (~15.7 ms, 16x slower) | **PASS** |

---

## Key Guarantees Verified

1. **Root Profile Lifecycle**:
   - `POST /api/profiles/me`: Creates root profile, sets authenticated user as owner, initializes empty sections (`201 Created`).
   - Duplicate creation: Returns `409 Conflict`.
   - `GET /api/profiles/me`: Returns `404 Not Found` if nonexistent (never auto-creates).
   - `PATCH /api/profiles/me`: Returns `405 Method Not Allowed`.
   - `DELETE /api/profiles/me`: Deletes profile row (`204 No Content`), cascades to sections, keeps user account in `users` table, preserves audit events. Re-creation creates a new `profile_id` while historical audit events retain original `profile_id`.

2. **Concurrency & Locking Fix**:
   - `_assert_profile_is_editable(locked)` added to `_save_section`, `create_contact`, `update_contact`, and `delete_contact` in `profiles/services.py`.
   - Evaluated directly on the locked row fetched via `SELECT FOR UPDATE`.
   - Prevents race conditions where a member passes initial permission check, but an admin concurrently deactivates the profile before member acquires the lock.

3. **Audit Immutability & Persistence**:
   - `AuditEvent` manager and model methods block `update()` and `delete()` at ORM level.
   - `AuditEvent.profile_id` is a plain `BigIntegerField` with `fk_count = 0` in PostgreSQL catalog, ensuring it never cascades on profile deletion.

