# Frontend Architecture

Next.js React application providing UI for Open Notebook research assistant. Three-layer architecture: **pages** (Next.js App Router), **components** (feature-specific UI), and **lib** (data fetching, state management, utilities).

## High-Level Data Flow

```
Pages (Next.js) → Components (feature-specific) → Hooks (queries/mutations)
                                                       ↓
                          Stores (auth/modal state) → API module → Backend
```

User interactions trigger mutations/queries via hooks, which communicate with the backend through the API module. Store state (auth, modals) flows back to components via hooks. Child CLAUDE.md files document specific modules in detail:

- **`lib/api/CLAUDE.md`**: Axios client, FormData handling, interceptors
- **`lib/hooks/CLAUDE.md`**: TanStack Query wrappers, SSE streaming, context building
- **`lib/stores/CLAUDE.md`**: Zustand auth/modal state, localStorage persistence
- **`lib/locales/CLAUDE.md`**: Internationalization (i18n) system, translation files
- **`components/ui/CLAUDE.md`**: Radix UI primitives, CVA styling, accessibility

## Architectural Layers

### Pages (`src/app/`) — Next.js App Router
- `(auth)/login`: Authentication entry point
- `(dashboard)/`: Protected routes (notebooks, sources, search, models, etc.)
- Directory-based routing; each `page.tsx` is a route endpoint
- **Key pattern**: Pages call hooks to fetch data, render components with state
- **Router groups** `(auth)`, `(dashboard)` organize routes by feature without affecting URL

### Components (`src/components/`) — Feature-Specific UI
- **layout**: `AppShell.tsx`, `AppSidebar.tsx` — main layout wrapper used by all pages
- **providers**: `ThemeProvider`, `QueryProvider`, `ModalProvider` — app-wide context setup
- **auth**: `LoginForm.tsx` — authentication UI
- **common**: `CommandPalette`, `ErrorBoundary`, `ContextToggle`, `ModelSelector` — shared across pages
- **ui**: Reusable Radix UI building blocks (see child CLAUDE.md)
- **source**, **notebooks**, **search**, **podcasts**: Feature-specific components consuming hooks

**Component composition pattern**: Pages → Feature components → UI components. Feature components handle page-level state (loading, error), UI components remain stateless and styled.

### Lib (`src/lib/`) — Data & State Layer

#### `lib/api/` — Backend Communication
- **`client.ts`**: Central Axios instance with auth interceptor, FormData handling, 10-min timeout
- **`query-client.ts`**: TanStack Query configuration
- **Resource modules** (`sources.ts`, `chat.ts`, `notebooks.ts`, etc.): Endpoint-specific functions returning typed responses
- **Pattern**: All requests go through `apiClient`; auth token auto-added from localStorage

#### `lib/hooks/` — React Query + Custom Logic
- **Query hooks**: `useNotebookSources`, `useSources`, `useSource` — TanStack Query wrappers with cache keys
- **Mutation hooks**: `useCreateSource`, `useUpdateSource`, `useDeleteSource` — mutations with toast feedback + cache invalidation
- **Complex hooks**: `useNotebookChat`, `useSourceChat` — session management, message streaming, context building
- **SSE streaming**: `useAsk` — parses newline-delimited JSON from backend for multi-stage workflows
- **Pattern**: Hooks return `{ data, isLoading, error, refetch }` + action functions; cache invalidation on mutations

#### `lib/stores/` — Application State
- **`auth-store.ts`**: Authentication state (token, isAuthenticated) with 30-second check caching
- **Zustand + persist middleware**: Auto-syncs sensitive state to localStorage
- **Pattern**: Store actions (`login()`, `logout()`, `checkAuth()`) update state; consumed via hooks in components

#### `lib/types/` — TypeScript Definitions
- API request/response shapes, domain models (Notebook, Source, Note, etc.)
- Ensures type safety across API calls and store mutations

#### `lib/locales/` — Internationalization (i18n)
- **Locale files** (`en-US/`, `pt-BR/`, `zh-CN/`, `zh-TW/`, `ja-JP/`): Translation strings organized by feature
- **`i18n.ts`**: i18next configuration with language detection
- **`use-translation.ts`**: Custom hook with Proxy-based `t.section.key` access pattern
- **Pattern**: Components call `useTranslation()` hook; access strings via `t.common.save`, `t.notebooks.title`

## Data & Control Flow Walkthrough

### Example: Notebook Chat
1. **Page** (`notebooks/[id]/page.tsx`) fetches initial data, passes `notebookId` to `ChatColumn` component
2. **Hook call** (`useNotebookChat()`):
   - Queries sessions for notebook via TanStack Query
   - Sets up message state + context building logic
   - Returns `{ messages, sendMessage(), setModelOverride() }`
