# Permission Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the confirmed three-level permission model with system administrators, team administrators, and regular users.

**Architecture:** Keep system role (`app_user.role`) separate from team role (`team_member.role`). Backend API authorization is the source of truth; frontend navigation and controls mirror backend permissions. Team-scoped model and transformation availability is represented by explicit allowlist tables and team routes.

**Tech Stack:** FastAPI, Pydantic, SurrealDB migrations and repositories, pytest, Next.js 16, React 19, TypeScript, TanStack Query, Vitest.

---

### Task 1: Protect System Administration API Writes

**Files:**
- Modify: `api/routers/models.py`
- Modify: `api/routers/credentials.py`
- Modify: `api/routers/transformations.py`
- Modify: `api/routers/settings.py`
- Test: `tests/test_permission_model.py`

- [ ] **Step 1: Write failing backend authorization tests**

Add tests that assert regular users cannot call system management endpoints and admins can.

```python
import pytest
from fastapi import HTTPException

from api.auth import CurrentUser, require_admin


@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user():
    user = CurrentUser(id="app_user:regular", username="regular", role="user")

    with pytest.raises(HTTPException) as exc:
        await require_admin(user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Admin privileges required"


@pytest.mark.asyncio
async def test_require_admin_allows_system_admin():
    admin = CurrentUser(id="app_user:admin", username="admin", role="admin")

    result = await require_admin(admin)

    assert result is admin
```

- [ ] **Step 2: Run tests to verify the baseline**

Run: `uv run pytest tests/test_permission_model.py -v`

Expected: tests pass because `require_admin` already exists; this locks the expected error contract before route changes.

- [ ] **Step 3: Apply `require_admin` dependencies to system write routes**

Update route signatures so system management writes require `CurrentUser = Depends(require_admin)`.

Routes to protect:

- `POST /models`
- `DELETE /models/{model_id}`
- `POST /models/{model_id}/test`
- `PUT /models/defaults`
- `GET /models/discover/{provider}`
- `POST /models/sync/{provider}`
- `POST /models/sync`
- `POST /models/auto-assign`
- `POST /credentials`
- `PUT /credentials/{credential_id}`
- `DELETE /credentials/{credential_id}`
- credential discovery, registration, migration, and testing endpoints
- `POST /transformations`
- `PUT /transformations/default-prompt`
- `PUT /transformations/{transformation_id}`
- `DELETE /transformations/{transformation_id}`
- `PUT /settings`

- [ ] **Step 4: Run backend tests**

Run: `uv run pytest tests/test_permission_model.py tests/test_team_service.py tests/test_share_service.py -v`

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
git add api/routers/models.py api/routers/credentials.py api/routers/transformations.py api/routers/settings.py tests/test_permission_model.py
git commit -m "Protect system administration routes"
```

### Task 2: Add Team Allowlist Data and Repository Layer

**Files:**
- Create: `open_notebook/database/migrations/22_team_allowlists.surrealql`
- Create: `open_notebook/database/migrations/22_team_allowlists_down.surrealql`
- Create: `open_notebook/database/repositories/team_allowlist_repository.py`
- Test: `tests/test_team_allowlist_repository.py`

- [ ] **Step 1: Write repository tests with mocked `repo_query`**

Test expected repository calls for replacing model and transformation allowlists, listing allowed items, and rejecting invalid record ids through `ensure_record_id`.

- [ ] **Step 2: Run repository tests to verify failure**

Run: `uv run pytest tests/test_team_allowlist_repository.py -v`

Expected: FAIL because `team_allowlist_repository.py` does not exist.

- [ ] **Step 3: Add migration**

Define `team_model` and `team_transformation` schemafull tables with `team`, `model` or `transformation`, `created_by`, `created`, and unique indexes.

- [ ] **Step 4: Add repository**

Implement:

- `list_team_models(team_id: str) -> list[dict]`
- `replace_team_models(team_id: str, model_ids: list[str], actor_id: str) -> list[dict]`
- `list_team_transformations(team_id: str) -> list[dict]`
- `replace_team_transformations(team_id: str, transformation_ids: list[str], actor_id: str) -> list[dict]`

Use transactions for replace operations.

- [ ] **Step 5: Run repository tests**

Run: `uv run pytest tests/test_team_allowlist_repository.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add open_notebook/database/migrations/22_team_allowlists.surrealql open_notebook/database/migrations/22_team_allowlists_down.surrealql open_notebook/database/repositories/team_allowlist_repository.py tests/test_team_allowlist_repository.py
git commit -m "Add team allowlist repository"
```

### Task 3: Add Team Allowlist Service and Routes

**Files:**
- Modify: `api/models.py`
- Modify: `api/services/team_service.py`
- Modify: `api/routers/teams.py`
- Test: `tests/test_team_service.py`

- [ ] **Step 1: Write failing service tests**

Add tests showing:

- Team owner can replace team model allowlist.
- Team admin can replace team transformation allowlist.
- Team member cannot replace allowlists.
- System team `team:public` cannot be managed.
- Unknown model or transformation ids raise `NotFoundError`.

- [ ] **Step 2: Run service tests to verify failure**

Run: `uv run pytest tests/test_team_service.py -v`

Expected: FAIL because allowlist use cases do not exist.

- [ ] **Step 3: Add request and response models**

Add Pydantic models:

- `TeamModelAllowlistUpdateRequest`
- `TeamModelAllowlistResponse`
- `TeamTransformationAllowlistUpdateRequest`
- `TeamTransformationAllowlistResponse`

- [ ] **Step 4: Add service use cases**

Implement:

- `list_team_models_use_case(team_id, actor)`
- `replace_team_models_use_case(team_id, request, actor)`
- `list_team_transformations_use_case(team_id, actor)`
- `replace_team_transformations_use_case(team_id, request, actor)`

Use existing `_ensure_team_manager` for write operations and reject system teams.

- [ ] **Step 5: Add routes**

Add:

- `GET /teams/{team_id}/models`
- `PUT /teams/{team_id}/models`
- `GET /teams/{team_id}/transformations`
- `PUT /teams/{team_id}/transformations`

- [ ] **Step 6: Run service tests**

Run: `uv run pytest tests/test_team_service.py -v`

Expected: all team service tests pass.

- [ ] **Step 7: Commit**

```bash
git add api/models.py api/services/team_service.py api/routers/teams.py tests/test_team_service.py
git commit -m "Add team model and transformation allowlists"
```

### Task 4: Add Frontend Permission State and Sidebar Rules

**Files:**
- Modify: `frontend/src/lib/api/teams.ts`
- Modify: `frontend/src/lib/hooks/use-teams.ts`
- Modify: `frontend/src/components/layout/AppSidebar.tsx`
- Modify: `frontend/src/components/layout/AppSidebar.test.tsx`

- [ ] **Step 1: Write failing sidebar tests**

Add tests showing:

- Admin sees system management.
- Team manager sees team management but not model credential or advanced system links.
- Regular user sees no management groups.

- [ ] **Step 2: Run sidebar tests to verify failure**

Run: `cd frontend && npm run test -- AppSidebar.test.tsx`

Expected: FAIL because team-manager navigation is not implemented.

- [ ] **Step 3: Add team management capability query**

Expose enough team data to determine whether the current user manages at least one team. Prefer an API-backed hook that treats a visible manageable team as team-management permission.

- [ ] **Step 4: Update sidebar sections**

Split navigation into product, account, team management, and system administration sections.

- [ ] **Step 5: Run sidebar tests**

Run: `cd frontend && npm run test -- AppSidebar.test.tsx`

Expected: all sidebar tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api/teams.ts frontend/src/lib/hooks/use-teams.ts frontend/src/components/layout/AppSidebar.tsx frontend/src/components/layout/AppSidebar.test.tsx
git commit -m "Apply permission-aware sidebar navigation"
```

