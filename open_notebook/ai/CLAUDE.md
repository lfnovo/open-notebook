# AI Module

Model configuration, provisioning, and management for multi-provider AI integration via Esperanto.

## Purpose

Centralizes AI model lifecycle: database models for model metadata (provider, type), default model configuration, and factory for instantiating LLM/embedding/speech models at runtime with fallback logic.

## Architecture Overview

**Two-tier system**:
1. **Database models** (`Model`, `DefaultModels`): Metadata storage and default configuration
2. **ModelManager**: Factory for provisioning models with intelligent fallback (large context detection, config override)

All models use Esperanto library as provider abstraction (OpenAI, Anthropic, Google, Groq, Ollama, Mistral, DeepSeek, xAI, OpenRouter).

## Component Catalog

### models.py

#### Model (ObjectModel)
- Database record: name, provider, type (language/embedding/speech_to_text/text_to_speech)
- `get_models_by_type()`: Async query to fetch all models of a specific type
- Stores provider-model pairs for AI factory instantiation

#### DefaultModels (RecordModel)
- Singleton configuration record (record_id: `open_notebook:default_models`)
- Fields: default_chat_model, default_transformation_model, large_context_model, default_text_to_speech_model, default_speech_to_text_model, default_embedding_model, default_tools_model
- `get_instance()`: Always fetches fresh from database (overrides parent caching for real-time updates)
- Returns fresh instance on each call (no singleton cache)

#### ModelManager
- Stateless factory for instantiating AI models
- `get_model(model_id)`: Retrieves Model by ID, creates via AIFactory.create_* based on type
- `get_defaults()`: Fetches DefaultModels configuration
- `get_default_model(model_type)`: Smart lookup (e.g., "chat" → default_chat_model, "transformation" → default_transformation_model with fallback to chat)
- `get_speech_to_text()`, `get_text_to_speech()`, `get_embedding_model()`: Type-specific convenience methods with assertions
- **Global instance**: `model_manager` singleton exported for use throughout app

### provision.py

#### provision_langchain_model()
- Factory for LangGraph nodes needing LLM provisioning
- **Smart fallback logic**:
  - If tokens > 105,000: Use `large_context_model`
  - Elif `model_id` specified: Use specific model
  - Else: Use default model for type (e.g., "chat", "transformation")
- Returns LangChain-compatible model via `.to_langchain()`
- Logs model selection decision

### key_provider.py

#### API Key Provider (DB→Env Fallback)
- **Purpose**: Provides API keys from database first, falls back to environment variables
- **Pattern**: Before Esperanto creates a model, keys are loaded from `APIKeyConfig` and set as environment variables
- **Integration point**: Called automatically by `ModelManager.get_model()` before `AIFactory.create_*`

#### Key Functions
- `get_api_key(provider)`: Get single API key (DB first, then env var)
- `provision_provider_keys(provider)`: Set env vars from DB config for a provider
- `provision_all_keys()`: Load all provider keys from DB into env vars (useful at startup)

#### Provider Configuration Maps
- `PROVIDER_CONFIG`: Simple providers (openai, anthropic, google, groq, etc.)
- `VERTEX_CONFIG`: Google Vertex AI (project, location, credentials)
- `AZURE_CONFIG`: Azure OpenAI (api_key, endpoint, api_version, mode-specific endpoints)
- `OPENAI_COMPATIBLE_CONFIG`: Generic OpenAI-compatible (generic + mode-specific for LLM/EMBEDDING/STT/TTS)

## Common Patterns

- **Type dispatch**: Model.type field drives factory logic (4 model types)
- **Provider abstraction**: Esperanto handles provider differences; ModelManager unaware of provider specifics
- **Fresh defaults**: DefaultModels.get_instance() always fetches from database (not cached) for live config updates
- **Config override**: provision_langchain_model() accepts kwargs passed to AIFactory.create_* methods
- **Token-based selection**: provision_langchain_model() detects large contexts and upgrades model automatically
- **Type assertions**: get_speech_to_text(), get_embedding_model() assert returned type (safety check)
- **DB→Env fallback**: API keys checked in database (APIKeyConfig) first, then environment variables; enables UI-based key management while maintaining backward compatibility

## Key Dependencies

- `esperanto`: AIFactory.create_language(), create_embedding(), create_speech_to_text(), create_text_to_speech()
- `open_notebook.database.repository`: repo_query, ensure_record_id
- `open_notebook.domain.base`: ObjectModel, RecordModel base classes
- `open_notebook.domain.api_key_config`: APIKeyConfig for database-stored API keys
- `open_notebook.utils`: token_count() for context size detection
- `loguru`: Logging for model selection decisions

## Important Quirks & Gotchas

