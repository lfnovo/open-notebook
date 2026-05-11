# Workspace Implementation Review and Closure Plan

> Status: implementation review
> Date: 2026-05-06
> Scope: Review current user/team permission implementation against `docs/7-DEVELOPMENT/workspace-architecture.md` and define the next execution plan.

## Review Summary

The current project has a workable first-stage team permission model, but it still treats `team`, `share_grant`, and `owner_id` as the resource boundary. That model cannot cleanly express the next target behavior:

- Team members can view team resources.
- Team members can add sources and notes.
- Team members can maintain their own contribution content.
- Team members cannot delete team-level resources.
- Team owner/admin can manage team resources and workspace policy.
- System admin sets global upper limits.

The next implementation should not add more special cases to the existing owner/share checks. It should introduce Workspace as the explicit resource boundary and then migrate write permissions to a single capability resolver.

## Findings

### P0: Notes API has no access control

File: `api/routers/notes.py`

The notes router does not receive `Request` or `CurrentUser`, and all read/write/delete endpoints operate directly on notes. `GET /notes` can return all notes when `notebook_id` is omitted, and `GET/PUT/DELETE /notes/{note_id}` do not verify notebook ownership, team access, resource sharing, or creator ownership.

This conflicts with the target rule that team members may edit/delete only their own notes, while other team members can only view them.

Affected lines:

- `get_notes`: lines 13-46
- `create_note`: lines 49-107
- `get_note`: lines 110-130
- `update_note`: lines 133-171
- `delete_note`: lines 174-189

### P0: Notebook write permissions are owner-only

File: `api/routers/notebooks.py`

`_check_notebook_access(..., require_owner=True)` only allows `owner_id == current_user`. This protects deletion, but it also blocks team members from adding sources and notes to a team notebook unless they are the original notebook owner.

This is the central mismatch with the target behavior: members should be able to add content, while destructive notebook operations remain manager-only.

Affected lines:

- owner-only helper: lines 41-59
- create only records `owner_id`: lines 144-158
- add source requires notebook owner: lines 390-410
- remove source requires notebook owner: lines 424-445
- delete notebook requires notebook owner: lines 458-483

### P0: Source mutations are owner-only and not workspace-policy aware

File: `api/services/source_service.py`, `api/routers/sources.py`

Source update, visibility, retry, KG extraction, insight creation, delete, and bulk delete all rely on `check_source_ownership(source.owner_id, user_id)`. That blocks legitimate team workflows such as a team member adding and processing their own source inside a team workspace, and it does not leave room for system global limits.

Affected lines:

- update source: `api/services/source_service.py` lines 463-484
- retry processing: `api/services/source_service.py` lines 528-583
- KG extraction: `api/services/source_service.py` lines 586-617
- insight creation: `api/services/source_service.py` lines 620-655
- delete source: `api/routers/sources.py` lines 417-443
- bulk delete: `api/routers/sources.py` lines 465-510

### P0: Team context is inferred from share grants

File: `api/services/team_context_service.py`

Runtime model resolution still infers team context from a single non-public team share grant. If a resource has no grant or multiple team grants, the resolver falls back or returns `None`. This is intentionally conservative, but it is not a stable ownership model.

The next target is `resource.workspace_id -> workspace.team_id -> team defaults/allowlist`.

Affected lines:

- share grant inference: lines 17-37
- single-team user fallback: lines 56-71
- resource resolver: lines 74-90

### P1: Frontend actions consume coarse `canManageNotebook`

Files:

- `frontend/src/app/(dashboard)/notebooks/[id]/page.tsx`
- `frontend/src/app/(dashboard)/notebooks/components/SourcesColumn.tsx`
- `frontend/src/app/(dashboard)/notebooks/components/NotesColumn.tsx`
- `frontend/src/components/source/SourceDetailContent.tsx`

The notebook detail page computes one `canManageNotebook` flag from `owner_id`, then passes it to sources, notes, and chat. That makes the UI unable to express “member can add note/source, cannot delete notebook, can edit own note, cannot edit others”.

The frontend should move to backend-returned capabilities instead of reimplementing permissions with owner checks.

### P1: Repository list queries still use owner/share visibility as the only access model

Files:

- `open_notebook/database/repositories/notebook_repository.py`
- `open_notebook/database/repositories/source_repository.py`

Notebook/source list queries include owner, public visibility, and share grants. They do not have workspace filters or workspace membership checks.

Affected lines:

- notebook access list: `notebook_repository.py` lines 13-57
- source access list: `source_repository.py` lines 13-67

### P1: Source deletion cascades physical deletion instead of workspace unlink semantics

File: `open_notebook/database/repositories/source_repository.py`

