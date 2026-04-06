# Goal: Fix Source List Auto-Refresh After Adding New Source

## Issue Reference
GitHub Issue: #526

## Problem
When a user adds a new source to a notebook (via URL, file upload, or text), the source list in the notebook page does not auto-refresh. The user sees a toast notification saying "Source Queued" but must manually refresh the browser to see the new source appear in the list.

## Root Cause
The notebook page uses `useNotebookSources()` which queries with key `QUERY_KEYS.sourcesInfinite(notebookId)` = `['sources', 'infinite', notebookId]`.

However, the mutation hooks that create sources only invalidate different query keys:
- `useCreateSource` invalidates `QUERY_KEYS.sources(notebookId)` = `['sources', notebookId]`
- `useFileUpload` invalidates `QUERY_KEYS.sources(variables.notebookId)` = `['sources', notebookId]`

React Query's prefix matching does NOT cascade from `['sources', notebookId]` to `['sources', 'infinite', notebookId]` because the second element differs (`notebookId` vs `'infinite'`).

Note: Other hooks like `useDeleteSource`, `useUpdateSource`, etc. correctly use `queryClient.invalidateQueries({ queryKey: ['sources'] })` which IS a prefix of all source queries and does cascade properly.

## Fix
Add `sourcesInfinite` query key invalidation in both `useCreateSource` and `useFileUpload` hooks in `frontend/src/lib/hooks/use-sources.ts`.

### Key Files
- `frontend/src/lib/hooks/use-sources.ts` - Contains all source mutation hooks (main fix location)
- `frontend/src/lib/api/query-client.ts` - Defines `QUERY_KEYS` including `sourcesInfinite`
- `frontend/src/app/(dashboard)/notebooks/[id]/page.tsx` - Notebook page that uses `useNotebookSources`
- `frontend/src/app/(dashboard)/notebooks/components/SourcesColumn.tsx` - Source list UI component

### Implementation Details

**In `useCreateSource` (line ~89-139)**:
After each `QUERY_KEYS.sources(notebookId)` invalidation, also invalidate `QUERY_KEYS.sourcesInfinite(notebookId)`.

**In `useFileUpload` (line ~195-220)**:
After `QUERY_KEYS.sources(variables.notebookId)` invalidation, also invalidate `QUERY_KEYS.sourcesInfinite(variables.notebookId)`.

### Why This Works
- The backend creates the source record immediately (even for async processing, with title "Processing...")
- The source is linked to the notebook immediately
- So invalidating the query will refetch and show the new source
- `SourceCard` already has `useSourceStatus()` that polls every 2 seconds during processing, so the status will auto-update

### Gotchas
- No need for polling/delays - the source record exists in DB when the API returns
- No need for WebSocket/SSE - simple cache invalidation is sufficient
- The async path creates a minimal source with "Processing..." title that gets updated when processing completes
- `SourceCard` already handles status polling via `useSourceStatus()` hook
