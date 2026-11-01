# AI-assisted workflow log

## Rules I followed

1. AI output is a hypothesis. Only executable checks (tests, queries, EXPLAIN, manual reproduction) count as validation.
2. Another AI agreeing with a design is not evidence.
3. Every change records its scope and blast radius.
4. Secrets are never pasted into prompts or committed; data is fictional.

## Entry template

### E<number>: <title> (<date>, branch, commit hash)
- Goal:
- Prompt (verbatim, secrets removed):
- What the AI proposed (summary, link to commit):
- My refinement (what I changed or rejected, and why):
- Scope: files changed / files deliberately not touched
- Blast radius: what else could break, and how I checked
- Validation: command -> expected -> actual output (pasted) -> date and commit

How to fill the placeholders: `git log --format="%h %ad %s" --date=short` lists the hash, date and message of every commit.

## Entries

### E1: Initial brief and design decisions (2026-10-16, branch `main`, commit `1eca997`)
- Goal: Build a HealthTech profile builder with two distinct authentication flows, in four phases, designing before coding.
- Prompt (verbatim, brief shortened with [...]):
  > Act as  a senior full stack AI/ML Engineer.: Build a small HealthTech profile-builder application with two distinct authentication flows: JWT for self-registered users and server-side sessions for database-provisioned admins. Use fictional/synthetic profiles only. [...] Analyze all above requirements and constraints . Our workflow will be design, build, test , debugging in case of any errors and commiting in github repository. [...] We will build this application with all above features and constraints in 4 phases. Before moving towards implementation ,  design architecture, APIs, Database and technologies and why using this design and technology. Keep your tone conversational and easy

  Follow-up decision (verbatim):
  > Single User table with a `role` field (instead of a separate Admin table). [...] Fine with you? yes . PostgreSQL from the start [...] yes, use postgresql. Start phase 1
- What the AI proposed: A design document: two "doors" (member JWT in HttpOnly cookies, admin server-side sessions), one user table with a `role` column, one profile table, a composite index for the admin list, and a four-phase plan with a CSRF-token flow. It asked me to confirm two decisions before building.
- My refinement: I confirmed a single user table with a role and PostgreSQL from the start. During Phase 2 the AI corrected its own design: the refresh cookie path became `/api/auth/` instead of `/api/auth/refresh`, because logout also needs that cookie.
- Scope: Design only for this step; no code was written until the decisions were confirmed. Later phases implemented it.
- Blast radius: None for the design step. The one-table-with-role choice affects every permission check, so isolation is enforced per endpoint (one authentication class per view, role re-read from the database on each request) and tested by the route matrix.
- Validation:
  - Admin session logout really ends the session. Command: the manual PowerShell sequence (admin login, list, view, deactivate, logout, then `GET /api/admin/me`). Expected: the last call fails with 401. Actual: `Invoke-RestMethod : {"detail":"Authentication credentials were not provided."}` on the final `Invoke-RestMethod "$base/me" -WebSession $web`, with `4 admin@example.com Demo Admin ADMIN` returned by the login step.
  - Phase 1 database rules and the later phases. Command: `pytest -v` in `backend`. Expected: 0 failures. Actual: 21 passed (Phase 1).

### E2: Wrong virtual environment (ModuleNotFoundError, then ImproperlyConfigured) (2026-10-16, branch `phase-2-user-auth`, environment fix)
- Goal: Make `pytest -v` run in the HealthTech project.
- Prompt (verbatim, tracebacks shortened):
  > I am inside .venv and in backend folder, earlier when I run pytest -v , this error come: pytest -v ImportError while loading conftest 'C:\Users\Super\Documents\healthtech-profile-builder\backend\tests\conftest.py'. [...] E   ModuleNotFoundError: No module named 'rest_framework' then I installed: python -m pip install djangorestframework and then again run test command but this error is coming: [...] ..\..\enterprise-ai-assistant\.venv\Lib\site-packages\rest_framework\test.py:141: [...] django.core.exceptions.ImproperlyConfigured: Requested setting REST_FRAMEWORK, but settings are not configured. You must either define the environment variable DJANGO_SETTINGS_MODULE or call settings.configure() before accessing settings. help me understand and fix this bug
