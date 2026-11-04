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

### E8: Profile contract alignment (<date from git log>, branch `phase-8b-profile-contract`, commit <hash from git log>)
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
  - Command: `pytest tests/test_completion.py tests/test_member_sections.py -k "required or optional or completion" -v` (evidence file `docs/evidence/e8-contract-tests.txt`). Expected: the six required items alone give 100% COMPLETE with optional fields empty; filling only optional fields gives 0% with six items missing. Actual: `test_the_required_items_alone_reach_one_hundred_percent` and `test_optional_information_never_counts_towards_completion`.
  - Command: `pytest -q`. Expected: 0 failed. Actual:`docs/evidence/e8-full-suite-summary.txt`.
  - Command: `python manage.py recalculate_completion --dry-run` after the real run. Expected: `Updated 0 profile(s)`. 
  - Manual: new member, fill only the six required items, optional fields blank; the completion card shows 100% and "Everything is filled in." Delete the demographics section: completion drops to 67%.


### E10: Member-only predictions authentication and admin access removal (2026-11-01, branch `phase-13-predictions-auth-fix`)
- Goal: Fix predictions page returning 403 Forbidden for authenticated members on `GET /api/v1/ml/model`, remove admin access to predictions through `admin/predictions` URL and backend implementation, and ensure administrators cannot access the member's prediction page.
- Prompt (verbatim, secrets removed):
  > You are a senior expert full stack AI Engineer. Analyze why predictions page is giving: GET http://localhost:3000/api/v1/ml/model 403 (Forbidden) and button: sign in is shown. although member has logged in and I can see access token and csrf token in cookie section. resolve this isssue so that model can be loaded. Also remove admin  access to predictions page through admin/predictions url and backend implementation for this. And admin should not be able to access member's prediction page. first analyze how profile page of member is guarded from admin access. Except these changings dont do any other change or change previous functionalities.  merge all files or commits of phase-12-dashboard-docs branch and then do all above changings in a seperate branch and tell that branch name , this branch should have all commited files of phase 12 and above changings I have asked. If there is any file to commit in phase-12-dashboard-docs branch , then first do this. Then write any tests and evidence of their execution and succesfulness and updating AI documentaion.md file for this new prompt. The acceptance is : after sign in , member would be able to access model related routes so that prediction page and its functionality would be working and Admin should not be able to access this page , even after sign in and admin should not have its prediction page or this functionality. Other existing functionalities should be changed [note: preserved/unchanged]
- What the AI proposed:
  - Root Cause Analysis:
    1. In `backend/config/settings.py`, `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` is configured as an empty list (`[]`).
    2. The views in `backend/predictions/views.py` (`ModelInfoView` and `NoShowPredictView`) did not define `authentication_classes`. Consequently, Django REST Framework performed no authentication on requests to `/api/v1/ml/model` or `/api/v1/ml/no-show/predict`.
    3. Even when a member was signed in with valid `access_token` and `csrftoken` cookies, `request.user` evaluated to `AnonymousUser` (`is_authenticated == False`).
    4. The permission class `IsAdminOrMember` in `predictions/access.py` rejected the unauthenticated user with HTTP 403 Forbidden.
    5. In the frontend component (`NoShowPredictor.js`), status 403 erroneously triggered `setState("signin")`, showing "You need to sign in to use this page" even though the member had already authenticated.
  - Member Profile Guard Pattern:
    Analysis of `backend/profiles/views.py` showed that member routes use `authentication_classes = [CookieJWTAuthentication]` and `permission_classes = [IsStandardUser]`. `CookieJWTAuthentication` strictly reads the HttpOnly `access_token` cookie and verifies CSRF on state-changing requests. `IsStandardUser` strictly verifies `request.user.role == Role.USER`. Administrators, who authenticate via server-side Django session (`admin_session` cookie) with `role == Role.ADMIN`, are rejected with 401 (if no JWT cookie) or 403 ("Standard user access only.").
  - Architecture Fix:
    1. In `backend/predictions/views.py`, created `MemberMLBaseView(APIView)` with `authentication_classes = [CookieJWTAuthentication]` and `permission_classes = [IsStandardUser]`. Refactored `ModelInfoView` and `NoShowPredictView` to inherit from `MemberMLBaseView`.
    2. In `backend/predictions/access.py`, refactored `IsAdminOrMember` to inherit from `IsStandardUser` (requiring `Role.USER`), removing `ADMIN_ROLE` from allowed roles.
    3. In `frontend/lib/mlClient.js`, removed admin CSRF routing, routing all prediction requests strictly through `/api/auth/csrf`.
    4. In `frontend/components/predictions/NoShowPredictor.js`, removed admin title and intro copy. On 401, added check against `/api/admin/me`: if the user is an admin session, state transitions to `"forbidden"` with an explicit message: "Predictions are available for members only. Administrator accounts cannot access this page." On 403, transitions to `"forbidden"`.
    5. In `backend/config/api_docs.py`, added a guard in `document()` so missing view methods do not cause `AttributeError` during Django schema resolution.
    6. In `backend/predictions/tests/test_Api.py`, updated test roles to verify members receive 200 while admins receive 403 Forbidden.
    7. Created `backend/tests/test_predictions_auth.py` containing end-to-end integration tests with Django's test client covering member success, CSRF enforcement, admin session rejection, admin JWT role rejection, anonymous rejection, and non-existence of admin predictions URLs.
