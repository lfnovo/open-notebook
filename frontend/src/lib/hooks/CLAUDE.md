# Hooks Module

React hooks for API data fetching, state management, and complex workflows (chat, streaming, file handling).

## Key Components

- **Query hooks** (`useNotebookSources`, `useSource`, `useSources`): TanStack Query wrappers for source data with infinite scroll and refetch strategies
- **Mutation hooks** (`useCreateSource`, `useUpdateSource`, `useDeleteSource`, `useFileUpload`, `useRetrySource`): Server mutations with toast notifications and cache invalidation
- **Chat hooks** (`useNotebookChat`, `useSourceChat`): Complex session management, context building, and message streaming
- **Streaming hooks** (`useAsk`): SSE parsing for multi-stage Ask workflows (strategy → answers → final answer)
- **Model/config hooks** (`useModels`, `useSettings`, `useTransformations`): Application-level settings and model management
- **Utility hooks** (`useMediaQuery`, `useToast`, `useNavigation`, `useAuth`): UI state and auth checking
- **i18n hook** (`useTranslation`): Proxy-based translation access with `t.section.key` pattern and language switching

## Important Patterns

- **TanStack Query integration**: All data hooks use `useQuery`/`useMutation` with `QUERY_KEYS` for cache consistency
- **Optimistic updates**: Mutations add local state before server response (e.g., notebook chat messages)
- **Cache invalidation**: Broad invalidation of query keys on mutations (e.g., `['sources']` catches all source queries)
- **Auto-refetch on return**: `refetchOnWindowFocus: true` on frequently-changing data (sources, notebooks)
- **Manual refetch controls**: Hooks return `refetch()` for parent components to trigger refresh
- **SSE streaming pattern**: `useAsk` manually parses newline-delimited JSON from `/api/search/ask`; handles incomplete buffers
- **Status polling**: `useSourceStatus` auto-refetches every 2s while `status === 'running' | 'queued' | 'new'`
- **Context building**: `useNotebookChat.buildContext()` assembles selected sources + notes with token/char counts
- **i18n Proxy pattern**: `useTranslation` returns `t` object with Proxy; access `t.section.key` instead of `t('section.key')`

## Key Dependencies

- `@tanstack/react-query`: Data fetching and caching
- `sonner`: Toast notifications
- `@/lib/api/*`: API module exports (sourcesApi, chatApi, searchApi, etc.)
- `@/lib/types/api`: TypeScript response types
- Zustand stores: `useAuthStore`, modal managers

## How to Add New Hooks

1. **Data queries**: Create `useQuery` hook wrapping API call; use `QUERY_KEYS.entityName(id)` for cache key
2. **Mutations**: Create `useMutation` hook with `onSuccess` cache invalidation + toast feedback
3. **Complex state**: Use `useState` + callbacks for local state (see `useAsk`, `useNotebookChat`)
4. **Return shape**: Export object with both state and action functions for composability

## Important Quirks & Gotchas

- **Cache invalidation breadth**: Invalidating `['sources']` affects ALL source queries; be precise if performance matters
- **Optimistic updates + error handling**: `useNotebookChat` removes optimistic messages on error; ensure cleanup
- **SSE buffer handling**: `useAsk` keeps incomplete lines in buffer between reads; incomplete JSON silently skipped
- **Model override timing**: `useNotebookChat` stores pending model override if no session exists; applied on session creation
- **Pagination cursor**: `useNotebookSources` uses offset-based pagination; `nextOffset` calculated from page size
- **Status polling race**: `useSourceStatus` may refetch stale data before server catches up; retry logic has 3-attempt limit
- **Keyboard trap in dialogs**: Some hooks manage modal state; ensure Dialog/Modal components handle escape key properly
- **Form data handling**: `useFileUpload` and source creation convert JSON fields to strings in FormData
- **useTranslation depth limit**: Proxy limits nesting to 4 levels; deeper access returns path string as fallback
- **useTranslation loop detection**: >1000 accesses to same key in 1s triggers error and breaks recursion

## Testing Patterns

```typescript
// Mock API
const mockApi = {
  list: vi.fn().mockResolvedValue([...])
}

// Test hook with QueryClientProvider + wrapper
render(<Component />, { wrapper: QueryClientProvider })

// Assert mutations trigger cache invalidation
await waitFor(() => expect(queryClient.invalidateQueries).toHaveBeenCalled())
```