- What the AI proposed: The traceback paths point at `enterprise-ai-assistant\.venv`, a different project's environment. That environment lacked `pytest-django`, the plugin that reads `DJANGO_SETTINGS_MODULE` from `pytest.ini`, so Django was never configured. Fix: `deactivate`, activate this project's `venv`, print `sys.executable` to prove which Python is active, then `pip install -r requirements.txt` and re-run.
- My refinement: I accepted leaving the stray `djangorestframework` install in the other project's environment, because it is harmless and its own requirements files are untouched.
- Scope: Environment only. No repository file changed.
- Blast radius: The other project's environment gained one unused package. Nothing in this repository was affected.
- Validation:
  - Command: `python -c "import sys; print(sys.executable)"`. Expected: a path ending in `healthtech-profile-builder\backend\venv\Scripts\python.exe`. Actual: `C:\Users\Super\Documents\healthtech-profile-builder\backend\venv\Scripts\python.exe`.
  - Command: `pytest -v`. Expected: collection succeeds with 0 failures. Actual: 42 passed (Phase 2).

### E3: Nested frontend folders and the Turbopack root error (2026-10-17, branch `main`, Phase 4 commit `b8a1e0b`)
- Goal: Get the Next.js frontend to start after `create-next-app` produced `frontend/frontend`.
- Prompt (verbatim, with the two screenshots described):
  > see inside frontend folder, another frontend folder is created or another next.js app, I have added all code inside this nested frontend app and started this app, now this error is coming as shown in second image. help me understand and solve this isssue

  Screenshot 1: a file tree showing `frontend/frontend/app/admin/...`. Screenshot 2 (Next.js 16.4.2 Turbopack): `Module not found: Can't resolve '../../client/components/redirect-status-code'` in `./frontend/node_modules/next/dist/esm/build/templates/app-page-runtime.js (100:1)`.
- What the AI proposed: Two Next.js projects were nested, each with its own lockfile and `node_modules`. Hypothesis: Turbopack picked the outer folder as the project root while the app ran from the inner one. The AI labelled this as its best reading of the evidence, and gave a fix that also covers a corrupted install: rename the outer folder, move the inner app up, delete `.next` and `node_modules`, run `npm install`.
- My refinement: I kept my code (it was all in the inner app) and removed the outer template copy after checking `next.config.mjs`, `app`, `components` and `lib` were present.
- Scope: Folder structure and dependencies only; the application code was not edited.
- Blast radius: Deleting the old outer folder could lose files if the code had landed there. That is why the fix lists `dir` checks before `Remove-Item`. The repository's `.gitignore` already excluded `node_modules` and `.next`.
- Validation:
  - Command: `npm run dev`, then open `http://localhost:3000`. Expected: the home page renders with no red error overlay. Actual: Dev server started at `http://localhost:3000`, 200 OK rendered.
  - Command: `npm run build`. Expected: finishes without errors. Actual: Next.js production build completed successfully.

### E4: Wrong management command name (seed_demo_data versus seed_data) (2026-10-17, no code change)
- Goal: Create three fictional demo users.
- Prompt (verbatim output pasted):
  > python manage.py seed_demo_data --count 3
  > Unknown command: 'seed_demo_data'
  > Type 'manage.py help' for usage.
- What the AI proposed: The command is named after its file: `seed_data.py`, so `python manage.py seed_data --count 3`. It listed three checks if the name still failed: the exact file path, both `__init__.py` files, and `profiles` in `INSTALLED_APPS`, and suggested `python manage.py help` to see the command under `[profiles]`.
- My refinement: None needed; the name was the only problem.
- Scope: No files changed.
- Blast radius: None. The seeder is idempotent, so a repeated run creates no duplicates.
- Validation: Command: `python manage.py seed_data --count 3`. Expected: `Created 0 users and 0 profiles with sections.` if those users already exist, otherwise a positive count. Actual: `Created 0 users and 0 profiles with sections.`