- My refinement: Maintained backwards compatibility for `requestPrediction` in `mlClient.js` to accept either payload or `(mode, payload)`. Kept all existing prediction validation, risk band calculation, and feature schemas untouched.
- Scope:
  - Files changed:
    - `backend/predictions/views.py`
    - `backend/predictions/access.py`
    - `backend/predictions/tests/test_Api.py`
    - `backend/config/api_docs.py`
    - `frontend/lib/mlClient.js`
    - `frontend/components/predictions/NoShowPredictor.js`
    - `backend/tests/test_predictions_auth.py` (new)
    - `docs/evidence/e10-predictions-auth-tests.txt` (new evidence)
    - `docs/AI_WORKFLOW.md`
  - Files deliberately untouched: All other profile, accounts, admin dashboard, audit, and ML training pipelines.
- Blast radius: Restricted solely to `/api/v1/ml/*` endpoints and the frontend `/predictions` page. Member profile management, admin profile management, and audit logging are completely unaffected.
- Validation:
  - Unit & Integration Tests: `pytest backend/predictions/tests/ backend/tests/test_predictions_auth.py -v`: 69 passed in 65.20s. Evidence captured in `docs/evidence/e10-predictions-auth-tests.txt`.
  - Member flow verified: Authenticated member with JWT cookie retrieves model info (200) and executes prediction with CSRF (200).
  - Admin access blocked: Authenticated admin session rejected from model info (401) and predictions (401). Admin user with JWT rejected with 403 ("Standard user access only.").
  - Admin predictions route: `GET /api/admin/predictions` confirmed 404 (non-existent).


### E10: Member-only predictions authentication and admin access removal (2026-11-01, branch `phase-13-predictions-auth-fix`)
- Goal: Fix predictions page returning 403 Forbidden for authenticated members on `GET /api/v1/ml/model`, remove admin access to predictions through `admin/predictions` URL and backend implementation, and ensure administrators cannot access the member's prediction page.
- Prompt (verbatim, secrets removed):
  > You are a senior expert full stack AI Engineer. Analyze why predictions page is giving: GET http://localhost:3000/api/v1/ml/model 403 (Forbidden) and button: sign in is shown. although member has logged in and I can see access token and csrf token in cookie section. resolve this isssue so that model can be loaded. Also remove admin  access to predictions page through admin/predictions url and backend implementation for this. And admin should not be able to access member's prediction page. first analyze how profile page of member is guarded from admin access. Except these changings dont do any other change or change previous functionalities.  merge all files or commits of phase-12-dashboard-docs branch and then do all above changings in a seperate branch and tell that branch name , this branch should have all commited files of phase 12 and above changings I have asked. If there is any file to commit in phase-12-dashboard-docs branch , then first do this. Then write any tests and evidence of their execution and succesfulness and updating AI documentaion.md file for this new prompt. The acceptance is : after sign in , member would be able to access model related routes so that prediction page and its functionality would be working and Admin should not be able to access this page , even after sign in and admin should not have its prediction page or this functionality. Other existing functionalities should be changed [note: preserved/unchanged]