- **Token counting rough estimate**: provision_langchain_model() uses token_count() which estimates via cl100k_base encoding (may differ 5-10% from actual model)
- **Large context threshold hard-coded**: 105,000 token threshold for large_context_model upgrade (not configurable)
- **DefaultModels.get_instance() fresh fetch**: Intentionally bypasses parent singleton cache to pick up live config changes; creates new instance each call
- **Type-specific getters use assertions**: get_speech_to_text() asserts isinstance (catches misconfiguration early)
- **No validation of model existence**: ModelManager.get_model() raises ValueError if model not found (not caught upstream)
- **Esperanto caching**: Actual model instances cached by Esperanto (not by ModelManager); ModelManager stateless
- **Fallback chain specificity**: "transformation" type falls back to default_chat_model if not explicitly set (convention-based)
- **kwargs passed through**: provision_langchain_model() passes kwargs to AIFactory but doesn't validate what's accepted
- **Key provider sets env vars**: `provision_provider_keys()` modifies `os.environ` to inject DB-stored keys; Esperanto reads from env vars

## How to Extend

1. **Add new model type**: Add type string to Model.type enum, add create_* method in AIFactory, handle in ModelManager.get_model()
2. **Add new default configuration**: Extend DefaultModels with new field (e.g., default_vision_model), add getter in ModelManager
3. **Change fallback logic**: Modify provision_langchain_model() token threshold or fallback chain
4. **Add model filtering**: Extend Model.get_models_by_type() with additional filters (e.g., by provider)
5. **Implement model caching**: Wrap ModelManager methods with functools.lru_cache (be aware of kwargs mutability)

## Usage Example

```python
from open_notebook.ai.models import model_manager

# Get default chat model
chat_model = await model_manager.get_default_model("chat")

# Get specific model by ID
embedding_model = await model_manager.get_model("model:openai_embedding")

# Get embedding model with config override
embedding_model = await model_manager.get_embedding_model(temperature=0.1)

# Provision model for LangGraph (auto-detects large context)
from open_notebook.ai.provision import provision_langchain_model
langchain_model = await provision_langchain_model(
    content=long_text,
    model_id=None,  # Use default
    default_type="chat",
    temperature=0.7
)
```

---

## Connection Testing (connection_tester.py)

### Purpose

Provides functionality to test if a provider's API key is valid by making minimal API calls. Used by the API Configuration UI to validate user-entered credentials before saving.

### test_provider_connection()

Main entry point for testing provider connectivity.

```python
async def test_provider_connection(
    provider: str, model_type: str = "language"
) -> Tuple[bool, str]
```

**Returns**: `(success: bool, message: str)` - Success status and human-readable message.

**Flow**:
1. Calls `provision_provider_keys(provider)` to load DB keys into env vars
2. Looks up test model from `TEST_MODELS` dict
3. For URL-based providers (ollama, openai_compatible): Tests server connectivity
4. For API-based providers: Creates minimal model via Esperanto and makes test call
5. Returns user-friendly error messages for common failures

### TEST_MODELS Configuration

Maps each provider to `(model_name, model_type)` for testing:

```python
TEST_MODELS = {
    "openai": ("gpt-3.5-turbo", "language"),
    "anthropic": ("claude-3-haiku-20240307", "language"),
    "google": ("gemini-1.5-flash", "language"),
    "groq": ("llama-3.1-8b-instant", "language"),
    "voyage": ("voyage-3-lite", "embedding"),
    "elevenlabs": ("eleven_multilingual_v2", "text_to_speech"),
    "ollama": (None, "language"),  # Dynamic
    # ... more providers
}
```

### Special Provider Handlers

- **`_test_ollama_connection(base_url)`**: Tests Ollama server via `/api/tags` endpoint, returns model count
- **`_test_openai_compatible_connection(base_url, api_key)`**: Tests OpenAI-compatible servers via `/models` endpoint
- **`_get_ollama_models(base_url)`**: Fetches available models from Ollama server

### Error Message Normalization

The tester normalizes error messages for user-friendly display:
- `401/unauthorized` -> "Invalid API key"
- `403/forbidden` -> "API key lacks required permissions"
- `rate limit` -> "Rate limited - but connection works" (success)
- `model not found` -> "API key valid (test model not available)" (success)
- Connection/timeout errors -> Helpful troubleshooting messages

---

## Key Provider (key_provider.py)

### Purpose

Unified interface for retrieving API keys with database-first, environment-fallback strategy. Enables UI-based key management while maintaining backward compatibility with `.env` files.

### Core Functions

#### get_api_key(provider)

```python
async def get_api_key(provider: str) -> Optional[str]
```

Gets API key for a provider. Checks database (`APIKeyConfig`) first, then environment variable.

**Fallback Chain**:
1. Query `APIKeyConfig.get_instance()` from database
2. Get field value via `getattr(api_config, config_field)`
3. Handle `SecretStr` (call `.get_secret_value()`) vs regular strings
4. If DB value exists and is non-empty, return it
5. Otherwise, return `os.environ.get(env_var)`

#### provision_provider_keys(provider)

```python
async def provision_provider_keys(provider: str) -> bool
```

Main entry point for DB->Env fallback. Sets environment variables from database config for a provider. Called before model provisioning to ensure Esperanto can read keys from env vars.

**Returns**: `True` if any keys were set from database.