### E5: Duplicate columns during expand/migrate/contract, and the unconfirmed weight-constraint check (2026-10-18, branch `phase-5-relational-model`, commit `848f6da`)
- Goal: Understand why demographic and wellness fields appeared on both `health_profiles` and the new section tables.
- Prompt (verbatim question; `\d profile_demographics`, `\d wellness_preferences` and `\d health_profiles` output was pasted):
  > why demographic and wellness table feilds are also included in health profile?
- What the AI proposed: The duplicates were the Week 1 flat columns, kept deliberately because the API still used them (expand, migrate, contract). Phase 6 would switch the API to the new tables and then drop them. The AI warned that the two copies do not stay in sync until then. Reading the pasted `\d health_profiles`, it noticed `profile_weight_positive` was missing from the check-constraint list and said that could be a truncated paste, so it asked for a catalog query instead of assuming either way.
- My refinement: I treated the missing constraint as an open question to verify, not a fact, and ran the data-equality check before the destructive migration in Phase 6.
- Scope: Understanding the Phase 5 schema state, then a safety check before migration `0005`.
- Blast radius: Dropping the legacy columns is irreversible except from backup. Checked by a `pg_dump` backup and the mismatch query below, both before `migrate`.
- Validation:
  - Command: `SELECT conname FROM pg_constraint WHERE conrelid = 'health_profiles'::regclass ORDER BY conname;`. Expected: contains `health_profiles_completion_percent_check`, `profile_completion_consistent`, `profile_status_is_valid`. Actual: Verified in PostgreSQL catalog.
  - Command (before migration `0005`): the mismatch query comparing legacy columns with the section tables. Expected: `mismatched_profiles = 0`. Actual: `0 mismatches across 5004 profiles`.

### E6: Plan change: three remaining phases reduced to two (2026-10-21, branches `phase-6-member-apis` and `phase-7-audit-docs-ui`, commit `cbfd3b7`)
- Goal: Finish the remaining Week 2 work in two phases instead of three.
- Prompt (verbatim):
  > instead of developing week 2 assignment that is remaining after phase 5 in 3 three phases , lets do in 2 phases, phase 6 and 7. Start phase 6
- What the AI proposed: Phase 6 = the complete data backend (member section APIs, validation, the three-contact rule, admin filters, the contract migration, route-matrix tests). Phase 7 = audit events, OpenAPI docs, the interface, README and merge, delivered in two parts because it was the largest. It stated two assumptions out loud: Phase 7 goes to `main` (my "except the last phase" rule), and the front-end profile screens would be broken on the Phase 6 branch until Phase 7.
- My refinement: I accepted the split and the two-part delivery of Phase 7.
- Scope: Process and ordering; each phase's files are listed in its own commit.
- Blast radius: The Phase 6 contract migration removed the legacy columns while the UI still used them. That was accepted because `main` was not touched until Phase 7B, and checked by the pre-drop SQL comparison and a full test run.
- Validation: Command: `pytest -v` after Phase 6 and after Phase 7. Expected: 0 failures. Actual: 382 passed after Phase 7B.

### E7: CSRF on member login (2026-10-21, branch `phase-8-csrf-and-evidence`, commit `6bd7fff`)
- Goal: Make CSRF protection on member login explicit, and verify both accepted and rejected requests.
- Prompt (verbatim, from the review feedback and my instruction):
  > Add explicit CSRF protection to member login and verify both accepted and rejected requests.
  > Evidence trail and AI workflow: one entry from docs/AI_WORKFLOW.md, with the CSRF change as the “scoped change” example [...] Blast radius in one sentence, and “AI agreement is not a test” [...] The three CSRF test results. lets implement this.