- What the AI proposed:
  - Root Cause Analysis:
    1. In `backend/config/settings.py`, `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` is configured as an empty list (`[]`).
    2. The views in `backend/predictions/views.py` (`ModelInfoView` and `NoShowPredictView`) did not define `authentication_classes`. Consequently, Django REST Framework performed no authentication on requests to `/api/v1/ml/model` or `/api/v1/ml/no-show/predict`.
    3. Even when a member was signed in with valid `access_token` and `csrftoken` cookies, `request.user` evaluated to `AnonymousUser` (`is_authenticated == False`).
    4. The permission class `IsAdminOrMember` in `predictions/access.py` rejected the unauthenticated user with HTTP 403 Forbidden.
    5. In the frontend component (`NoShowPredictor.js`), status 403 erroneously triggered `setState("signin")`, showing "You need to sign in to use this page" even though the member had already authenticated.
  - Member Profile Guard Pattern:
    Analysis of `backend/profiles/views.py` showed that member routes use `authentication_classes = [CookieJWTAuthentication]` and `permission_classes = [IsStandardUser]`. `CookieJWTAuthentication` strictly reads the HttpOnly `access_token` cookie and verifies CSRF on state-changing requests. `IsStandardUser` strictly verifies `request.user.role == Role.USER`. Administrators, who authenticate via server-side Django session (`admin_session` cookie) with `role == Role.ADMIN`, are rejected with 401 (if no JWT cookie) or 403 ("Standard user access only.").
  - Architecture Fix:
    1. In `backend/predictions/views.py`, created `MemberMLBaseView(APIView)` with `authentication_classes = [CookieJWTAuthentication]` and `permission_classes = [IsStandardUser]`. Refactored `ModelInfoView` and `NoShowPredictView` to inherit from `MemberMLBaseView`.
    2. In `backend/predictions/access.py`, refactored `IsAdminOrMember` to inherit from `IsStandardUser` (requiring `Role.USER`), removing `ADMIN_ROLE` from allowed roles.
    3. In `frontend/lib/mlClient.js`, removed admin CSRF routing, routing all prediction requests strictly through `/api/auth/csrf`.
    4. In `frontend/components/predictions/NoShowPredictor.js`, removed admin title and intro copy. On 401, added check against `/api/admin/me`: if the user is an admin session, state transitions to `"forbidden"` with an explicit message: "Predictions are available for members only. Administrator accounts cannot access this page." On 403, transitions to `"forbidden"`.
    5. In `backend/config/api_docs.py`, added a guard in `document()` so missing view methods do not cause `AttributeError` during Django schema resolution.
    6. In `backend/predictions/tests/test_Api.py`, updated test roles to verify members receive 200 while admins receive 403 Forbidden.
    7. Created `backend/tests/test_predictions_auth.py` containing end-to-end integration tests with Django's test client covering member success, CSRF enforcement, admin session rejection, admin JWT role rejection, anonymous rejection, and non-existence of admin predictions URLs.
- My refinement: Maintained backwards compatibility for `requestPrediction` in `mlClient.js` to accept either payload or `(mode, payload)`. Kept all existing prediction validation, risk band calculation, and feature schemas untouched.
- Scope:
  - Files changed:
    - `backend/predictions/views.py`
    - `backend/predictions/access.py`
    - `backend/predictions/tests/test_Api.py`
    - `backend/config/api_docs.py`
    - `frontend/lib/mlClient.js`
    - `frontend/components/predictions/NoShowPredictor.js`
    - `backend/tests/test_predictions_auth.py` (new)
    - `docs/evidence/e10-predictions-auth-tests.txt` (new evidence)
    - `docs/AI_WORKFLOW.md`
  - Files deliberately untouched: All other profile, accounts, admin dashboard, audit, and ML training pipelines.
- Blast radius: Restricted solely to `/api/v1/ml/*` endpoints and the frontend `/predictions` page. Member profile management, admin profile management, and audit logging are completely unaffected.
- Validation:
  - Unit & Integration Tests: `pytest backend/predictions/tests/ backend/tests/test_predictions_auth.py -v`: 69 passed in 65.20s. Evidence captured in `docs/evidence/e10-predictions-auth-tests.txt`.
  - Member flow verified: Authenticated member with JWT cookie retrieves model info (200) and executes prediction with CSRF (200).
  - Admin access blocked: Authenticated admin session rejected from model info (401) and predictions (401). Admin user with JWT rejected with 403 ("Standard user access only.").
  - Admin predictions route: `GET /api/admin/predictions` confirmed 404 (non-existent).