### Task 5: Add Team Allowlist UI

**Files:**
- Modify: `frontend/src/lib/api/teams.ts`
- Modify: `frontend/src/lib/hooks/use-teams.ts`
- Modify: `frontend/src/app/(dashboard)/settings/teams/page.tsx`
- Test: `frontend/src/app/(dashboard)/settings/teams/page.test.tsx`

- [ ] **Step 1: Write failing UI tests**

Add tests showing the team page renders model and transformation multi-select controls for manageable teams and does not render system model configuration actions.

- [ ] **Step 2: Run UI tests to verify failure**

Run: `cd frontend && npm run test -- 'src/app/(dashboard)/settings/teams/page.test.tsx'`

Expected: FAIL because allowlist UI is missing.

- [ ] **Step 3: Add frontend API methods**

Implement:

- `teamsApi.listModels(teamId)`
- `teamsApi.updateModels(teamId, modelIds)`
- `teamsApi.listTransformations(teamId)`
- `teamsApi.updateTransformations(teamId, transformationIds)`

- [ ] **Step 4: Add hooks**

Implement TanStack Query hooks for reading and updating team model and transformation allowlists.

- [ ] **Step 5: Add team-scoped multi-select UI**

Add model and transformation sections inside the selected team panel. Use checkboxes or multi-select controls backed by system model/transformation list queries.

- [ ] **Step 6: Run UI tests**

Run: `cd frontend && npm run test -- 'src/app/(dashboard)/settings/teams/page.test.tsx'`

Expected: all team page tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/api/teams.ts frontend/src/lib/hooks/use-teams.ts 'frontend/src/app/(dashboard)/settings/teams/page.tsx' 'frontend/src/app/(dashboard)/settings/teams/page.test.tsx'
git commit -m "Add team allowlist management UI"
```

### Task 6: Full Verification

**Files:**
- No direct code edits unless verification finds a bug.

- [ ] **Step 1: Run backend focused tests**

Run: `uv run pytest tests/test_permission_model.py tests/test_team_service.py tests/test_team_allowlist_repository.py tests/test_share_service.py -v`

Expected: all selected backend tests pass.

- [ ] **Step 2: Run frontend focused tests**

Run: `cd frontend && npm run test -- AppSidebar.test.tsx 'src/app/(dashboard)/settings/teams/page.test.tsx'`

Expected: all selected frontend tests pass.

- [ ] **Step 3: Run type checks and lint**

Run:

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run lint
```

Expected: TypeScript passes. Lint exits successfully, allowing existing warnings.

- [ ] **Step 4: Run backend broader smoke tests**

Run: `uv run pytest tests/test_auth_change_password.py tests/test_jwt_auth_security.py tests/test_visibility_access.py -v`

Expected: all selected tests pass.

- [ ] **Step 5: Final status**

Summarize changed files, commits, and verification evidence.