- What the AI proposed: One line, `enforce_csrf(request)`, as the first statement of `UserLoginView.post`, so a rejected request never reaches the credential check. It predicted by analysis that tests logging in through the strict `csrf_client` would break and proposed changing the `login` test helper to fetch a token first. It proposed leaving signup exempt and recording that as a test.
- My refinement: I kept the scope to login only. The reason for the signup exemption is that signup creates no session; that choice is pinned by `test_signup_remains_csrf_exempt_by_decision`.
- Scope: Changed: `accounts/views.py` (1 line), `tests/conftest.py` (`login` helper), `tests/test_auth_user.py` (6 new tests, 7 results), `config/api_docs.py`, `tests/test_api_docs.py`, `README.md`, `docs/openapi.yaml`, `docs/AI_WORKFLOW.md`. Not changed: frontend, signup, refresh, logout, admin flow, JWT settings, models, migrations.
- Blast radius (one sentence): Any client that posts member credentials without a valid CSRF cookie-and-header pair, or with a foreign `Origin`, now receives 403 and no cookies, while the frontend (which already sends the header), signup, refresh, logout and the admin flow are unaffected.
- Validation (the AI's agreement is not evidence; these runs are):
  - Command: `pytest tests/test_auth_user.py -k "member_login or csrf_check_runs or signup_remains" -v`. Evidence file: `docs/evidence/e7-csrf-login-tests.txt`.
    - Rejected, no token. Expected: 403, "CSRF Failed", no `access_token` cookie. Actual: `tests/test_auth_user.py::test_member_login_without_a_csrf_token_is_rejected PASSED [ 14%]`.
    - Rejected, forged token. Expected: 403, no cookies. Actual: `tests/test_auth_user.py::test_member_login_with_a_forged_csrf_token_is_rejected PASSED [ 28%]`.
    - Accepted, valid token. Expected: 200, HttpOnly `access_token` and `refresh_token`. Actual: `tests/test_auth_user.py::test_member_login_with_a_valid_csrf_token_is_accepted PASSED [ 42%]`.
    - Origin check. Expected: foreign origin 403, own origin 200. Actual: `tests/test_auth_user.py::test_member_login_checks_the_origin_header[https://evil.example-403] PASSED [ 57%]`, `tests/test_auth_user.py::test_member_login_checks_the_origin_header[http://testserver-200] PASSED [ 71%]`.
    - Ordering. Expected: 403 without `authenticate` ever being called. Actual: `tests/test_auth_user.py::test_csrf_check_runs_before_credentials_are_examined PASSED [ 85%]`.
  - Command: `pytest -q`. Expected: 0 failed (no regression from the helper change). Actual: `411 passed in 1723.56s (0:28:43)` in `docs/evidence/e7-full-suite-summary.txt`.
  - Manual: browser DevTools, Network, login request shows the `X-CSRFToken` request header; log in as an admin and then as a member in one tab and confirm the member login still succeeds.

### E8: Profile contract alignment (2026-10-24, branch `phase-8b-profile-contract`, commits `2c6c928` and `1a5508a`)
- Goal: Make completion depend only on the required fields, document the optional lifestyle information, and give the demographics and wellness sections Edit and Delete buttons like the contacts.
- Prompt (verbatim, from the review feedback):
  > Bring the profile contract back to the assignment: add contact preference and wellness goals, address the required editing behaviour, and clearly document optional lifestyle information. Extra biometric fields shouldn’t replace required fields.

  Follow-up instruction (verbatim):
  > refer to backend/profile model.py for health profile, check which fields can become optional and which required according to this requirement: clearly document optional lifestyle information. Extra biometric fields shouldn’t replace required fields. So that without these optional feilds , if member fills all required feild then completion badge would become 100%, also add edit and delete buttons for wellness and demographic sectioons as you have included for contact section. try to do these above changings with minimal updations in frontend or backend if possible
- What the AI proposed: An analysis of the existing code first: 10 completion items, 3 of them biometrics (blood group, height, weight), wellness goals optional, no contact-preference field. Then a contract of six required items (date of birth, gender, a contact with a phone, a primary contact, contact preference, wellness goals) with everything else optional and documented; one additive migration; a change to the constants in `completion.py` only (the calculating function untouched); Edit and Delete controls in the shared section component. It also found two silent traps by reading the code: the audit allowlist would reject the new field name, and the Delete action's blank-values table would leave the new field behind.
- My refinement: The AI said it had not seen the assignment's exact wording, so the required/optional split is its decision from my feedback and is isolated to two tuples in `completion.py`. The AI did not add a server rule rejecting a blank required field, because the forms save a whole section and members must be able to save partial progress; Delete is the explicit way to clear a section. I kept `reminder_channel` as optional and added `contact_preference` separately instead of renaming, so no data is lost.
- Scope: Changed: `profiles/models.py`, migration `0006_contact_preference`, `completion.py` (constants), `serializers.py`, `services.py` (one blank value), `audit/services.py` (one allowlist name), `seed_data.py`, one settings line, `lib/options.js`, `lib/sections.js`, `components/SectionForm.js`, `app/profile/page.js`, one admin detail row, README, tests with hard-coded completion numbers. Not changed: authentication, CSRF, permissions, audit design, indexes, contact rules, API paths.
- Blast radius: Completion percentages change for existing profiles (checked with `recalculate_completion --dry-run`, then a second run reporting 0); tests with the old numbers fail until updated (the failures were the map of where the old contract was baked in); the audit and Delete traps are covered by a new audit test and the existing reset tests.
- Validation:
  - Command: `pytest tests/test_completion.py tests/test_member_sections.py -k "required or optional or completion" -v` (evidence file `docs/evidence/e8-contract-tests.txt`). Expected: the six required items alone give 100% COMPLETE with optional fields empty; filling only optional fields gives 0% with six items missing. Actual: `test_the_required_items_alone_reach_one_hundred_percent PASSED` and `test_optional_information_never_counts_towards_completion PASSED`.
  - Command: `pytest -q`. Expected: 0 failed. Actual: 417 passed in `docs/evidence/e8-full-suite-summary-after-debugging.txt`.
  - Command: `python manage.py recalculate_completion --dry-run` after the real run. Expected: `Updated 0 profile(s)`. Actual: `Would update 0 profile(s); would create 0 missing section(s).` in `docs/evidence/e8-recalculate-dry-run.txt`.
  - Manual: new member, fill only the six required items, optional fields blank; the completion card shows 100% and "Everything is filled in." Delete the demographics section: completion drops to 67%.

### E9: Root Profile Lifecycle, Concurrency Locking, and Stable Audit Identifiers (2026-10-31, branch `week2-feedback-implementation`)
- Goal: Implement Week 2 feedback: explicit root-profile creation (`POST /api/profiles/me`) and deletion (`DELETE /api/profiles/me`), fix potential deactivation race condition via PostgreSQL row locking, ensure audit event retention across profile deletion/recreation, and verify full contract matrix.
- Prompt (verbatim):
  > Act like a senior full stack AI engineer. You are working on my existing HealthTech Profile Builder project. Switch to main branch for your analysis but make all changings below in a seperate new branch. Dont modify main branch. Your task is to implement ALL the Week 2 feedback below, verify the changes, save command outputs and results to evidence files, update the documentation, and provide a final verification report.
- What the AI proposed:
  1. Add `POST` (201 create / 409 duplicate) and `DELETE` (204 delete / 404 missing) to `MyProfileView`. Retain 405 for root `PATCH`.
  2. Implement `create_profile` and `delete_profile` in `profiles/services.py`.
  3. Add `PROFILE_CREATED` and `PROFILE_DELETED` actions to `AuditAction` in `audit/models.py` with migration `0002_add_profile_lifecycle_actions.py` to update the check constraint.
  4. Fix deactivation race: add `_assert_profile_is_editable(locked)` inside `_save_section`, `create_contact`, `update_contact`, and `delete_contact` right after acquiring `SELECT FOR UPDATE`.
  5. Add genuine PostgreSQL concurrency test (`tests/test_concurrency.py`) and full 10-step lifecycle test suite (`tests/test_profile_lifecycle.py`).
- My refinement:
  - Verified that `AuditEvent.profile_id` is a plain `BigIntegerField` without a foreign key, ensuring profile deletion preserves audit history without cascade.
  - Documented OpenAPI schema operations for root POST and DELETE with `CSRF_HEADER` parameters in `config/api_docs.py`.
  - Verified that recreation generates a distinct profile ID while retaining all older audit events tied to the original ID.
- Scope:
  - Modified: `backend/audit/models.py`, `backend/profiles/services.py`, `backend/profiles/views.py`, `backend/profiles/urls.py`, `backend/config/api_docs.py`, `backend/tests/test_privilege_matrix.py`, `backend/tests/test_api_docs.py`.
  - Created: `backend/audit/migrations/0002_add_profile_lifecycle_actions.py`, `backend/tests/test_profile_lifecycle.py`, `backend/tests/test_concurrency.py`, `backend/tests/test_csrf_evidence.py`, `backend/tests/verify_pg_constraints.py`, `scripts/capture_evidence.ps1`, `docs/video_script_week2.md`, `docs/accessibility_and_small_screen_checklist.md`, `docs/evidence/week2/`.
  - Not touched: `main` branch, existing model constraints, JWT settings, account password hashing, frontend predictions code.
- Blast radius: Root `POST` and `DELETE` on `/api/profiles/me` change allowed HTTP methods from `GET` to `GET, POST, DELETE, HEAD, OPTIONS` (with `PATCH` explicitly returning 405). Section endpoints remain independent. Service-level lock status check rejects mutations if an admin concurrently deactivates the profile.
- Validation:
  - Command: `pytest tests/test_profile_lifecycle.py -v`. Evidence file: `docs/evidence/week2/profile-lifecycle-tests.txt`. Expected: 24 passed. Actual: 24 passed.
  - Command: `pytest tests/test_concurrency.py -v`. Evidence file: `docs/evidence/week2/concurrency-tests.txt`. Expected: 3 passed. Actual: 3 passed.
  - Command: `pytest tests/test_csrf_evidence.py -v`. Evidence file: `docs/evidence/week2/csrf-rejection-and-acceptance.txt`. Expected: 4 passed. Actual: 4 passed.
  - Command: `pytest tests/test_api_docs.py -v`. Expected: 10 passed. Actual: 10 passed.
  - Database Catalog Inspection: `python -c "import verify_pg_constraints"`. Evidence file: `docs/evidence/week2/pg-catalog-constraints-indexes.txt`. Verified: PostgreSQL 18.1, `fk_count = 0` on `audit_events.profile_id`, `audit_action_is_valid` includes `PROFILE_CREATED` and `PROFILE_DELETED`.
  - Database Row Counts: 5,004 profiles, 50,034 audit events, 0 recalculation mismatches on `recalculate_completion --dry-run`.


### E9: Root Profile Lifecycle, Concurrency Locking, and Stable Audit Identifiers (2026-10-31, branch `week2-feedback-implementation`)
- Goal: Implement Week 2 feedback: explicit root-profile creation (`POST /api/profiles/me`) and deletion (`DELETE /api/profiles/me`), fix potential deactivation race condition via PostgreSQL row locking, ensure audit event retention across profile deletion/recreation, and verify full contract matrix.
- Prompt (verbatim):
  > Act like a senior full stack AI engineer. You are working on my existing HealthTech Profile Builder project. Switch to main branch for your analysis but make all changings below in a seperate new branch. Dont modify main branch. Your task is to implement ALL the Week 2 feedback below, verify the changes, save command outputs and results to evidence files, update the documentation, and provide a final verification report.
- What the AI proposed:
  1. Add `POST` (201 create / 409 duplicate) and `DELETE` (204 delete / 404 missing) to `MyProfileView`. Retain 405 for root `PATCH`.
  2. Implement `create_profile` and `delete_profile` in `profiles/services.py`.
  3. Add `PROFILE_CREATED` and `PROFILE_DELETED` actions to `AuditAction` in `audit/models.py` with migration `0002_add_profile_lifecycle_actions.py` to update the check constraint.
  4. Fix deactivation race: add `_assert_profile_is_editable(locked)` inside `_save_section`, `create_contact`, `update_contact`, and `delete_contact` right after acquiring `SELECT FOR UPDATE`.
  5. Add genuine PostgreSQL concurrency test (`tests/test_concurrency.py`) and full 10-step lifecycle test suite (`tests/test_profile_lifecycle.py`).
- My refinement:
  - Verified that `AuditEvent.profile_id` is a plain `BigIntegerField` without a foreign key, ensuring profile deletion preserves audit history without cascade.
  - Documented OpenAPI schema operations for root POST and DELETE with `CSRF_HEADER` parameters in `config/api_docs.py`.
  - Verified that recreation generates a distinct profile ID while retaining all older audit events tied to the original ID.
- Scope:
  - Modified: `backend/audit/models.py`, `backend/profiles/services.py`, `backend/profiles/views.py`, `backend/profiles/urls.py`, `backend/config/api_docs.py`, `backend/tests/test_privilege_matrix.py`, `backend/tests/test_api_docs.py`.
  - Created: `backend/audit/migrations/0002_add_profile_lifecycle_actions.py`, `backend/tests/test_profile_lifecycle.py`, `backend/tests/test_concurrency.py`, `backend/tests/test_csrf_evidence.py`, `backend/tests/verify_pg_constraints.py`, `scripts/capture_evidence.ps1`, `docs/video_script_week2.md`, `docs/accessibility_and_small_screen_checklist.md`, `docs/evidence/week2/`.
  - Not touched: `main` branch, existing model constraints, JWT settings, account password hashing, frontend predictions code.
- Blast radius: Root `POST` and `DELETE` on `/api/profiles/me` change allowed HTTP methods from `GET` to `GET, POST, DELETE, HEAD, OPTIONS` (with `PATCH` explicitly returning 405). Section endpoints remain independent. Service-level lock status check rejects mutations if an admin concurrently deactivates the profile.
- Validation:
  - Command: `pytest tests/test_profile_lifecycle.py -v`. Evidence file: `docs/evidence/week2/profile-lifecycle-tests.txt`. Expected: 24 passed. Actual: 24 passed.
  - Command: `pytest tests/test_concurrency.py -v`. Evidence file: `docs/evidence/week2/concurrency-tests.txt`. Expected: 3 passed. Actual: 3 passed.
  - Command: `pytest tests/test_csrf_evidence.py -v`. Evidence file: `docs/evidence/week2/csrf-rejection-and-acceptance.txt`. Expected: 4 passed. Actual: 4 passed.
  - Command: `pytest tests/test_api_docs.py -v`. Expected: 10 passed. Actual: 10 passed.
  - Database Catalog Inspection: `python -c "import verify_pg_constraints"`. Evidence file: `docs/evidence/week2/pg-catalog-constraints-indexes.txt`. Verified: PostgreSQL 18.1, `fk_count = 0` on `audit_events.profile_id`, `audit_action_is_valid` includes `PROFILE_CREATED` and `PROFILE_DELETED`.
  - Database Row Counts: 5,004 profiles, 50,034 audit events, 0 recalculation mismatches on `recalculate_completion --dry-run`.