**Usage**:
```python
# Before creating a model, ensure DB keys are in env vars
await provision_provider_keys("openai")
model = AIFactory.create_language(model_name="gpt-4", provider="openai")
```

#### provision_all_keys()

```python
async def provision_all_keys() -> dict[str, bool]
```

Provisions all providers at once. Useful at application startup.

### Provider Configuration Maps

#### PROVIDER_CONFIG (Simple Providers)

Single-field providers with API key only:

```python
PROVIDER_CONFIG = {
    "openai": {"env_var": "OPENAI_API_KEY", "config_field": "openai_api_key"},
    "anthropic": {"env_var": "ANTHROPIC_API_KEY", "config_field": "anthropic_api_key"},
    "google": {"env_var": "GOOGLE_API_KEY", "config_field": "google_api_key"},
    "groq": {"env_var": "GROQ_API_KEY", "config_field": "groq_api_key"},
    "mistral": {"env_var": "MISTRAL_API_KEY", "config_field": "mistral_api_key"},
    "deepseek": {"env_var": "DEEPSEEK_API_KEY", "config_field": "deepseek_api_key"},
    "xai": {"env_var": "XAI_API_KEY", "config_field": "xai_api_key"},
    "openrouter": {"env_var": "OPENROUTER_API_KEY", "config_field": "openrouter_api_key"},
    "voyage": {"env_var": "VOYAGE_API_KEY", "config_field": "voyage_api_key"},
    "elevenlabs": {"env_var": "ELEVENLABS_API_KEY", "config_field": "elevenlabs_api_key"},
    "ollama": {"env_var": "OLLAMA_API_BASE", "config_field": "ollama_api_base"},
}
```

#### VERTEX_CONFIG (Google Vertex AI)

Multi-field configuration for Vertex AI:

```python
VERTEX_CONFIG = {
    "project": {"env_var": "VERTEX_PROJECT", "config_field": "vertex_project"},
    "location": {"env_var": "VERTEX_LOCATION", "config_field": "vertex_location"},
    "credentials": {"env_var": "GOOGLE_APPLICATION_CREDENTIALS", "config_field": "google_application_credentials"},
}
```

#### AZURE_CONFIG (Azure OpenAI)

Generic and mode-specific endpoints for Azure:

```python
AZURE_CONFIG = {
    "api_key": {"env_var": "AZURE_OPENAI_API_KEY", "config_field": "azure_openai_api_key"},
    "api_version": {"env_var": "AZURE_OPENAI_API_VERSION", "config_field": "azure_openai_api_version"},
    "endpoint": {"env_var": "AZURE_OPENAI_ENDPOINT", "config_field": "azure_openai_endpoint"},
    # Mode-specific endpoints
    "endpoint_llm": {"env_var": "AZURE_OPENAI_ENDPOINT_LLM", "config_field": "azure_openai_endpoint_llm"},
    "endpoint_embedding": {"env_var": "AZURE_OPENAI_ENDPOINT_EMBEDDING", "config_field": "azure_openai_endpoint_embedding"},
    "endpoint_stt": {"env_var": "AZURE_OPENAI_ENDPOINT_STT", "config_field": "azure_openai_endpoint_stt"},
    "endpoint_tts": {"env_var": "AZURE_OPENAI_ENDPOINT_TTS", "config_field": "azure_openai_endpoint_tts"},
}
```

#### OPENAI_COMPATIBLE_CONFIG

Generic and mode-specific configuration for OpenAI-compatible providers:

```python
OPENAI_COMPATIBLE_CONFIG = {
    # Generic
    "api_key": {"env_var": "OPENAI_COMPATIBLE_API_KEY", "config_field": "openai_compatible_api_key"},
    "base_url": {"env_var": "OPENAI_COMPATIBLE_BASE_URL", "config_field": "openai_compatible_base_url"},
    # Mode-specific: LLM, Embedding, STT, TTS
    "api_key_llm": {"env_var": "OPENAI_COMPATIBLE_API_KEY_LLM", "config_field": "openai_compatible_api_key_llm"},
    "base_url_llm": {"env_var": "OPENAI_COMPATIBLE_BASE_URL_LLM", "config_field": "openai_compatible_base_url_llm"},
    # ... similar for embedding, stt, tts
}
```

### Internal Helper Functions

- **`_provision_simple_provider(provider)`**: Sets single env var for simple providers
- **`_provision_vertex()`**: Sets all Vertex AI env vars
- **`_provision_azure()`**: Sets all Azure OpenAI env vars (handles SecretStr)
- **`_provision_openai_compatible()`**: Sets all OpenAI-compatible env vars

### Integration with ModelManager

The key provider integrates with the existing model provisioning flow:

1. **API endpoint** calls `provision_provider_keys(provider)` before model operations
2. **ConnectionTester** calls `provision_provider_keys()` before testing
3. **Keys are set** in `os.environ` where Esperanto reads them
4. **Esperanto** creates models using standard env var lookup

This approach requires no changes to Esperanto or existing model creation code - keys are transparently injected into the environment before Esperanto needs them.
