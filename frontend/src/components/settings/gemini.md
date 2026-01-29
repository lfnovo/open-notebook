# Settings Components Module

API key configuration forms for managing provider credentials in Open Notebook. Part of the API Configuration UI feature (Issue #477).

## Purpose

This module provides React components for configuring AI provider API keys directly in the UI. Components handle secure input, connection testing, model synchronization, and migration from environment variables to database storage.

## Component Catalog

### MigrationBanner
**File**: `MigrationBanner.tsx`

Alert component prompting users to migrate API keys from environment variables to database.

```typescript
interface MigrationBannerProps {
  envKeysCount: number  // Number of keys available for migration
}
```

- Shows amber-styled alert when `envKeysCount > 0`
- Uses `useMigrateApiKeys` mutation hook
- Displays loading state during migration
- Returns `null` if no keys to migrate

### ProviderCard
**File**: `ProviderCard.tsx`

Card wrapper displaying provider configuration status with model type badges.

```typescript
type ModelType = 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'

interface ProviderCardProps {
  name: string              // Provider identifier
  displayName: string       // Human-readable name
  isConfigured: boolean     // Whether provider has credentials
  source?: string           // 'database' | 'environment'
  supportedTypes?: ModelType[]  // Model capabilities
  children: React.ReactNode // Form component
}
```

- Colored badges for each model type (language=blue, embedding=purple, tts=amber, stt=teal)
- Configuration status badge (emerald=configured, dashed outline=not configured)
- Source badge showing where credentials are stored
- Opacity reduction when not configured

### SimpleKeyForm
**File**: `SimpleKeyForm.tsx`

Standard form for providers requiring only an API key.

```typescript
interface SimpleKeyFormProps {
  provider: string          // Provider identifier
  isConfigured: boolean     // Has existing credentials
  source?: string           // Credential source
  placeholder?: string      // Input placeholder
  defaultUrl?: string       // Reference API endpoint URL
  docsUrl?: string         // Link to get API key
}
```

- Password input with show/hide toggle
- Default URL display (read-only) with copy button
- External link to provider documentation
- Save/Delete buttons with loading states
- Test Connection and Sync Models actions when configured
- Model count badge showing configured models
- Hint text for environment variable sources

### UrlKeyForm
**File**: `UrlKeyForm.tsx`

Form for providers requiring only a base URL (e.g., Ollama).

```typescript
interface UrlKeyFormProps {
  provider: string          // Provider identifier
  isConfigured: boolean     // Has existing credentials
  source?: string           // Credential source
  defaultUrl?: string       // Placeholder URL
}
```

- URL input field
- Same action patterns as SimpleKeyForm
- No password visibility toggle (URLs are not sensitive)

### AzureKeyForm
**File**: `AzureKeyForm.tsx`

Complex form for Azure OpenAI with per-service endpoint configuration.

```typescript
interface AzureKeyFormProps {
  isConfigured: boolean     // Has existing credentials
  source?: string           // Credential source
}
```

- API key (password input)
- Base endpoint URL
- API version field
- Collapsible service-specific endpoints (LLM, embedding, STT, TTS)
- All fields required for save
- Combines all config into single POST call

### OpenAICompatibleForm
**File**: `OpenAICompatibleForm.tsx`

Form for OpenAI-compatible providers with service type selection.

```typescript
interface OpenAICompatibleFormProps {
  isConfigured: boolean     // Has existing credentials
  source?: string           // Credential source
}
```

- Service type dropdown (llm, embedding, stt, tts)
- Base URL field
- API key (password input)
- Helpful hint text explaining compatible providers
- Delete targets specific service type

### VertexKeyForm
**File**: `VertexKeyForm.tsx`

Form for Google Vertex AI configuration.

```typescript
interface VertexKeyFormProps {
  isConfigured: boolean     // Has existing credentials
  source?: string           // Credential source
}
```

- GCP Project ID field
- Region/Location field
- Service account JSON path field
- Info box with documentation link
- Disabled inputs when from environment
- Hint about container path for credentials file

## Hook Dependencies

All form components use hooks from `@/lib/hooks/use-api-keys`:

| Hook | Purpose |
|------|---------|
| `useSetApiKey` | Mutation for saving credentials |
| `useDeleteApiKey` | Mutation for removing credentials |
| `useTestConnection` | Test provider connectivity |
| `useSyncModels` | Discover available models |
| `useProviderModelCount` | Query model count for badge |
| `useMigrateApiKeys` | Migration mutation (MigrationBanner only) |

## Usage Pattern

```tsx
import { ProviderCard, SimpleKeyForm, ModelType } from '@/components/settings'

const supportedTypes: ModelType[] = ['language', 'embedding']

<ProviderCard
  name="openai"
  displayName="OpenAI"
  isConfigured={status?.openai?.configured ?? false}
  source={status?.openai?.source}
  supportedTypes={supportedTypes}
>
  <SimpleKeyForm
    provider="openai"
    isConfigured={status?.openai?.configured ?? false}
    source={status?.openai?.source}
    defaultUrl="https://api.openai.com/v1"
    docsUrl="https://platform.openai.com/api-keys"
  />
</ProviderCard>
```

## Important Patterns

- **Controlled inputs**: All forms use local state, cleared on successful save
- **Environment fallback display**: When `source === 'environment'`, forms show hint and disable delete
- **Optimistic UI**: Loading spinners on buttons during mutations
- **Connection testing**: Local state tracks test results per provider
- **i18n integration**: All text uses `useTranslation()` hook with `t.apiKeys.*` keys
- **Accessibility**: Password visibility toggles, proper labels, ARIA attributes

## Key Dependencies

- `@/components/ui/*`: Button, Input, Label, Card, Badge, Alert, Collapsible, Select
- `lucide-react`: Icons (Eye, EyeOff, Loader2, Trash2, Plug, RefreshCw, Check, X, etc.)
- `@/lib/hooks/use-translation`: i18n translations
- `@/lib/hooks/use-api-keys`: All API key mutations and queries

## Important Quirks and Gotchas

- **Azure requires all fields**: API key, endpoint, and API version are all mandatory
- **OpenAI Compatible delete is service-specific**: Pass `serviceType` to delete correct configuration
- **Vertex credentials path**: Must be accessible inside container, not host filesystem
- **Test results are local state**: Results clear on page navigation; not persisted
- **Model count badge**: Only shows when `totalModels > 0`
- **Password inputs use autocomplete="off"**: Prevents browser from caching API keys

---

## Pattern Analysis

### Form State Management Pattern
All form components follow a consistent pattern:
1. Local `useState` for form inputs
2. Mutation hooks for API calls
3. Clear state on successful mutation via `onSuccess` callback
4. Disabled state derived from `isPending` of mutations

### Visual Feedback Pattern
Connection test results use a three-state visual:
- Pending: Loader2 spinner
- Success: Green Check icon
- Failure: Red X icon
- Default: Plug icon (not yet tested)

### Conditional Rendering Pattern
Actions section (Test/Sync buttons) only renders when `isConfigured === true`, preventing attempts to test unconfigured providers.

### Badge Color Consistency
Model types use consistent color schemes throughout:
- Language models: Blue palette
- Embedding models: Purple palette
- Text-to-speech: Amber palette
- Speech-to-text: Teal palette

---

## Extension Guidance

### Adding a New Provider Form
1. Analyze existing form components to identify common patterns
2. Determine required fields for the new provider (key only, URL+key, multi-field)
3. Check `api/routers/models.py` for provider-specific validation requirements
4. Create new form extending appropriate base pattern (SimpleKeyForm or custom)
5. Add to index.ts exports

### Adding New Model Type Badge
1. Extend `ModelType` union in `ProviderCard.tsx`
2. Add icon mapping in `TYPE_ICONS` constant
3. Add color mapping in `TYPE_COLORS` constant
4. Add translation key in `typeLabels` record

### Implementing Bulk Configuration Import
Research questions:
- What file formats should be supported (JSON, YAML, .env)?
- How should conflicts with existing configurations be handled?
- Should import validate connections before saving?
- What security measures prevent importing malicious configurations?

### Adding Configuration Export
Research questions:
- Should API keys be exported or only non-sensitive config?
- What format maximizes portability across installations?
- How should export handle environment-sourced vs database-sourced keys?

### Improving Connection Test UX
Research questions:
- Should test results persist across sessions?
- Should automatic periodic re-testing be implemented?
- How to handle partial success (e.g., LLM works but embedding fails)?
- Should detailed error messages include remediation steps?

---

## Agent Task Suggestions

### Task: Add New Provider Form Component
**Assigned Agent**: frontend-agent
**Prerequisites**: API endpoint for new provider exists in backend
**Steps**:
1. Identify required fields from `api/routers/models.py` provider config
2. Choose base pattern (SimpleKeyForm, UrlKeyForm, or custom)
3. Create `NewProviderForm.tsx` following existing patterns
4. Add export to `index.ts`
5. Add translation keys to `lib/locales/en-US/apiKeys.json`
6. Update consuming page to include new form

### Task: Implement Form Validation
**Assigned Agent**: frontend-agent
**Integration Points**: Form components, useSetApiKey hook
**Steps**:
1. Add validation state to form components
2. Implement URL format validation for UrlKeyForm
3. Add API key format hints (e.g., sk-* for OpenAI)
4. Show inline validation errors before submission
5. Integrate with react-hook-form if complexity warrants

### Task: Add Configuration Backup/Restore
**Assigned Agent**: frontend-agent + api-agent
**Integration Points**: Settings components, new API endpoints
**Steps**:
1. **api-agent**: Create `/api/settings/export` and `/api/settings/import` endpoints
2. **frontend-agent**: Add ExportButton component with file download
3. **frontend-agent**: Add ImportDialog with file upload and preview
4. **frontend-agent**: Show confirmation before overwriting existing config
5. Add translation keys for new UI elements

### Task: Improve Test Connection Feedback
**Assigned Agent**: frontend-agent
**Integration Points**: useTestConnection hook, form action sections
**Steps**:
1. Extend TestConnectionResult to include latency/details
2. Display response time on successful connection
3. Show specific error type (auth, network, rate limit)
4. Add retry button for failed tests
5. Consider caching successful test results in session storage

### Task: Add Bulk Provider Configuration
**Assigned Agent**: frontend-agent
**Integration Points**: New component, api-keys hooks
**Steps**:
1. Create BulkConfigForm component
2. Add JSON textarea input for multiple providers
3. Validate structure before submission
4. Show preview of changes before saving
5. Use Promise.all for concurrent saves with error handling

---

## Integration Points for Modifications

### Adding Translation Keys
**Location**: `frontend/src/lib/locales/en-US/apiKeys.json`
**Pattern**: Flat namespace with dot access via `t.apiKeys.keyName`

### Modifying API Key Storage
**Locations**:
- Frontend: `lib/api/api-keys.ts` (API client)
- Frontend: `lib/hooks/use-api-keys.ts` (mutation hooks)
- Backend: `api/routers/api_keys.py` (endpoints)
- Backend: `open_notebook/domain/api_key.py` (model)

### Adding Provider to Models Page
**Location**: Page consuming these components (likely `app/(dashboard)/models/page.tsx`)
**Pattern**: Map over provider configs, render ProviderCard with appropriate form

### Extending Model Type Badges
**Files to Modify**:
1. `ProviderCard.tsx`: Add to ModelType, TYPE_ICONS, TYPE_COLORS
2. Translation files: Add `t.apiKeys.typeNewType` key

### Modifying Connection Test Logic
**Files to Modify**:
1. `use-api-keys.ts`: useTestConnection hook
2. `api/api-keys.ts`: testConnection API call
3. Backend: `api/routers/api_keys.py` test endpoint
4. Backend: `open_notebook/ai/connection_tester.py` actual test logic

### Cache Invalidation Extensions
**Current Keys** (in use-api-keys.ts):
- `API_KEYS_QUERY_KEYS.status`
- `API_KEYS_QUERY_KEYS.envStatus`
- `API_KEYS_QUERY_KEYS.modelCount(provider)`
- `MODEL_QUERY_KEYS.providers`
- `MODEL_QUERY_KEYS.models`

---

## Testing Patterns

```typescript
// Test form submission
render(<SimpleKeyForm provider="openai" isConfigured={false} />)
await userEvent.type(screen.getByLabelText(/api key/i), 'sk-test-key')
await userEvent.click(screen.getByRole('button', { name: /save/i }))
expect(mockSetApiKey.mutate).toHaveBeenCalledWith({
  provider: 'openai',
  data: { api_key: 'sk-test-key' }
})

// Test connection button disabled when not configured
render(<SimpleKeyForm provider="anthropic" isConfigured={false} />)
expect(screen.queryByRole('button', { name: /test/i })).not.toBeInTheDocument()

// Test migration banner visibility
render(<MigrationBanner envKeysCount={3} />)
expect(screen.getByText(/3 keys/i)).toBeInTheDocument()

render(<MigrationBanner envKeysCount={0} />)
expect(screen.queryByRole('alert')).not.toBeInTheDocument()
```