### E11: Week 4 Phase 1 – Supervised Learning Comparative Workbench & Hyperparameter Tuning (2026-11-02, branch `week4-phase1-supervised-workbench`)
- Goal: Expand the single-model ML setup into a comparative supervised learning workbench training Logistic Regression, Random Forest, and Gradient Boosting, with GridSearchCV hyperparameter tuning, train-vs-validation overfitting checks, permutation feature importance, confusion matrices, and false positive / negative error analysis.
- Prompt (verbatim, secrets removed):
  > WEEK 4 | Supervised + Unsupervised ML and LLM Foundations [...] Supervised learning: prepare a synthetic appointment-attendance or wellness-engagement dataset; clearly define features, labels, split strategy and leakage checks. Train at least three algorithms: Logistic Regression, Random Forest, and one of Gradient Boosting/XGBoost or SVM. Evaluate classification with confusion matrix, precision, recall, F1, ROC-AUC and PR-AUC when appropriate; compare train versus validation performance, perform stratified cross-validation and tune one model with GridSearchCV or RandomizedSearchCV. Explain feature importance or permutation importance and inspect false positives/negatives. Include a reproducible preprocessing pipeline for imputation, encoding and scaling as appropriate. [...] Acceptance checks: Provide a metrics comparison table for three supervised models, confusion matrix, one tuning experiment and a reproducible saved pipeline. [...] We will implement above task in 4 phases and in different branches , not commiting them to main branch and save evidence of tests and update AI documentation. Our flow for each phase will be: design or build, test and commit. Start phase 1
- What the AI proposed:
  - Dataset & Leakage Protection: Utilized the 20,000 synthetic clinical appointment dataset with 9 input features. Validated that patient-grouped splitting (`StratifiedGroupKFold` / `GroupShuffleSplit`) guarantees zero patient overlap across train (60%), validation (20%), and test (20%) splits.
  - Preprocessing Pipelines: Built scikit-learn `Pipeline` and `ColumnTransformer` setups ensuring train-only fitting. Handled numeric features with median imputation and missingness indicators, scaled continuous values, and applied one-hot encoding for categorical variables.
  - Algorithm Suite:
    1. Baseline Floor: `DummyClassifier`
    2. Linear Model: `LogisticRegression` with L2 regularisation
    3. Bagging Ensemble: `RandomForestClassifier`
    4. Boosting Ensemble: `HistGradientBoostingClassifier`
    5. Tuned Ensemble: `RandomForestClassifier` tuned via `GridSearchCV`
  - Hyperparameter Tuning: Conducted a 3-fold patient-grouped `StratifiedGroupKFold` `GridSearchCV` on the training split, optimizing for PR-AUC across tree depth, estimator counts, and split thresholds (`{'model__max_depth': 6, 'model__min_samples_split': 10, 'model__n_estimators': 100}`, achieving CV PR-AUC = 0.3131).
  - Train vs. Validation Overfitting Analysis: Evaluated all algorithms across Train, Validation, and Test splits. Identified that unconstrained Random Forest overfits (Train-Val gap = +0.4180), whereas depth-constrained tuned Random Forest (+0.0835) and regularized Logistic Regression (-0.0051) generalize stably.
  - Error Analysis: Inspected False Positives (driven by high lead times and past no-show counts where patients attended anyway) and False Negatives (short lead times and clean histories where unexpected personal conflicts caused an absence).
  - API & Artifacts: Added `GET /api/v1/ml/models/comparison` view with member JWT authentication and OpenAPI schema documentation. Generated `backend/ml_artifacts/supervised_comparison.json` and `docs/ml/SUPERVISED_COMPARISON.md`.