`delete_related_records` removes embeddings, insights, KG records, and all notebook references. In workspace architecture, a team member removing a source from a notebook is different from deleting the source resource from the workspace.

Affected lines:

- source related deletion: lines 130-152

## Execution Plan

### Phase 0: Guard current data before Workspace migration

Goal: Close the highest-risk permission holes without changing the schema.

- Add backend access checks to `api/routers/notes.py`.
- Require readable notebook access for note listing and note creation.
- Record `creator_id` or equivalent note author field in the response path if the schema already supports it; otherwise add it in the Workspace migration phase rather than a temporary note-only field.
- Keep existing owner-only destructive notebook/source behavior until workspace capabilities are available.
- Add regression tests proving non-members cannot read/update/delete notes through direct endpoints.

Suggested tests:

```bash
uv run pytest tests/test_notes_api.py tests/test_permission_model.py -q
```

### Phase 1: Add Workspace schema and repositories

Goal: Create the new resource boundary while preserving old behavior.

Files to add or modify:

- Add migration `open_notebook/database/migrations/27_workspace.surrealql`.
- Add rollback `open_notebook/database/migrations/27_workspace_down.surrealql`.
- Add `open_notebook/database/repositories/workspace_repository.py`.
- Add workspace models to `api/models.py`.
- Add `api/services/workspace_service.py`.
- Add `api/routers/workspaces.py` and register it in `api/main.py`.

Data to model:

- `workspace`: `name`, `type`, `owner_user_id`, `team_id`, `is_default`, `archived`, timestamps.
- `workspace_policy`: per-workspace member permissions.
- `workspace_system_policy`: global upper limits.
- `workspace_id` on `notebook`, `source`, `note`, `chat_session`.
- `creator_id` on resources that do not already have stable creator semantics.

Migration behavior:

- Create one personal default workspace per active user.
- Create one default team workspace per workspace team.
- Backfill private owner resources to owner personal workspace.
- Backfill clearly team-shared resources only when unambiguous.
- Leave ambiguous multi-team shared resources in the owner personal workspace and keep share grants.

### Phase 2: Implement capability resolver

Goal: Replace scattered owner checks with one backend source of truth.

Files to add or modify:

- Add `api/services/workspace_permissions.py`.
- Modify `api/routers/notebooks.py`.
- Modify `api/services/source_service.py`.
- Modify `api/routers/sources.py`.
- Modify `api/routers/notes.py`.
- Modify `api/routers/chat.py` and `api/routers/source_chat.py`.

Capability groups:

- Notebook: `read`, `update_metadata`, `delete`, `add_source`, `remove_source`, `publish_public`.
- Source: `read`, `create`, `update_own`, `process_own`, `create_insight_own`, `remove_from_notebook`, `delete`.
- Note: `read`, `create`, `update_own`, `delete_own`, `update_any`, `delete_any`.
- Chat: `read`, `create`, `delete_own`, `delete_any`.

Default policy:

- Members can read workspace content.
- Members can add sources.
- Members can add notes.
- Members can edit/delete their own notes.
- Members cannot delete notebook.
- Members cannot delete team sources.
- Managers can manage workspace resources.
- System admin can manage global upper limits and override for administration.

### Phase 3: Move runtime model context to Workspace

Goal: Make team default models follow the resource's workspace, not inferred share state.

Files to modify:

- `api/services/team_context_service.py`
- `open_notebook/ai/model_resolution.py`
- `api/routers/chat.py`
- `api/routers/source_chat.py`
- `api/routers/search.py`
- `api/services/source_service.py`

Resolution order:

1. Explicit team id, for admin/system operations only where still needed.
2. Resource `workspace_id`.
3. Workspace `team_id`.
4. Team default model if valid and allowlisted.
5. System default fallback.

This phase closes the current gap where a team owner changes chat defaults but a team member still resolves the system default if the resource has no single share-derived team context.

### Phase 4: Implement move into team workspace

Goal: Support the confirmed product behavior: move first, copy later.

Files to add or modify:

- `api/routers/workspaces.py`
- `api/services/workspace_service.py`
- `open_notebook/database/repositories/workspace_repository.py`
- Frontend workspace selector and move dialog.

Move semantics:

- Moving a notebook updates the notebook workspace.
- Notes and chat sessions under the notebook move with it.
- Personal sources used only by that notebook can move after confirmation.
- Sources already in target workspace remain unchanged.
- Public or externally referenced sources remain linked read-only unless the user explicitly confirms a future copy/move path.
- Copy API is reserved but not implemented in this phase.

### Phase 5: Frontend capability adoption

Goal: Remove coarse owner-based UI decisions.

Files to modify:

