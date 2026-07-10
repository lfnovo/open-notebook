# Frontend Architecture

How the Next.js app is layered and how data flows through it. Normative rules (commands, i18n, gotchas) live in [`frontend/AGENTS.md`](../../frontend/AGENTS.md); this page is the mental model.

## Layers

```
Pages (src/app/, App Router) → Feature components (src/components/) → Hooks (src/lib/hooks/)
                                                                          ↓
                              Stores (src/lib/stores/) → API modules (src/lib/api/) → Backend
```

- **Pages** — route endpoints. Router groups `(auth)` / `(dashboard)` organize routes without affecting URLs. Pages call hooks and render components.
- **Components** — feature folders (`source/`, `notebooks/`, `podcasts/`, …) own page-level state (loading, error); `components/ui/` are stateless Radix UI wrappers styled with Tailwind + CVA.
- **Hooks** (`src/lib/hooks/`) — TanStack Query wrappers. Query hooks return `{ data, isLoading, error, refetch }`; mutation hooks invalidate caches and toast. Complex hooks (`useNotebookChat`, `useAsk`) add session management, context building, SSE streaming.
- **Stores** (`src/lib/stores/`) — Zustand for auth and modal state; `persist` middleware syncs to localStorage (auth token under `auth-storage`).
- **API modules** (`src/lib/api/`) — namespaced typed clients (`sourcesApi.list()`, …) over a single axios instance with auth/FormData/401 interceptors.

Provider tree in `app/layout.tsx` (outermost → innermost): ErrorBoundary → ThemeProvider → QueryProvider → I18nProvider → ConnectionGuard → Toaster.

## Flow walkthrough: notebook chat

1. `notebooks/[id]/page.tsx` passes `notebookId` to `ChatColumn`.
2. `useNotebookChat()` queries sessions, manages message state, returns `{ messages, sendMessage(), setModelOverride() }`.
3. On send: `buildContext()` assembles selected sources/notes (token/char counts), calls `chatApi.sendMessage()`, and applies an **optimistic update** (message added locally, removed on error).
4. Response updates the TanStack Query cache; related source/note mutations elsewhere invalidate broadly so stale UI refreshes.
5. Model override before a session exists is stored as pending and applied on session creation.

## Flow walkthrough: file upload

1. `SourceDialog` collects the file; `useFileUpload` builds FormData — nested JSON fields are stringified.
2. The client interceptor deletes the Content-Type header so the browser sets the multipart boundary.
3. On success, `queryClient.invalidateQueries(['sources'])` refetches lists; `useSourceStatus` polls every 2s while the source is processing.

## Caching strategy

Query keys are hierarchical (`QUERY_KEYS.sources(notebookId)`), but invalidation is deliberately **broad** (`['sources']` catches everything) — a precision/simplicity trade-off. Frequently changing data uses `refetchOnWindowFocus: true`.

## Auth

The token is validated by an actual API call (`/notebooks`), not JWT decoding, with a 30-second cache in the auth store. The response interceptor clears auth and redirects to `/login` on 401. Logout is client-side only.

## Error handling

`getApiErrorMessage()` (`lib/utils/error-handler.ts`) tries an i18n mapping first, then falls back to the backend's descriptive message — which the backend error-classification system already makes user-friendly (see [architecture.md](architecture.md)). Mutations surface errors as toasts; an app-level ErrorBoundary catches render errors.