- Scope:
  - Files created/modified:
    - `backend/mlcore/config.py`
    - `backend/mlcore/pipeline.py`
    - `backend/mlcore/evaluate.py`
    - `backend/mlcore/supervised_workbench.py`
    - `backend/predictions/views.py`
    - `backend/predictions/urls.py`
    - `backend/mlcore/tests/test_ml_supervised_workbench.py`
    - `backend/predictions/tests/test_comparison_api.py`
    - `docs/ml/SUPERVISED_COMPARISON.md`
    - `backend/ml_artifacts/supervised_comparison.json`
    - `docs/evidence/week4/phase1-supervised-tests.txt`
    - `docs/AI_WORKFLOW.md`
- Blast radius: Isolated to ML core and predictions application. Existing member profile APIs, accounts, admin sessions, and audit logging remain completely unaffected.
- Validation:
  - Test suite: `pytest backend/mlcore/tests/test_ml_supervised_workbench.py backend/predictions/tests/ backend/tests/test_predictions_auth.py -v`: 78 passed (evidence recorded in `docs/evidence/week4/phase1-supervised-tests.txt`).
  - OpenAPI validation: `pytest backend/tests/test_api_docs.py`: 10 passed (100%).


### E12: Week 4 Phase 2 – Unsupervised Learning: Behavioral Clustering & PCA 2D Projection (2026-11-02, branch `week4-phase2-unsupervised-clustering`)
- Goal: Implement an unsupervised learning engine over non-sensitive appointment engagement features, evaluating K-Means and Agglomerative Clustering across $k \in [2, 6]$ via elbow method and silhouette scores, performing 2D PCA projection, profiling clusters in neutral non-clinical terms, providing method comparison and meaningful vs. misleading cluster analysis, and exposing an authenticated API endpoint.
- Prompt (verbatim, secrets removed):
  > Unsupervised learning: run K-Means and one alternative such as DBSCAN or Agglomerative Clustering on non-sensitive profile/engagement features; choose scaling and cluster count using silhouette score and/or elbow method. Perform PCA for 2D visualization; describe each discovered cluster in neutral, non-clinical terms, compare methods, and explain why clusters are exploratory rather than ground-truth categories. [...] Acceptance checks: Show two clustering algorithms, PCA plot, cluster quality analysis and an explanation of meaningful versus misleading clusters. [...] We will implement above task in 4 phases and in different branches , not commiting them to main branch and save evidence of tests and update AI documentation. Our flow for each phase will be: design or build, test and commit. Start phase 1 [...] continue and at end of each phase tell what work you have done in easy words
- What the AI proposed:
  - Feature Selection & Privacy Safeguards: Selected 7 operational engagement features (`lead_time_days`, `scheduled_hour`, `previous_appointments`, `previous_no_shows`, `attendance_ratio`, `distance_km`, `reminder_sent`). Strictly excluded all demographic traits (`age`, `gender`, `race`, `postcode`) and clinical diagnostic data.
  - Preprocessing: Handled missing distance data with median imputation and normalized continuous variables via `StandardScaler`.
  - Clustering Suite:
    1. K-Means: Evaluated across $k \in [2, 6]$, measuring inertia (Elbow curve), silhouette scores, and Davies-Bouldin separation.
    2. Agglomerative Clustering: Evaluated hierarchical Ward linkage across $k \in [2, 6]$, comparing silhouette scores and Davies-Bouldin separation.
  - Method Comparison: Calculated Adjusted Rand Index (ARI = 0.4866), Normalized Mutual Information (NMI = 0.4776), and contingency cross-tabulation between K-Means and Agglomerative cluster assignments.
  - 2D PCA Dimensionality Reduction: Fitted 2 principal components explaining 41.95% of total variance (PC1 = 23.51% driven by past volume and attendance; PC2 = 18.44% driven by lead time and travel distance).
  - Neutral Non-Clinical Archetypes: Described clusters as exploratory operational patterns with tailored scheduling recommendations (`Long-Horizon Advance Planners`, `High-Volume Recurring Clinic Attendees`, `Traditional / Offline Communications Group`, `Emerging / Low-History Visitors`, `Regional Extended-Travel Attendees`).
  - Ethical Analysis: Explicitly documented why clusters are exploratory logistical groupings and must never be interpreted as clinical diagnoses or used to deprioritize healthcare access.
  - API & Artifacts: Added `GET /api/v1/ml/clusters` endpoint with member JWT authentication and OpenAPI docs. Saved `backend/ml_artifacts/clustering_results.json`, `docs/ml/CLUSTERING_ANALYSIS.md`, and static figures (`docs/ml/figures/clustering_elbow_silhouette.png`, `docs/ml/figures/clustering_pca_2d.png`).