- `frontend/src/app/(dashboard)/notebooks/[id]/page.tsx`
- `frontend/src/app/(dashboard)/notebooks/components/SourcesColumn.tsx`
- `frontend/src/app/(dashboard)/notebooks/components/NotesColumn.tsx`
- `frontend/src/app/(dashboard)/notebooks/components/ChatColumn.tsx`
- `frontend/src/components/source/SourceDetailContent.tsx`
- `frontend/src/lib/utils/notebook-permissions.ts`
- `frontend/src/lib/utils/source-delete-eligibility.ts`

Implementation direction:

- Return resource capabilities from notebook/source/note detail APIs.
- Add a `useResourceCapabilities` or resource-specific hooks.
- Show add buttons when `add_source` or `create_note` is true.
- Show edit/delete actions only when corresponding capability is true.
- Keep disabled destructive buttons only where a visible educational cue is useful; otherwise omit unavailable menu items.

### Phase 6: Tests and release gates

Backend minimum:

```bash
uv run pytest tests/test_permission_model.py tests/test_team_context_service.py tests/test_model_resolution.py tests/test_model_policy_service.py tests/test_notes_api.py tests/test_sources_api.py tests/test_chat_permissions.py -q
uv run python scripts/generate_openapi_types.py --check
```

Frontend minimum:

```bash
cd frontend
npm test -- --run 'src/app/(dashboard)/notebooks/components'
npm test -- --run 'src/components/source'
npm run lint
npm run build
```

Manual checks:

- Admin can create team, assign owner, configure allowlist, configure five default models.
- Team owner can set team default chat model.
- Team member opens team notebook and uses the team default chat model.
- Team member can add a source.
- Team member can add a note.
- Team member can edit/delete own note.
- Team member cannot edit/delete another member's note.
- Team member cannot remove/delete team source unless policy permits.
- Team member cannot delete notebook or chat sessions owned by another member.
- Workspace manager can manage resources within system global limits.

## Recommended Execution Order

1. Phase 0: Patch notes API access control.
2. Phase 1: Add Workspace schema and backfill.
3. Phase 2: Add capability resolver and migrate write endpoints.
4. Phase 3: Resolve model context from Workspace.
5. Phase 4: Add move API and move dialog.
6. Phase 5: Switch frontend to backend capabilities.
7. Phase 6: Full regression and release hardening.

The first implementation batch should stop after Phase 0 and Phase 1 tests are green. That gives the project a stable schema foundation before changing all write behaviors.

## Implementation Closure Update

> Updated: 2026-05-06
> Branch: `codex/workspace`

This branch has moved beyond the original first batch and closes the practical Workspace MVP slices that were required for the team-notebook permission redesign.

Completed:

- Phase 0: Notes API now uses workspace-aware capability checks for list, create, read, update, and delete paths.
- Phase 1: Workspace schema, repository, service, router, default personal workspace creation, default team workspace creation, and workspace list/get APIs are implemented.
- Phase 2: Backend resource capabilities now cover notebook, source, note, and chat actions, including creator-aware member rules and workspace policy limits.
- Phase 3: Runtime team context resolution now prefers resource workspace ownership before share-grant fallback, so team model defaults follow team workspace resources.
- Phase 4: Notebook move API and frontend move dialog are implemented for moving resources into a target workspace.
- Phase 5: Frontend notebook/source/note/chat controls consume backend capabilities, and admin/team policy UIs are available for system limits and workspace manager settings.
- Phase 6 gate: OpenAPI generated types were refreshed and checked.

Verified:

```bash
uv run pytest tests/test_permission_model.py tests/test_team_context_service.py tests/test_model_resolution.py tests/test_model_policy_service.py tests/test_notes_api.py tests/test_sources_api.py tests/test_chat_permissions.py -q
uv run python scripts/generate_openapi_types.py --check
cd frontend && npm test -- 'src/app/(dashboard)/notebooks/components'
cd frontend && npm test -- 'src/components/source'
cd frontend && npm run lint
cd frontend && npm run build
```

Notes:

- `npm run lint` currently exits successfully with pre-existing warnings unrelated to the Workspace implementation.
- Full deep-copy/export/import behavior remains future work. The current implementation keeps the confirmed MVP behavior as move-first and preserves API space for future copy/export/import evolution.

## Next Evolution Addendum: Scoped Vector and KG Maintenance

> Added: 2026-05-08
> Reason: Current resources are workspace-aware, but embeddings and KG are still stored in global structures and then permission-filtered at query time.

### Design Decision

The next phase should move embeddings and KG from “global index plus resource filtering” to explicit scope ownership:

- Team workspace embeddings are created and rebuilt per team workspace.
- Team KG is created per team workspace, and teams do not share KG entity identity or relation expansion.
- System KG is separate from team KG and is partitioned by industry tags to prevent one large global knowledge graph from degrading quality, privacy boundaries, and rebuild cost.
- Team owner/admin can run only scoped maintenance for their own team workspace.
- System admin can run system and industry KG maintenance, but team maintenance remains scope-aware and audited.

### Phase 7: Add vector/KG scope model

Goal: Make derived search structures follow the same workspace boundary as resources.

Files to modify:

- Add migration under `open_notebook/database/migrations/`.
- Update `commands/embedding_commands.py`.
- Update `open_notebook/graphs/knowledge_graph.py`.
- Update `open_notebook/database/repositories/search_repository.py`.
- Update `open_notebook/domain/notebook.py`.
- Add/modify tests in `tests/test_search_repository.py`, `tests/test_kg.py`, and new maintenance tests.

Schema changes:

- Add `workspace_id` and `team_id` to `source_embedding`.
- Add `workspace_id` and `team_id` to `source_insight`, or introduce a separate insight embedding table if the current record shape becomes too overloaded.
- Ensure `note.workspace_id` is used when embedding notes; if note embeddings remain inline, search queries must filter by `note.workspace_id`.
- Add `workspace_id`, `team_id`, `scope_type`, and optional `industry_tag_id` to `kg_entity`.
- Add the same scope fields to `kg_relation`.
- Stop using only global slug ids for KG entities. Use scoped ids or generated ids with a unique constraint on `(scope_type, workspace_id, team_id, industry_tag_id, normalized_name, type)`.

Acceptance:

- Two teams extracting entity “Insulin” produce separate KG entities.
- Team A KG search cannot return or traverse Team B KG nodes.
- Team A vector rebuild does not delete or rewrite Team B embeddings.
- Team query embeddings use Team A effective embedding model.
- Personal workspace search continues to use system defaults.

### Phase 8: Split maintenance APIs

Goal: Replace global-only advanced maintenance with scoped APIs that can be safely exposed to team owner/admin.

Backend endpoints:

```http
POST /workspaces/{workspace_id}/maintenance/embeddings/rebuild
POST /workspaces/{workspace_id}/maintenance/kg/rebuild
GET /workspaces/{workspace_id}/maintenance/jobs/{command_id}
POST /system/maintenance/embeddings/rebuild
POST /system/maintenance/kg/rebuild
POST /system/kg/industry-tags/{tag_id}/rebuild
```

Files to add or modify:

- Add `api/routers/workspace_maintenance.py`.
- Keep `api/routers/embedding_rebuild.py` admin-only or deprecate it after the scoped API is available.
- Add service layer for scoped rebuild submission, for example `api/services/workspace_maintenance_service.py`.
- Add scoped command inputs in `commands/embedding_commands.py`.
- Add KG rebuild command input in the KG command module.
- Add frontend team advanced panel under `frontend/src/app/(dashboard)/advanced/page.tsx`.

Permission rules:

- Team owner/admin can rebuild embeddings/KG only for a team workspace they manage.
- Team members cannot run maintenance.
- System admin can run system/industry maintenance.
- System admin observation must not silently mutate personal workspaces.

Acceptance:

- Team owner sees actionable “团队向量重建” and “团队 KG 重建” controls instead of a disabled global advanced page.
- Calling a scoped rebuild with another team workspace id returns 403.
- Rebuild job payload contains `workspace_id`, `team_id`, and selected model ids.
- Audit log records scope, actor, job id, resource counts, and result.

### Phase 9: System KG industry tags

Goal: Keep platform knowledge manageable and queryable by industry instead of a single unbounded global graph.

Files to add or modify:

- Add migration for `industry_tag` and system KG scope metadata.
- Add repository/service/router support for industry tag management.
- Add admin UI for industry tags and system KG rebuild.
- Update KG extraction/import flows so system KG writes require at least one industry tag.

Suggested tags for current product direction:

- `biopharma`
- `life-science`
- `materials`
- `ai-research`
- `enterprise-knowledge`

Acceptance:

- System KG rebuild can target one industry tag.
- System KG search requires explicit industry tags or a configured default tag set.
- Team KG can optionally read selected system industry KG as read-only background, but cannot merge private team nodes into system KG.

## Updated Recommended Execution Order

1. Finish manual validation of the current Workspace MVP.
2. Phase 7: Add vector/KG scope model and migration.
3. Phase 8: Split maintenance APIs and enable team scoped advanced tools.
4. Phase 9: Add system KG industry tags.
5. Return to export/import, artifact abstraction, and copy evolution once derived indexes have clear scope boundaries.
