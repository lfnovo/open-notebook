# Permission Design Closure Plan

> Status: implementation batch closed for model/runtime permissions

This plan closes the gap between `docs/7-DEVELOPMENT/permission-design.md` and the current codebase.

## 2026-05-05 End-of-day Closure Summary

Today's user enhancement batch is closed on branch `codex/user-enhancement`.

Closed product and permission scope:

- Implemented the three current permission levels:
  - System admin manages system models, credentials/API keys, transformations, global settings, advanced tools, users, teams, and audit surfaces.
  - Team owner/admin manages team members and team defaults within system-admin-provided model/transformation availability.
  - Ordinary users and team members use notebooks, sources, notes, chat, search, and public/team/private content without configuring system or team model inventory.
- Enforced team-aware runtime model behavior for chat, embedding, transformation, tools, and large-context defaults.
- Blocked ordinary users/team members from bypassing effective system/team defaults through explicit model overrides.
- Preserved the policy that available models and available transformations are configured only by system admins; team admins select defaults from allowed options but do not configure inventory.
- Added team/member visibility in navigation: team members see team membership; team managers see editable team management affordances.
- Closed notebook ownership rules for team notebooks:
  - Non-owner team members cannot delete notebooks, remove sources from notebooks, delete sources from notebook context, delete chat sessions, edit/delete notes, archive notebooks, edit notebook title/description, or use notebook management action menus.
  - Destructive action menus are disabled at the trigger level, not only inside the menu.
- Closed source ownership rules:
  - Source cards and source details show destructive/management actions only when the current user can manage the source.
  - Source delete remains stricter than general management because public/referenced source delete policy can block deletion even for the owner.
  - Source detail opened from a notebook modal hides the top-right action menu so it does not overlap the dialog close button; the standalone source page keeps the action menu.
- Added creator display on notebook cards using the creator profile login instead of raw owner IDs.
- Fixed source list counts for insights and references.
- Fixed source deletion and notebook-source removal permission handling in both list and notebook detail contexts.
- Removed the extra password-change UI from the system settings page while keeping profile fields for language and theme.
- Added lazy audit log behavior and UI scrolling/pagination support for audit log review.
- Fixed profile/team state refresh after switching users.
- Fixed public/home navigation and unauthenticated public browsing:
  - Public page no longer uses the authenticated app shell.
  - Public and home navigation use matching guest styling.
  - Hidden create dialogs are mounted only when opened, preventing unauthenticated public pages from firing protected API calls and producing console 401 errors.

Backend closure:

- Added backend chat-session delete ownership checks so team members cannot delete sessions attached to notebooks they do not own by bypassing the frontend.
- Kept backend as the permission source of truth; frontend changes are interaction clarity and early blocking.

Frontend closure:

- Consolidated notebook management checks through `canManageNotebook`.
- Added source-detail `showActions` mode for modal vs standalone contexts.
- Disabled `InlineEdit`, visibility controls, action triggers, and session delete controls when the user lacks ownership/management permission.
- Kept public/guest routes free from authenticated-only background queries.

Verification completed:

- Frontend targeted tests for notebook/source permissions, dialog mounting, public/dashboard layout, and source detail action visibility.
- Backend tests for visibility access, chat-session ownership, and notes API.
- `git diff --check`.
- `npm run lint` with 0 errors and existing warnings only.
- `npm run build`.
- Browser console smoke for unauthenticated public routes and authenticated admin routes showed no console errors or failed 4xx/5xx responses after the dialog lazy-mount fix.

Known follow-up work remains tracked in `docs/plans/2026-05-05-user-enhancement-followup-todo.md`.

## Implementation Update

Closed in this batch:

- Added backend team context resolution for notebook/source/share contexts.
- Added team-aware model default resolution for chat, embedding, transformation, tools, and large-context slots.
- Enforced explicit model selection policy so ordinary users can only use the effective system/team default; system admins may still choose any configured model.
- Passed team context through chat, source chat, Ask, transformation, source processing, and source embedding flows.
- Hid arbitrary model selection UI from non-admin users and aligned command palette/setup banner exposure with role visibility.

Remaining product extension:

- Team-scoped non-model settings are still a follow-on surface. The current implementation closes runtime model behavior and permission bypasses while preserving global system settings as the only non-model advanced settings surface.

## Review Summary

The project has the core system/team/user role structure in place, and the current working tree adds team-scoped default model configuration. The remaining closure work is concentrated in three areas:

1. Runtime model resolution now supports team defaults and explicit model override policy.
2. Team-scoped non-model search and advanced settings are not yet modeled.
3. Frontend/global entry points now filter arbitrary model/system configuration affordances by role.