- Scope:
  - Files created/modified:
    - `backend/mlcore/config.py`
    - `backend/mlcore/clustering.py` (new)
    - `backend/predictions/views.py`
    - `backend/predictions/urls.py`
    - `backend/mlcore/tests/test_ml_clustering.py` (new)
    - `backend/predictions/tests/test_clustering_api.py` (new)
    - `docs/ml/CLUSTERING_ANALYSIS.md` (new)
    - `docs/ml/figures/clustering_elbow_silhouette.png` (new)
    - `docs/ml/figures/clustering_pca_2d.png` (new)
    - `backend/ml_artifacts/clustering_results.json` (new)
    - `docs/evidence/week4/phase2-clustering-tests.txt` (new evidence)
    - `docs/AI_WORKFLOW.md`
- Blast radius: Strictly scoped to ML clustering module and `GET /api/v1/ml/clusters`. All existing supervised predictions, member profiles, and admin management remain isolated and regression-free.
- Validation:
  - Unit & API Test Suite: `pytest backend/mlcore/tests/test_ml_clustering.py backend/predictions/tests/test_clustering_api.py backend/predictions/tests/test_comparison_api.py backend/mlcore/tests/test_ml_supervised_workbench.py backend/tests/test_predictions_auth.py backend/tests/test_api_docs.py -v`: 36 passed in 152.14s (evidence captured in `docs/evidence/week4/phase2-clustering-tests.txt`).
  - OpenAPI verification: `test_api_docs.py` passed 10/10 with valid schema generation.
  - Security check: Anonymous access returns 401; admin access returns 403; standard member returns 200.

### Entry 13: 2026-11-02 – Week 4 Phase 3: LLM Foundations – Grounded Policy RAG FAQ Assistant
- Objective: Design and implement a safe, educational FAQ assistant over approved fictional clinic policies using Retrieval-Augmented Generation (RAG) with Gemini 1.5 Flash, structured JSON responses, adversarial injection defenses, out-of-scope refusals, medical disclaimers, and a 12-case evaluation harness.
- Action:
  - Fictional Policy Documents: Authored 4 non-sensitive, fictional clinic documents in `backend/rag/docs/` (`booking_policy.txt`, `cancellation_policy.txt`, `privacy_policy.txt`, `ai_disclaimer.txt`).
  - RAG Retrieval Engine: Built `backend/rag/engine.py` with sliding window chunking (350 chars with 60 char overlap), TF-IDF vectorizer (ngram 1-2, 3000 features, sublinear tf), and cosine similarity retrieval without external vector DB dependencies.
  - Multi-Layer Safety & Security:
    - Pre-retrieval adversarial prompt injection detection (`_INJECTION_RE`) catching system-override attempts, jailbreak syntax, and instruction leak requests.
    - Medical query detector (`_MEDICAL_RE`) enforcing strict medical disclaimers and refusal to diagnose or prescribe.
    - System prompt grounding: Zero patient PII transmission, cited source passages, explicit "insufficient information" refusal for unsupported queries.
    - In-process rate limiting (1 sec minimum interval), 30s timeout, token estimation, and mock fallback for deterministic testing without external API credentials.
  - Endpoints & Schemas:
    - Created `POST /api/v1/llm/faq/` for grounded Q&A with structured schema (`answer`, `citations`, `confidence`, `safety_flag`, `out_of_scope`, `approximate_input_tokens`, `approximate_output_tokens`, `model_used`, `latency_ms`).
    - Created `GET /api/v1/llm/faq/evaluate/` returning the live 12-case evaluation matrix.
    - Guarded with `MemberMLBaseView` (member-only JWT; admin and anonymous access strictly rejected).
  - 12-Case Evaluation Suite: Authored `backend/rag/evaluation.py` covering 6 answerable queries, 2 ambiguous queries, 2 out-of-scope queries, 1 medical query, and 1 adversarial injection test. Achieved 12/12 (100%) pass rate.
  - OpenAPI & Schemas: Full `drf-spectacular` schema integration; validated against all OpenAPI constraints.
