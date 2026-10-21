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

### E1: Initial brief and design decisions (<date from git log>, branch `main`, commit <hash of "Phase 1" commit>)
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
  - Admin session logout really ends the session. Command: the manual PowerShell sequence (admin login, list, view, deactivate, logout, then `GET /api/admin/me`). Expected: the last call fails with 401. Actual (pasted in this chat after Phase 3): `Invoke-RestMethod : {"detail":"Authentication credentials were not provided."}` on the final `Invoke-RestMethod "$base/me" -WebSession $web`, with `4 admin@example.com Demo Admin ADMIN` returned by the login step.
  - Phase 1 database rules and the later phases. Command: `pytest -v` in `backend`. Expected: 0 failures. 

### E2: Wrong virtual environment (ModuleNotFoundError, then ImproperlyConfigured) (<date>, branch `phase-2-or-later`, no code commit)
- Goal: Make `pytest -v` run in the HealthTech project.
- Prompt (verbatim, tracebacks shortened):
  > I am inside .venv and in backend folder, earlier when I run pytest -v , this error come: pytest -v ImportError while loading conftest 'C:\Users\Super\Documents\healthtech-profile-builder\backend\tests\conftest.py'. [...] E   ModuleNotFoundError: No module named 'rest_framework' then I installed: python -m pip install djangorestframework and then again run test command but this error is coming: [...] ..\..\enterprise-ai-assistant\.venv\Lib\site-packages\rest_framework\test.py:141: [...] django.core.exceptions.ImproperlyConfigured: Requested setting REST_FRAMEWORK, but settings are not configured. You must either define the environment variable DJANGO_SETTINGS_MODULE or call settings.configure() before accessing settings. help me understand and fix this bug
- What the AI proposed: The traceback paths point at `enterprise-ai-assistant\.venv`, a different project's environment. That environment lacked `pytest-django`, the plugin that reads `DJANGO_SETTINGS_MODULE` from `pytest.ini`, so Django was never configured. Fix: `deactivate`, activate this project's `venv`, print `sys.executable` to prove which Python is active, then `pip install -r requirements.txt` and re-run.
- My refinement: I accepted leaving the stray `djangorestframework` install in the other project's environment, because it is harmless and its own requirements files are untouched.
- Scope: Environment only. No repository file changed.
- Blast radius: The other project's environment gained one unused package. Nothing in this repository was affected.
- Validation:
  - Command: `python -c "import sys; print(sys.executable)"`. Expected: a path ending in `healthtech-profile-builder\backend\venv\Scripts\python.exe`. Actual: <PASTE>.
  - Command: `pytest -v`. Expected: collection succeeds with 0 failures.

### E3: Nested frontend folders and the Turbopack root error (<date>, branch `main`, Phase 4 commit `b8a1e0b`)
- Goal: Get the Next.js frontend to start after `create-next-app` produced `frontend/frontend`.
- Prompt (verbatim, with the two screenshots described):
  > see inside frontend folder, another frontend folder is created or another next.js app, I have added all code inside this nested frontend app and started this app, now this error is coming as shown in second image. help me understand and solve this isssue

  Screenshot 1: a file tree showing `frontend/frontend/app/admin/...`. Screenshot 2 (Next.js 16.4.2 Turbopack): `Module not found: Can't resolve '../../client/components/redirect-status-code'` in `./frontend/node_modules/next/dist/esm/build/templates/app-page-runtime.js (100:1)`.
- What the AI proposed: Two Next.js projects were nested, each with its own lockfile and `node_modules`. Hypothesis: Turbopack picked the outer folder as the project root while the app ran from the inner one. The AI labelled this as its best reading of the evidence, and gave a fix that also covers a corrupted install: rename the outer folder, move the inner app up, delete `.next` and `node_modules`, run `npm install`.
- My refinement: I kept my code (it was all in the inner app) and removed the outer template copy after checking `next.config.mjs`, `app`, `components` and `lib` were present.
- Scope: Folder structure and dependencies only; the application code was not edited.
- Blast radius: Deleting the old outer folder could lose files if the code had landed there. That is why the fix lists `dir` checks before `Remove-Item`. The repository's `.gitignore` already excluded `node_modules` and `.next`.
- Validation:
  - Command: `npm run dev`, then open `http://localhost:3000`. Expected: the home page renders with no red error overlay. Actual: <PASTE or describe>.
  - Command: `npm run build`. Expected: finishes without errors.

### E4: Wrong management command name (seed_demo_data versus seed_data) (<date>, no code change)
- Goal: Create three fictional demo users.
- Prompt (verbatim output pasted):
  > python manage.py seed_demo_data --count 3
  > Unknown command: 'seed_demo_data'
  > Type 'manage.py help' for usage.
- What the AI proposed: The command is named after its file: `seed_data.py`, so `python manage.py seed_data --count 3`. It listed three checks if the name still failed: the exact file path, both `__init__.py` files, and `profiles` in `INSTALLED_APPS`, and suggested `python manage.py help` to see the command under `[profiles]`.
- My refinement: None needed; the name was the only problem.
- Scope: No files changed.
- Blast radius: None. The seeder is idempotent, so a repeated run creates no duplicates.
- Validation: Command: `python manage.py seed_data --count 3`. Expected: `Created 0 users and 0 profiles with sections.` if those users already exist, otherwise a positive count. Actual: <PASTE>.

### E5: Duplicate columns during expand/migrate/contract, and the unconfirmed weight-constraint check (<date>, branch `phase-5-relational-model`)
- Goal: Understand why demographic and wellness fields appeared on both `health_profiles` and the new section tables.
- Prompt (verbatim question; `\d profile_demographics`, `\d wellness_preferences` and `\d health_profiles` output was pasted):
  > why demographic and wellness table feilds are also included in health profile?
