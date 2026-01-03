# API Module

Axios-based client and resource-specific API modules for backend communication with auth, FormData handling, and error recovery.

## Key Components

- **`client.ts`**: Central Axios instance with request/response interceptors, auth headers, base URL resolution
- **Resource modules** (`sources.ts`, `notebooks.ts`, `chat.ts`, `search.ts`, etc.): Endpoint-specific functions returning typed responses
- **`query-client.ts`**: TanStack Query client configuration with default options
- **`models.ts`, `notes.ts`, `embeddings.ts`, `settings.ts`**: Additional resource APIs

## Important Patterns

- **Single axios instance**: `apiClient` with 10-minute timeout (for slow LLM operations)
- **Request interceptor**: Auto-fetches base URL from config, adds Bearer auth from localStorage `auth-storage`
- **FormData handling**: Auto-removes Content-Type header for FormData to let browser set multipart boundary
- **Response interceptor**: 401 clears auth and redirects to `/login`
- **Async base URL resolution**: `getApiUrl()` fetches from runtime config on first request
- **Error propagation**: All functions return typed responses via `response.data`
- **Method chaining**: Resource modules export namespaced objects (e.g., `sourcesApi.list()`, `sourcesApi.create()`)

## Key Dependencies

- `axios`: HTTP client library
- `@/lib/config`: `getApiUrl()` for dynamic base URL
- `@/lib/types/api`: TypeScript types for request/response shapes

## How to Add New API Modules

1. Create new file (e.g., `transforms.ts`)
2. Import `apiClient`
3. Export namespaced object with methods:
   ```typescript
   export const transformsApi = {
     list: async () => { const response = await apiClient.get('/transforms'); return response.data }
   }
   ```
4. Add types to `@/lib/types/api` if new response shapes needed

## Important Quirks & Gotchas

- **Base URL delay**: First request waits for `getApiUrl()` to resolve; can be slow on startup
- **FormData fields as JSON strings**: Nested objects (arrays, objects) must be JSON stringified in FormData (e.g., `notebooks`, `transformations`)
- **Timeout for streaming**: 10-minute timeout may not cover very long-running LLM operations; consider extending if needed
- **Auth token management**: Token stored in localStorage `auth-storage` key; uses Zustand persist middleware
- **Headers mutation in interceptor**: Mutating `config.headers` directly; be careful with middleware order
- **No retry logic**: Failed requests not automatically retried; must be handled in consuming code
- **Content-Type header precedence**: FormData interceptor deletes Content-Type after checking; subsequent interceptors won't re-add it

## Usage Example

```typescript
// Basic list
const sources = await sourcesApi.list({ notebook_id: notebookId })

// File upload with FormData
const response = await sourcesApi.create({
  type: 'upload',
  file: fileObj,
  notebook_id: notebookId,
  async_processing: true
})

// With auth token (auto-added by interceptor)
const notes = await notesApi.list()
```