- Scope:
  - Files created/modified:
    - `backend/rag/__init__.py` (new)
    - `backend/rag/docs/booking_policy.txt` (new)
    - `backend/rag/docs/cancellation_policy.txt` (new)
    - `backend/rag/docs/privacy_policy.txt` (new)
    - `backend/rag/docs/ai_disclaimer.txt` (new)
    - `backend/rag/engine.py` (new)
    - `backend/rag/evaluation.py` (new)
    - `backend/rag/views.py` (new)
    - `backend/rag/urls.py` (new)
    - `backend/rag/tests.py` (new)
    - `backend/config/urls.py`
    - `backend/config/settings.py`
    - `docs/ml/LLM_EVALUATION.md` (new)
    - `docs/evidence/week4/phase3-llm-tests.txt` (new evidence)
    - `docs/AI_WORKFLOW.md`
- Blast radius: Isolated to `backend/rag/` application and `/api/v1/llm/` routes. Existing ML predictions and member profiles remain untouched.
- Validation:
  - Unit & API tests: 27/27 passed (`backend/rag/tests.py` and `backend/tests/test_api_docs.py`).
  - Evaluation Harness: 12/12 test cases passed; report generated in `docs/ml/LLM_EVALUATION.md`.

### Entry 14: 2026-11-02 – Week 4 Phase 4: Multi-Tab Workbench UI & Full Regression Verification
- Objective: Complete the Week 4 user experience by implementing an interactive, multi-tabbed Machine Learning & AI Workbench in Next.js, integrating all supervised, unsupervised, and LLM services with strict member authentication guards, accessible styling, and zero regressions across the codebase.
- Action:
  - Frontend Client Extensions: Added `fetchSupervisedComparison()`, `fetchClusteringAnalysis()`, `askFaq(question)`, and `fetchFaqEvaluation()` to `frontend/lib/mlClient.js` with automated CSRF handling.
  - Multi-Tab Workbench UI:
    - Tab 1: **Single Prediction** (Week 3 interactive model with form presets, instant probability calculations, risk bands, and disclaimers).
    - Tab 2: **Supervised Benchmark** (`SupervisedComparisonTab.js` displaying 5-algorithm comparison table, train/val/test metrics, overfitting gaps, 3-fold StratifiedGroupKFold GridSearchCV tuning parameters, and feature importances).
    - Tab 3: **Patient Clustering (PCA)** (`ClusteringTab.js` displaying K-Means vs Agglomerative metrics, 2D PCA explained variance breakdown, and 6 neutral exploratory persona cards with operational recommendations).
    - Tab 4: **Policy FAQ Assistant (LLM)** (`PolicyFaqTab.js` featuring interactive Q&A assistant with quick prompt buttons, source citations, safety shield indicators, approximate token usage, and collapsible 12-case evaluation benchmark matrix).
  - Security & Authentication Guard: Preserved member-only access across all tabs (anonymous redirected to sign in; admin requests strictly denied with 403 Forbidden).
  - Production Build: Executed `npm run build` in Next.js Turbopack with 0 errors across all 11 routes.
  - Full Regression Testing: Verified full test suite (`backend/mlcore/tests/`, `backend/predictions/tests/`, `backend/rag/tests.py`, `backend/tests/test_predictions_auth.py`, `backend/tests/test_api_docs.py`). Re-enforced strict schema category validation (`handle_unknown="error"`).
- Scope:
  - Files created/modified:
    - `frontend/lib/mlClient.js`
    - `frontend/components/predictions/NoShowPredictor.js`
    - `frontend/components/predictions/SupervisedComparisonTab.js` (new)
    - `frontend/components/predictions/ClusteringTab.js` (new)
    - `frontend/components/predictions/PolicyFaqTab.js` (new)
    - `frontend/components/predictions/predictions.module.css`
    - `backend/mlcore/pipeline.py`
    - `docs/evidence/week4/phase4-regression-tests.txt` (new evidence)
    - `docs/AI_WORKFLOW.md`
- Blast radius: Frontend workbench component updates and ML preprocessor categorical validation guard. All existing accounts, member profiles, and admin capabilities remain regression-free.
- Validation:
  - Frontend build: `npm run build` passed with 0 errors across 11 routes.
  - Full regression test suite: 186/186 passed in 101.51s (evidence documented in `docs/evidence/week4/phase4-regression-tests.txt`).