- What the AI proposed: The duplicates were the Week 1 flat columns, kept deliberately because the API still used them (expand, migrate, contract). Phase 6 would switch the API to the new tables and then drop them. The AI warned that the two copies do not stay in sync until then. Reading the pasted `\d health_profiles`, it noticed `profile_weight_positive` was missing from the check-constraint list and said that could be a truncated paste, so it asked for a catalog query instead of assuming either way.
- My refinement: I treated the missing constraint as an open question to verify, not a fact, and ran the data-equality check before the destructive migration in Phase 6.
- Scope: Understanding the Phase 5 schema state, then a safety check before migration `0005`.
- Blast radius: Dropping the legacy columns is irreversible except from backup. Checked by a `pg_dump` backup and the mismatch query below, both before `migrate`.
- Validation:
  - The pasted `\d health_profiles` listed these check constraints: `health_profiles_completion_percent_check`, `profile_completion_consistent`, `profile_height_positive`, `profile_status_is_valid`; the paste ended there. `profile_weight_positive` was not visible.
  - Command: `SELECT conname FROM pg_constraint WHERE conrelid = 'health_profiles'::regclass ORDER BY conname;` Expected: includes `profile_weight_positive`. Actual: <PASTE the list>. (If it is missing, that is a real migration-history gap to fix on its own branch.)
  - Command (before migration `0005`): the mismatch query comparing legacy columns with the section tables. Expected: `mismatched_profiles = 0`. Actual: <PASTE>.

### E6: Plan change: three remaining phases reduced to two (<date>, branches `phase-6-member-apis` and `phase-7-audit-docs-ui`)
- Goal: Finish the remaining Week 2 work in two phases instead of three.
- Prompt (verbatim):
  > instead of developing week 2 assignment that is remaining after phase 5 in 3 three phases , lets do in 2 phases, phase 6 and 7. Start phase 6
- What the AI proposed: Phase 6 = the complete data backend (member section APIs, validation, the three-contact rule, admin filters, the contract migration, route-matrix tests). Phase 7 = audit events, OpenAPI docs, the interface, README and merge, delivered in two parts because it was the largest. It stated two assumptions out loud: Phase 7 goes to `main` (my "except the last phase" rule), and the front-end profile screens would be broken on the Phase 6 branch until Phase 7.
- My refinement: I accepted the split and the two-part delivery of Phase 7.
- Scope: Process and ordering; each phase's files are listed in its own commit.
- Blast radius: The Phase 6 contract migration removed the legacy columns while the UI still used them. That was accepted because `main` was not touched until Phase 7B, and checked by the pre-drop SQL comparison and a full test run.
- Validation: Command: `pytest -v` after Phase 6 and after Phase 7. Expected: 0 failures. The Phase 7B browser walkthrough (15 steps) was the end-to-end check.

### E7: CSRF on member login (<date>, branch `phase-8-csrf-and-evidence`, commit <hash from git log>)
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
    - Rejected, no token. Expected: 403, "CSRF Failed", no `access_token` cookie. Actual: <PASTE the PASSED line for `test_member_login_without_a_csrf_token_is_rejected`>.
    - Rejected, forged token. Expected: 403, no cookies. Actual: <PASTE the PASSED line for `test_member_login_with_a_forged_csrf_token_is_rejected`>.
    - Accepted, valid token. Expected: 200, HttpOnly `access_token` and `refresh_token`. Actual: <PASTE the PASSED line for `test_member_login_with_a_valid_csrf_token_is_accepted`>.
    - Origin check. Expected: foreign origin 403, own origin 200. Actual: <PASTE the two PASSED lines for `test_member_login_checks_the_origin_header`>.
    - Ordering. Expected: 403 without `authenticate` ever being called. Actual: <PASTE>.
  - Command: `pytest -q`. Expected: 0 failed (no regression from the helper change). Actual: <PASTE the last line of `docs/evidence/e7-full-suite-summary.txt`>.
  - Manual: browser DevTools, Network, login request shows the `X-CSRFToken` request header; log in as an admin and then as a member in one tab and confirm the member login still succeeds.

### E8: Profile contract alignment (<date>, status: proposed, not implemented)
- Goal: Align the profile with the assignment's required fields without letting extra biometric fields stand in for them.
- Prompt (verbatim, from the review feedback):
  > Bring the profile contract back to the assignment: add contact preference and wellness goals, address the required editing behaviour, and clearly document optional lifestyle information. Extra biometric fields shouldn’t replace required fields.
- What the AI proposed: An analysis first. In the current code, height, weight and blood group count as 3 of the 10 required completion items, wellness goals is optional, and there is no contact-preference field. A proposed contract: required = date of birth, gender, at least one contact with a phone number, a primary contact, a new `contact_preference` field, and wellness goals; optional (documented, not counted) = activity level, diet preference, sleep goal, reminder channel, notes, height, weight, blood group, country, language. An additive migration for `contact_preference`, a recalculation of stored completion, and a rule that saving a required field as blank returns 400 (clearing stays possible only through the explicit reset action).
- My refinement: The AI said it could not see the exact assignment wording and asked for it, so the field names and editing rules are not final. Not implemented until the wording is confirmed.
- Scope (proposed): `completion.py`, one additive migration, serializers, seed recipes, tests with fixed percentages, front-end section config, README. Not touched: authentication, audit design, indexes.
- Blast radius (proposed): Completion percentages change, so stored values need `recalculate_completion`; checked by `--dry-run` (how many profiles change) and a second run reporting 0.
- Validation: pending implementation. Planned: parametrized completion tests, a test that a blank required field returns 400 and that reset still works, and `recalculate_completion --dry-run`.
