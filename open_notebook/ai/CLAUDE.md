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

## Common Patterns

- **Type dispatch**: Model.type field drives factory logic (4 model types)
- **Provider abstraction**: Esperanto handles provider differences; ModelManager unaware of provider specifics
- **Fresh defaults**: DefaultModels.get_instance() always fetches from database (not cached) for live config updates
- **Config override**: provision_langchain_model() accepts kwargs passed to AIFactory.create_* methods
- **Token-based selection**: provision_langchain_model() detects large contexts and upgrades model automatically
- **Type assertions**: get_speech_to_text(), get_embedding_model() assert returned type (safety check)

## Key Dependencies

- `esperanto`: AIFactory.create_language(), create_embedding(), create_speech_to_text(), create_text_to_speech()
- `open_notebook.database.repository`: repo_query, ensure_record_id
- `open_notebook.domain.base`: ObjectModel, RecordModel base classes
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