### Entry 15: 2026-11-04 – Week 5 Phase 1: Advanced RAG, Hybrid Retrieval, Versioning & 20-Question Benchmark
- Objective: Upgrade clinic policy retrieval into an enterprise-grade Advanced RAG system featuring document versioning, live add/update/delete re-indexing, metadata pre-filtering, hybrid BM25 + TF-IDF with Reciprocal Rank Fusion (RRF), chunk-size ablation experiments, and a rigorous 20-question retrieval benchmark evaluating Recall@K, Hit Rate, Groundedness, and Abstention accuracy.
- Action:
  - Advanced Hybrid Engine (`backend/rag/advanced_engine.py`):
    - Implemented `DocumentMetadata` and `PolicyDocument` dataclasses supporting versioning (semver), category, department, target audience, SHA-256 content hashing, and active/soft-delete flags.
    - Implemented lightweight pure-Python/NumPy `BM25Index` (k1=1.5, b=0.75) for exact lexical matching.
    - Built `AdvancedHybridVectorStore` combining lexical BM25 rankings and sublinear TF-IDF cosine similarities via Reciprocal Rank Fusion ($k=60$) with exact entity/numeric token boosting.
    - Provided dynamic mutations: `add_document`, `update_document`, `delete_document(soft=True/False)`, and instantaneous `reindex()` without server reboot.
    - Added metadata pre-filtering across `category`, `department`, and `target_audience`.
    - Executed chunk-size comparison experiment across Small (200 chars), Medium (400 chars), and Large (800 chars), selecting Medium as optimal for 100% hit rate and low token overhead (avg 148.5 tokens).
  - 20-Question Evaluation Benchmark (`backend/rag/advanced_evaluation.py`):
    - Curated 20 labeled clinical policy queries: 10 answerable, 4 ambiguous, 4 out-of-scope, and 2 safety/adversarial.
    - Measured Recall@1, Recall@3, Recall@5, Top-3 Hit Rate, Citation Correctness, Groundedness, and Abstention Accuracy.
    - Demonstrated measurable retrieval improvement:
      - Baseline TF-IDF Abstention Accuracy: **33.3%**
      - Advanced Hybrid RRF Abstention Accuracy: **100.0%** (+66.7% improvement in safely rejecting ungrounded or adversarial queries).
    - Generated automated evaluation artifact: `docs/ml/RAG_ADVANCED_EVALUATION.md`.
  - API Endpoints (`backend/rag/views.py`):
    - `POST /api/v1/llm/rag/search/`: Hybrid search with metadata filtering and OpenAPI documentation.
    - `GET /api/v1/llm/rag/eval-20/`: Admin/Member benchmark execution returning before/after comparison and chunk experiment stats.
    - `POST /api/v1/llm/rag/documents/`: Admin-only document lifecycle management (add, update, delete, reindex) with CSRF protection and auditability.
  - Test Suite (`backend/rag/tests_advanced.py`):
    - 12 comprehensive unit and integration tests covering BM25 indexing, dynamic lifecycle, metadata filtering, chunk experiment, benchmark metrics, and RBAC security.
- Scope:
  - Files created/modified:
    - `backend/rag/advanced_engine.py` (new)
    - `backend/rag/advanced_evaluation.py` (new)
    - `backend/rag/tests_advanced.py` (new)
    - `backend/rag/views.py`
    - `backend/rag/urls.py`
    - `docs/ml/RAG_ADVANCED_EVALUATION.md` (new)
    - `docs/evidence/week5/phase1-advanced-rag-tests.txt` (new evidence)
    - `docs/AI_WORKFLOW.md`
- Blast radius: Isolated to `backend/rag/` advanced modules and new `/api/v1/llm/rag/` endpoints. All Week 1–4 authentication, member profiles, supervised ML predictions, clustering, and existing `/api/v1/llm/faq` endpoints remain unaffected.
- Validation:
  - Phase 1 test suite: 39/39 passed (`backend/rag/tests.py`, `backend/rag/tests_advanced.py`, `backend/tests/test_api_docs.py`). Evidence recorded in `docs/evidence/week5/phase1-advanced-rag-tests.txt`.
