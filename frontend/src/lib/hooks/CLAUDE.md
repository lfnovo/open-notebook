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

## Credentials Hooks (`use-credentials.ts`)

Hooks for managing AI provider credentials with TanStack Query integration, toast notifications, and cache invalidation.

### Query Keys

```typescript
export const CREDENTIAL_QUERY_KEYS = {
  all: ['credentials'] as const,
  status: ['credentials', 'status'] as const,
  envStatus: ['credentials', 'env-status'] as const,
  byProvider: (provider: string) => ['credentials', 'provider', provider] as const,
  detail: (id: string) => ['credentials', id] as const,
}
```

### Query Hooks

| Hook | Description | Returns |
|------|-------------|---------|
| `useCredentialStatus()` | Get configuration status of all providers | `{ configured, source, encryption_configured }` |
| `useEnvStatus()` | Get which providers have env vars set | `{ [provider]: boolean }` |
| `useCredentials(provider?)` | List all credentials (optional filter) | `Credential[]` |
| `useCredentialsByProvider(provider)` | List credentials for a specific provider | `Credential[]` |
| `useCredential(credentialId)` | Get a specific credential | `Credential` |

### Mutation Hooks

| Hook | Description | Cache Invalidation |
|------|-------------|-------------------|
| `useCreateCredential()` | Create new credential | `all`, `providers` |
| `useUpdateCredential()` | Update credential | `all`, `providers` |
| `useDeleteCredential()` | Delete credential | `all`, `models`, `providers` |
| `useTestCredential()` | Test credential connection | None (stores result locally) |
| `useDiscoverModels()` | Discover models for credential | None |
| `useRegisterModels()` | Register discovered models | `models`, `all` |
| `useMigrateFromEnv()` | Migrate from env vars | `status`, `envStatus`, `models`, `providers` |
| `useMigrateFromProviderConfig()` | Migrate from legacy ProviderConfig | `status`, `envStatus`, `models`, `providers` |

### useTestCredential Details

Returns extended interface with local state management for test results:

```typescript
const {
  testCredential,        // (credentialId: string) => void
  testCredentialAsync,   // (credentialId: string) => Promise<TestConnectionResult>
  isPending,             // boolean
  testResults,           // Record<string, TestConnectionResult>
  clearResult,           // (credentialId: string) => void
} = useTestCredential()
```

### Cache Invalidation Strategy

All mutation hooks invalidate:
- `CREDENTIAL_QUERY_KEYS.all` — refreshes all credential queries (cascades to filtered queries)
- `MODEL_QUERY_KEYS.providers` — refreshes provider list

Delete hook additionally invalidates:
- `MODEL_QUERY_KEYS.models` — refreshes full model list (linked models may be deleted)

Migration hooks additionally invalidate:
- `CREDENTIAL_QUERY_KEYS.status` — refreshes configured/source info
- `CREDENTIAL_QUERY_KEYS.envStatus` — refreshes env var status

### Usage Example

```typescript
import {
  useCredentialStatus,
  useCredentials,
  useCreateCredential,
  useTestCredential,
  useMigrateFromEnv
} from '@/lib/hooks/use-credentials'

function CredentialSettings() {
  const { data: status, isLoading } = useCredentialStatus()
  const { data: credentials } = useCredentials()
  const createCredential = useCreateCredential()
  const { testCredential, testResults, isPending } = useTestCredential()
  const migrateFromEnv = useMigrateFromEnv()

  const handleCreate = () => {
    createCredential.mutate({
      name: 'My OpenAI Key',
      provider: 'openai',
      modalities: ['language', 'embedding'],
      api_key: 'sk-...'
    })
  }

  const handleTest = (credentialId: string) => {
    testCredential(credentialId)
  }

  const handleMigrate = () => {
    migrateFromEnv.mutate()
  }

  return (
    <div>
      {credentials?.map(cred => (
        <div key={cred.id}>
          <span>{cred.name} ({cred.provider})</span>
          <button onClick={() => handleTest(cred.id)} disabled={isPending}>Test</button>
          {testResults[cred.id]?.success && <span>Connected!</span>}
        </div>
      ))}
      <button onClick={handleCreate}>Add Credential</button>
      <button onClick={handleMigrate}>Migrate from .env</button>
    </div>
  )
}
```

### Important Notes

- **Toast notifications**: All mutations show success/error toasts automatically
- **i18n integration**: Toast messages use translation keys from `t.apiKeys.*` and `t.common.*`
- **Error handling**: Uses `getApiErrorKey()` utility to extract error messages from API responses
- **Local test results**: `useTestCredential` stores results in local state (not cached in TanStack Query)
- **Migration feedback**: Migration hooks show different toasts based on migrated/skipped/error counts