## Key Findings

### 1. Team default models are configurable but not used at runtime

Affected files:

- `open_notebook/ai/models.py`
- `open_notebook/ai/provision.py`
- `api/services/source_service.py`
- `api/routers/search.py`
- `api/routers/chat.py`
- `api/routers/source_chat.py`
- `open_notebook/graphs/chat.py`
- `open_notebook/graphs/source_chat.py`

Current behavior:

- `ModelManager.get_default_model()` reads only global `DefaultModels`.
- `provision_langchain_model()` only accepts explicit `model_id` or global default type.
- Source processing validates only global defaults.
- Search and Ask validate/use global embedding and explicitly supplied model IDs.
- Chat/source chat pass `model_override` straight into graph configuration.

Required behavior:

- Add a team-aware default resolver.
- Derive current team context from resource/workspace context.
- Resolve team default first, then fall back to system default.
- Reject explicit model overrides that are not allowed in the active team context.

### 2. Explicit model overrides currently let users bypass the intended role model

Affected files:

- `api/routers/chat.py`
- `api/routers/source_chat.py`
- `api/routers/search.py`
- `frontend/src/components/source/ModelSelector.tsx`
- `frontend/src/app/(dashboard)/search/page.tsx`

Current behavior:

- Chat sessions and messages accept `model_override`.
- Ask accepts three explicit model IDs.
- Frontend model selector and search advanced model dialog are based on global model/default lists.

Required behavior:

- Normal users should not configure arbitrary models.
- Team members should use team/system defaults unless product explicitly allows per-request choice from a bounded team allowlist.
- If explicit selection remains available, backend must validate the selected model against the active team allowlist or system policy.

### 3. Team search and advanced settings are not modeled yet

Affected files:

- `api/routers/settings.py`
- `open_notebook/domain/content_settings.py`
- `open_notebook/graphs/tools.py`
- `api/routers/search.py`

Current behavior:

- Settings are global.
- Team-level search settings do not exist.
- Tavily/web search settings are global.

Required behavior:

- Add a team-scoped settings model for allowed team overrides.
- Keep system settings as upper bounds/defaults.
- Resolve runtime search/advanced behavior through the same team context mechanism.

### 4. Frontend admin navigation is mostly correct, but command palette and setup banner need role filtering

Affected files:

- `frontend/src/components/layout/AppSidebar.tsx`
- `frontend/src/components/common/CommandPalette.tsx`
- `frontend/src/components/layout/SetupBanner.tsx`

Current behavior:

- Sidebar hides system management from non-admin users.
- Command palette still includes Models, Transformations, Settings, and Advanced as static global items.
- Setup banner links directly to `/settings/api-keys`.

Required behavior:

- Command palette should build items from the same role-aware navigation model as the sidebar.
- Setup banner should only route system admins to model/API-key configuration.
- Non-admin users should see a non-actionable status or contact-admin message when provider migration/configuration is required.

## Closure Tasks

### Task 1: Introduce team context resolution

Goal: provide one backend service that resolves active team context from the current resource/workspace.

Files:

- Create: `api/services/team_context_service.py`
- Modify: `api/routers/chat.py`
- Modify: `api/routers/source_chat.py`
- Modify: `api/routers/search.py`
- Modify: `api/services/source_service.py`
- Test: `tests/test_team_context_service.py`

Implementation notes:

- Resolve team context from notebook/source/share/workspace metadata.
- Do not infer a team from user membership alone when multiple teams exist.
- Return `None` when no team context exists.
- Include tests for no team, one resource team, multiple user teams, and inaccessible team.

Acceptance:

- Runtime callers can request `team_id | None` without duplicating team lookup logic.

### Task 2: Add team-aware model default resolver

Goal: centralize final effective model resolution.

Files:

- Create: `open_notebook/ai/model_resolution.py`
- Modify: `open_notebook/ai/models.py`
- Modify: `open_notebook/ai/provision.py`
- Test: `tests/test_model_resolution.py`

Implementation notes:

- Provide a resolver for slots: `chat`, `embedding`, `transformation`, `tools`, `large_context`.
- If `team_id` is present, read team defaults and allowlist.
- Prefer team default when present and allowed.
- Fall back to system default when team default is unset or invalid.
- Preserve existing global behavior when `team_id` is absent.

Acceptance:

- The same model slot produces system default without team context and team default with team context.
- Invalid team defaults fall back to system default.

### Task 3: Validate explicit model overrides against policy

Goal: prevent normal users or team members from bypassing configured defaults.

Files:

- Modify: `api/routers/chat.py`
- Modify: `api/routers/source_chat.py`
- Modify: `api/routers/search.py`
- Modify: `api/models.py`
- Test: `tests/test_model_override_permissions.py`

Implementation notes:

- Decide whether explicit overrides remain available for normal users.
- If disabled for ordinary users, reject request/session `model_override` with 403.
- If allowed within team scope, verify the model is in the active team's allowlist.
- System admins may continue to use any configured model.

Acceptance:

- Ordinary users cannot call chat/search with arbitrary model IDs.
- Team-scoped override, if allowed, cannot exceed team allowlist.

### Task 4: Wire team-aware model resolution into runtime flows

Goal: make the configured team defaults actually affect use.

Files:

- Modify: `api/services/source_service.py`
- Modify: `open_notebook/graphs/chat.py`
- Modify: `open_notebook/graphs/source_chat.py`
- Modify: `open_notebook/graphs/ask.py`
- Modify: `open_notebook/graphs/knowledge_graph.py`
- Modify: `open_notebook/utils/embedding.py`
- Test: `tests/test_team_model_runtime.py`

Implementation notes:

- Pass `team_id` through graph config/state where needed.
- Use team-aware resolver for chat, transformation, tools, large-context, and embedding slots.
- Keep existing fallback behavior for deployments with no team context.

Acceptance:

- Chat in a team notebook uses team chat default.
- Source processing in a team notebook uses team embedding/transformation/tools defaults.
- Ask/search uses team embedding and team chat defaults.

### Task 5: Model team search and advanced settings

Goal: implement the team-admin-configurable settings promised by the permission design.

Files:

- Create migration for team settings fields or a `team_settings` table.
- Create repository/service for team settings.
- Add team settings schemas in `api/models.py`.
- Add endpoints under `/teams/{team_id}/settings`.
- Add frontend hooks and team page UI.
- Test: `tests/test_team_settings_service.py`

Implementation notes:

- System settings remain authoritative upper bounds/defaults.
- Team settings may only narrow/select allowed behavior.
- Start with search-related settings, then extend to advanced settings if needed.

Acceptance:

- Team owner/admin can configure team search settings within system limits.
- Normal members cannot configure team settings.
- System admin can configure both system settings and team settings.

### Task 6: Close frontend exposure gaps

Goal: align visible UI with backend permissions.

Files:

- Modify: `frontend/src/components/common/CommandPalette.tsx`
- Modify: `frontend/src/components/layout/SetupBanner.tsx`
- Modify: `frontend/src/components/source/ModelSelector.tsx`
- Modify: `frontend/src/app/(dashboard)/search/page.tsx`
- Test: relevant component tests

Implementation notes:

- Reuse sidebar's role-aware navigation logic for command palette.
- Hide or disable arbitrary model selection for normal users unless backend policy allows bounded selection.
- Show team effective defaults instead of global defaults where team context exists.

Acceptance:

- Non-admin command palette does not expose system configuration routes.
- Team members cannot select arbitrary global models from UI.
- Team admins see team defaults/settings but not Provider/API-key controls.

### Task 7: Audit and documentation closure

Goal: make sensitive configuration changes reviewable.

Files:

- Modify: audit logging around model defaults, team defaults, team settings, allowlists.
- Modify: `docs/3-USER-GUIDE/user-management-and-sharing.md`
- Modify: `docs/7-DEVELOPMENT/api-reference.md`
- Test: audit log tests.

Implementation notes:

- Add audit events for team settings and model default changes.
- Ensure metadata records actor, team, changed keys, and new values.

Acceptance:

- Admin can audit who changed system defaults, team allowlists, team defaults, and team settings.

## Recommended Order

1. Task 1: team context resolution.
2. Task 2: effective model resolver.
3. Task 3: explicit override policy.
4. Task 4: runtime wiring.
5. Task 6: frontend exposure cleanup.
6. Task 5: team search/advanced settings.
7. Task 7: audit/docs.

This order closes the highest-risk security and behavior gaps before adding new team settings surface area.

## Verification Suite

Run after each implementation batch:

```bash
uv run pytest tests/test_permission_model.py tests/test_team_service.py tests/test_team_repository.py tests/test_model_resolution.py tests/test_team_context_service.py tests/test_model_override_permissions.py -q
```

Frontend:

```bash
cd frontend
npm test -- --run 'src/app/(dashboard)/settings/teams/page.test.tsx'
npm run lint
```

Known current caveat:

- `frontend/src/lib/locales/index.test.ts` has existing unrelated locale parity/unused-key failures. Fix separately before using it as a gating check.
