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

## API Keys Module (`api-keys.ts`)

Client functions for managing API provider configurations (keys, base URLs, endpoints) stored in SurrealDB.

### Type Definitions

```typescript
// Status of all configured API keys
interface ApiKeyStatus {
  configured: Record<string, boolean>  // provider -> is configured
  source: Record<string, string>       // provider -> 'database' | 'environment'
}

// Environment variable status
interface EnvStatus {
  [provider: string]: boolean  // provider -> has env var set
}

// Request payload for setting API key
interface SetApiKeyRequest {
  api_key?: string
  base_url?: string
  endpoint?: string
  api_version?: string
  endpoint_llm?: string
  endpoint_embedding?: string
  endpoint_stt?: string
  endpoint_tts?: string
  service_type?: 'llm' | 'embedding' | 'stt' | 'tts'
  // Vertex AI specific
  vertex_project?: string
  vertex_location?: string
  vertex_credentials_path?: string
}

// Migration result from env to database
interface MigrationResult {
  message: string
  migrated: string[]
  skipped: string[]
  errors: string[]
}

// Connection test result
interface TestConnectionResult {
  provider: string
  success: boolean
  message: string
}
```

### API Functions

| Function | Description | Endpoint |
|----------|-------------|----------|
| `getStatus()` | Get configuration status of all providers | `GET /api-keys/status` |
| `getEnvStatus()` | Get which providers have env vars set | `GET /api-keys/env-status` |
| `setKey(provider, data)` | Set/update API key configuration | `POST /api-keys/{provider}` |
| `deleteKey(provider, serviceType?)` | Delete API key configuration | `DELETE /api-keys/{provider}` |
| `migrate()` | Migrate keys from env vars to database | `POST /api-keys/migrate` |
| `testConnection(provider)` | Test provider connectivity | `POST /api-keys/{provider}/test` |

### Usage Example

```typescript
import { apiKeysApi } from '@/lib/api/api-keys'

// Check which providers are configured
const status = await apiKeysApi.getStatus()
if (status.configured['openai']) {
  console.log(`OpenAI configured via ${status.source['openai']}`)
}

// Set a new API key
await apiKeysApi.setKey('anthropic', {
  api_key: 'sk-ant-...',
  base_url: 'https://api.anthropic.com'
})

// Test the connection
const result = await apiKeysApi.testConnection('anthropic')
if (result.success) {
  console.log('Connection successful!')
}

// Delete a key (optionally for specific service type)
await apiKeysApi.deleteKey('openai', 'embedding')
```
