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

## Credentials Module (`credentials.ts`)

Client functions for managing AI provider credentials (API keys, base URLs, endpoints) stored encrypted in SurrealDB.

### Type Definitions

```typescript
// Full credential object (api_key never exposed)
interface Credential {
  id: string
  name: string
  provider: string
  modalities: string[]
  has_api_key: boolean
  model_count: number
  base_url?: string
  endpoint?: string
  api_version?: string
  // ... endpoint_llm, endpoint_embedding, endpoint_stt, endpoint_tts, project, location, credentials_path
}

// Request payload for creating/updating credential
interface CreateCredentialRequest {
  name: string
  provider: string
  modalities: string[]
  api_key?: string
  base_url?: string
  // ... other provider-specific fields
}

// Model discovery and registration
interface DiscoverModelsResponse { provider: string; models: DiscoveredModel[]; credential_id: string }
interface RegisterModelsRequest { models: RegisterModelData[] }

// Status and migration
interface CredentialStatus { configured: Record<string, boolean>; source: Record<string, string>; encryption_configured: boolean }
interface EnvStatus { [provider: string]: boolean }
interface MigrationResult { message: string; migrated: string[]; skipped: string[]; errors: string[] }
interface TestConnectionResult { provider: string; success: boolean; message: string }
```

### API Functions

| Function | Description | Endpoint |
|----------|-------------|----------|
| `getStatus()` | Get configuration status of all providers | `GET /credentials/status` |
| `getEnvStatus()` | Get which providers have env vars set | `GET /credentials/env-status` |
| `list(provider?)` | List all credentials (optional filter) | `GET /credentials` |
| `listByProvider(provider)` | List credentials for a provider | `GET /credentials/by-provider/{provider}` |
| `get(credentialId)` | Get a specific credential | `GET /credentials/{credentialId}` |
| `create(data)` | Create a new credential | `POST /credentials` |
| `update(credentialId, data)` | Update a credential | `PUT /credentials/{credentialId}` |
| `delete(credentialId, options?)` | Delete a credential | `DELETE /credentials/{credentialId}` |
| `test(credentialId)` | Test connection using credential | `POST /credentials/{credentialId}/test` |
| `discover(credentialId)` | Discover available models | `POST /credentials/{credentialId}/discover` |
| `registerModels(credentialId, data)` | Register discovered models | `POST /credentials/{credentialId}/register-models` |
| `migrateFromProviderConfig()` | Migrate from legacy ProviderConfig | `POST /credentials/migrate-from-provider-config` |
| `migrateFromEnv()` | Migrate from env vars | `POST /credentials/migrate-from-env` |

### Usage Example

```typescript
import { credentialsApi } from '@/lib/api/credentials'

// Check which providers are configured
const status = await credentialsApi.getStatus()
if (status.configured['openai']) {
  console.log(`OpenAI configured via ${status.source['openai']}`)
}

// Create a new credential
const cred = await credentialsApi.create({
  name: 'My OpenAI Key',
  provider: 'openai',
  modalities: ['language', 'embedding'],
  api_key: 'sk-proj-...'
})

// Test the connection
const result = await credentialsApi.test(cred.id)
if (result.success) {
  console.log('Connection successful!')
}

// Discover and register models
const discovered = await credentialsApi.discover(cred.id)
await credentialsApi.registerModels(cred.id, {
  models: discovered.models.map(m => ({ model_id: m.model_id, name: m.name, type: 'language' }))
})
```