3. **Component renders**: `ChatColumn` displays messages, text input
4. **User sends message**: Component calls `sendMessage()` hook
5. **Hook execution**:
   - Builds context from selected sources/notes via `buildContext()` helper
   - Calls `chatApi.sendMessage()` (from API module)
   - Client-side optimistic update: adds message to local state before response
6. **Backend response** arrives, TanStack Query updates cache
7. **Cache invalidation** on other source/note mutations ensures stale UI refreshes

### Example: File Upload with Source Creation
1. **Component** (`SourceDialog`) renders form with file picker
2. **Hook** (`useFileUpload`):
   - Converts file to FormData (JSON fields stringified)
   - Calls `sourcesApi.create()` with FormData
   - API client interceptor deletes Content-Type header (lets browser set multipart boundary)
3. **Toast notifications** show progress
4. **Cache invalidation** on success: `queryClient.invalidateQueries(['sources'])`
5. **Related queries** auto-refetch: notebooks, sources list, etc.

## Key Patterns & Cross-Layer Coordination

### Caching & Invalidation
- **Query keys**: `QUERY_KEYS.notebook(id)`, `QUERY_KEYS.sources(notebookId)` — hierarchical structure
- **Broad invalidation**: `['sources']` invalidates all source queries; trade-off between accuracy + performance
- **Auto-refetch**: `refetchOnWindowFocus: true` on frequently-changing data (sources, notebooks)

### Auth & Protected Routes
- **Proxy** (`src/proxy.ts`): Redirects root `/` to `/notebooks`
- **Auth store**: Validates token via `/notebooks` API call (actual validation, not JWT decode)
- **Interceptor**: Adds `Bearer {token}` to all requests; 401 response clears auth and redirects to login

### Modal State Management
- **Modal hooks**: Components query modal state from stores
- **Context**: Modals pass data (e.g., notebook ID) to child components
- **Pattern**: One store per modal type; triggered by button clicks + data passing via hook arguments

### Error Handling
- **API errors**: All request failures propagate to consuming code; components show toast notifications
- **Toast feedback**: Mutations show success/error toasts (from `sonner` library)
- **Error boundary**: App-level error boundary catches React render errors; shows fallback UI

### FormData Handling
- **JSON fields**: Nested objects (arrays, objects) must be JSON stringified before FormData
- **Content-Type header**: Removed by interceptor for FormData requests (lets browser set boundary)
- **Example**: `sources` array converted to string via `JSON.stringify()` before appending to FormData

## Component Organization Within Features

- **Feature folders** (`source/`, `notebooks/`, `podcasts/`): Group related components
- **Composition**: Larger components nest smaller ones; no deep prop drilling (state lifted to hooks)
- **Dialog patterns**: Features define dialog components for inline actions (edit, create, delete)
- **Props**: Components accept data + action callbacks from parent or hooks

## Providers & Context Setup

**Root layout** (`app/layout.tsx`) wraps app with (outermost → innermost):
1. `ErrorBoundary` — React error boundary (catches all render errors)
2. `ThemeProvider` — next-themes for light/dark mode
3. `QueryProvider` — TanStack Query client
4. `I18nProvider` — i18next initialization and language loading overlay
5. `ConnectionGuard` — checks backend connectivity on startup
6. `Toaster` — sonner toast notification system (inside ConnectionGuard)

## Important Gotchas & Design Decisions

- **Token storage**: Stored in localStorage under `auth-storage` key (Zustand persist); consumed by API interceptor
- **Base URL discovery**: API client fetches base URL from runtime config on first request (async; can be slow on startup)
- **Optimistic updates**: Chat messages added to state before server confirmation; removed on error
- **Modal lifecycle**: Dialogs not auto-reset; parent must clear form state after submit
- **Focus management**: Dialog auto-focuses first input; can cause layout shifts if inputs are conditional
- **Cache invalidation breadth**: Trade-off between precision + simplicity; broad invalidation simpler but may over-fetch

## How to Add a New Feature

1. **Create page**: `app/(dashboard)/feature/page.tsx` — calls hooks, renders components
2. **Create feature components**: `components/feature/` — compose UI + business logic
3. **Add hooks** (if data needed): `lib/hooks/useFeature.ts` — TanStack Query wrapper
4. **Add API module** (if backend call needed): `lib/api/feature.ts` — resource-specific functions
5. **Add types**: `lib/types/api.ts` — request/response shapes
6. **Use UI components**: Import from `components/ui/` for consistent styling
7. **Handle auth**: Middleware redirects unauthenticated users; no special handling needed in component

## Testing

- **Hooks**: Mock API functions, wrap in `QueryClientProvider`, assert query/mutation behavior
- **Components**: Mock hooks via `vi.fn()`, test rendering + user interactions
- **API calls**: Mock `axios` interceptors; test request/response shapes
- **Stores**: Mock store state, test mutations via `act()`, assert state changes

See child CLAUDE.md files for module-specific testing patterns.
