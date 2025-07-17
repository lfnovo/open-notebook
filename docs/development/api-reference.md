# API Reference

Open Notebook provides a comprehensive REST API for programmatic access to all functionality. This document covers all available endpoints, authentication, request/response formats, and usage examples.

## 🔗 Base Information

- **Base URL**: `http://localhost:5055` (default development)
- **Content Type**: `application/json`
- **Authentication**: Optional password-based authentication
- **API Version**: v0.2.2

## 🔐 Authentication

Open Notebook supports optional password-based authentication via the `APP_PASSWORD` environment variable.

### Authentication Header

```bash
# If APP_PASSWORD is set
curl -H "Authorization: Bearer YOUR_PASSWORD" \
  http://localhost:5055/api/notebooks
```

### Authentication Responses

**401 Unauthorized**:
```json
{
  "detail": "Authentication required"
}
```

## 📚 Notebooks API

Manage notebook collections and organization.

### GET /api/notebooks

Get all notebooks with optional filtering and ordering.

**Query Parameters**:
- `archived` (boolean, optional): Filter by archived status
- `order_by` (string, optional): Order by field and direction (default: "updated desc")

**Response**:
```json
[
  {
    "id": "notebook:uuid",
    "name": "My Research Notebook",
    "description": "Research on AI applications",
    "archived": false,
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z"
  }
]
```

**Example**:
```bash
curl -X GET "http://localhost:5055/api/notebooks?archived=false&order_by=created desc"
```

### POST /api/notebooks

Create a new notebook.

**Request Body**:
```json
{
  "name": "My New Notebook",
  "description": "Description of the notebook"
}
```

**Response**: Same as GET single notebook

**Example**:
```bash
curl -X POST http://localhost:5055/api/notebooks \
  -H "Content-Type: application/json" \
  -d '{"name": "Research Project", "description": "AI research notebook"}'
```

### GET /api/notebooks/{notebook_id}

Get a specific notebook by ID.

**Path Parameters**:
- `notebook_id` (string): Notebook ID

**Response**: Same as POST response

### PUT /api/notebooks/{notebook_id}

Update a notebook.

**Path Parameters**:
- `notebook_id` (string): Notebook ID

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "archived": true
}
```

**Response**: Same as GET single notebook

### DELETE /api/notebooks/{notebook_id}

Delete a notebook.

**Path Parameters**:
- `notebook_id` (string): Notebook ID

**Response**:
```json
{
  "message": "Notebook deleted successfully"
}
```

## 📄 Sources API

Manage content sources within notebooks.

### POST /api/sources

Create a new source.

**Request Body**:
```json
{
  "notebook_id": "notebook:uuid",
  "type": "link",
  "url": "https://example.com/article",
  "title": "Optional title",
  "transformations": ["transformation:uuid"],
  "embed": true,
  "delete_source": false
}
```

**Source Types**:
- `link`: Web URL
- `upload`: File upload
- `text`: Direct text content

**Response**:
```json
{
  "id": "source:uuid",
  "title": "Article Title",
  "topics": ["AI", "Machine Learning"],
  "asset": {
    "url": "https://example.com/article"
  },
  "full_text": "Article content...",
  "embedded_chunks": 15,
  "created": "2024-01-01T00:00:00Z",
  "updated": "2024-01-01T00:00:00Z"
}
```

### GET /api/sources

Get all sources with optional filtering.

**Query Parameters**:
- `notebook_id` (string, optional): Filter by notebook
- `limit` (integer, optional): Maximum results (default: 100)
- `offset` (integer, optional): Pagination offset

**Response**:
```json
[
  {
    "id": "source:uuid",
    "title": "Article Title",
    "topics": ["AI"],
    "asset": {
      "url": "https://example.com/article"
    },
    "embedded_chunks": 15,
    "insights_count": 3,
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z"
  }
]
```

### GET /api/sources/{source_id}

Get a specific source by ID.

**Path Parameters**:
- `source_id` (string): Source ID

**Response**: Same as POST response

### PUT /api/sources/{source_id}

Update a source.

**Path Parameters**:
- `source_id` (string): Source ID

**Request Body** (all fields optional):
```json
{
  "title": "Updated Title",
  "topics": ["Updated", "Topics"]
}
```

**Response**: Same as GET single source

### DELETE /api/sources/{source_id}

Delete a source.

**Path Parameters**:
- `source_id` (string): Source ID

**Response**:
```json
{
  "message": "Source deleted successfully"
}
```

## 📝 Notes API

Manage notes within notebooks.

### POST /api/notes

Create a new note.

**Request Body**:
```json
{
  "title": "Note Title",
  "content": "Note content",
  "note_type": "human",
  "notebook_id": "notebook:uuid"
}
```

**Note Types**:
- `human`: Manual note
- `ai`: AI-generated note

**Response**:
```json
{
  "id": "note:uuid",
  "title": "Note Title",
  "content": "Note content",
  "note_type": "human",
  "created": "2024-01-01T00:00:00Z",
  "updated": "2024-01-01T00:00:00Z"
}
```

### GET /api/notes

Get all notes with optional filtering.

**Query Parameters**:
- `notebook_id` (string, optional): Filter by notebook
- `note_type` (string, optional): Filter by note type
- `limit` (integer, optional): Maximum results

**Response**: Array of note objects

### GET /api/notes/{note_id}

Get a specific note by ID.

**Path Parameters**:
- `note_id` (string): Note ID

**Response**: Same as POST response

### PUT /api/notes/{note_id}

Update a note.

**Path Parameters**:
- `note_id` (string): Note ID

**Request Body** (all fields optional):
```json
{
  "title": "Updated Title",
  "content": "Updated content",
  "note_type": "ai"
}
```

**Response**: Same as GET single note

### DELETE /api/notes/{note_id}

Delete a note.

**Path Parameters**:
- `note_id` (string): Note ID

**Response**:
```json
{
  "message": "Note deleted successfully"
}
```

## 🔍 Search API

Perform full-text and vector search across content.

### POST /api/search

Search the knowledge base.

**Request Body**:
```json
{
  "query": "artificial intelligence",
  "type": "vector",
  "limit": 10,
  "search_sources": true,
  "search_notes": true,
  "minimum_score": 0.2
}
```

**Search Types**:
- `text`: Full-text search
- `vector`: Semantic search (requires embedding model)

**Response**:
```json
{
  "results": [
    {
      "id": "source:uuid",
      "title": "AI Research Paper",
      "content": "Relevant content excerpt...",
      "score": 0.85,
      "type": "source",
      "metadata": {
        "topics": ["AI", "Machine Learning"]
      }
    }
  ],
  "total_count": 1,
  "search_type": "vector"
}
```

### POST /api/search/ask

Ask questions using AI models (streaming response).

**Request Body**:
```json
{
  "question": "What are the key benefits of AI?",
  "strategy_model": "model:gpt-4o-mini",
  "answer_model": "model:gpt-4o-mini",
  "final_answer_model": "model:gpt-4o-mini"
}
```

**Response**: Server-Sent Events (SSE) stream

**Stream Events**:
```json
// Strategy phase
data: {"type": "strategy", "reasoning": "...", "searches": [...]}

// Individual answers
data: {"type": "answer", "content": "Answer content..."}

// Final answer
data: {"type": "final_answer", "content": "Final synthesized answer..."}

// Completion
data: {"type": "complete", "final_answer": "Final answer..."}
```

### POST /api/search/ask/simple

Ask questions (non-streaming response).

**Request Body**: Same as streaming version

**Response**:
```json
{
  "answer": "The key benefits of AI include...",
  "question": "What are the key benefits of AI?"
}
```

## 🤖 Models API

Manage AI models and configurations.

### GET /api/models

Get all configured models.

**Response**:
```json
[
  {
    "id": "model:uuid",
    "name": "gpt-4o-mini",
    "provider": "openai",
    "type": "language",
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z"
  }
]
```

### POST /api/models

Create a new model configuration.

**Request Body**:
```json
{
  "name": "gpt-4o-mini",
  "provider": "openai",
  "type": "language"
}
```

**Model Types**:
- `language`: Text generation models
- `embedding`: Vector embedding models
- `text_to_speech`: TTS models
- `speech_to_text`: STT models

**Response**: Same as GET single model

### GET /api/models/{model_id}

Get a specific model by ID.

**Path Parameters**:
- `model_id` (string): Model ID

**Response**: Same as POST response

### DELETE /api/models/{model_id}

Delete a model configuration.

**Path Parameters**:
- `model_id` (string): Model ID

**Response**:
```json
{
  "message": "Model deleted successfully"
}
```

### GET /api/models/defaults

Get default model configurations.

**Response**:
```json
{
  "default_chat_model": "model:gpt-4o-mini",
  "default_transformation_model": "model:gpt-4o-mini",
  "large_context_model": "model:gpt-4o-mini",
  "default_text_to_speech_model": "model:tts-1",
  "default_speech_to_text_model": "model:whisper-1",
  "default_embedding_model": "model:text-embedding-3-small",
  "default_tools_model": "model:gpt-4o-mini"
}
```

## 🔧 Transformations API

Manage content transformations and AI-powered analysis.

### GET /api/transformations

Get all transformations.

**Response**:
```json
[
  {
    "id": "transformation:uuid",
    "name": "summarize",
    "title": "Summarize Content",
    "description": "Create a concise summary",
    "prompt": "Summarize the following content...",
    "apply_default": true,
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z"
  }
]
```

### POST /api/transformations

Create a new transformation.

**Request Body**:
```json
{
  "name": "custom_analysis",
  "title": "Custom Analysis",
  "description": "Perform custom content analysis",
  "prompt": "Analyze the following content for key themes...",
  "apply_default": false
}
```

**Response**: Same as GET single transformation

### GET /api/transformations/{transformation_id}

Get a specific transformation by ID.

**Path Parameters**:
- `transformation_id` (string): Transformation ID

**Response**: Same as POST response

### PUT /api/transformations/{transformation_id}

Update a transformation.

**Path Parameters**:
- `transformation_id` (string): Transformation ID

**Request Body** (all fields optional):
```json
{
  "name": "updated_name",
  "title": "Updated Title",
  "description": "Updated description",
  "prompt": "Updated prompt...",
  "apply_default": true
}
```

**Response**: Same as GET single transformation

### DELETE /api/transformations/{transformation_id}

Delete a transformation.

**Path Parameters**:
- `transformation_id` (string): Transformation ID

**Response**:
```json
{
  "message": "Transformation deleted successfully"
}
```

### POST /api/transformations/execute

Execute a transformation on content.

**Request Body**:
```json
{
  "transformation_id": "transformation:uuid",
  "input_text": "Content to transform...",
  "model_id": "model:gpt-4o-mini"
}
```

**Response**:
```json
{
  "output": "Transformed content...",
  "transformation_id": "transformation:uuid",
  "model_id": "model:gpt-4o-mini"
}
```

## 📊 Insights API

Manage AI-generated insights for sources.

### GET /api/sources/{source_id}/insights

Get insights for a specific source.

**Path Parameters**:
- `source_id` (string): Source ID

**Response**:
```json
[
  {
    "id": "insight:uuid",
    "source_id": "source:uuid",
    "insight_type": "summary",
    "content": "This source discusses...",
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z"
  }
]
```

### POST /api/sources/{source_id}/insights

Create a new insight for a source.

**Path Parameters**:
- `source_id` (string): Source ID

**Request Body**:
```json
{
  "transformation_id": "transformation:uuid",
  "model_id": "model:gpt-4o-mini"
}
```

**Response**: Same as GET insight

### POST /api/insights/{insight_id}/save-as-note

Save an insight as a note.

**Path Parameters**:
- `insight_id` (string): Insight ID

**Request Body**:
```json
{
  "notebook_id": "notebook:uuid"
}
```

**Response**:
```json
{
  "note_id": "note:uuid",
  "message": "Insight saved as note successfully"
}
```

## 🎙️ Podcasts API

Generate professional multi-speaker podcasts.

### GET /api/episode-profiles

Get all episode profiles.

**Response**:
```json
[
  {
    "id": "episode_profile:uuid",
    "name": "tech_discussion",
    "description": "Technical discussion between 2 experts",
    "speaker_config": "tech_experts",
    "outline_provider": "openai",
    "outline_model": "gpt-4o-mini",
    "transcript_provider": "openai",
    "transcript_model": "gpt-4o-mini",
    "default_briefing": "Create an engaging technical discussion...",
    "num_segments": 5,
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z"
  }
]
```

### GET /api/speaker-profiles

Get all speaker profiles.

**Response**:
```json
[
  {
    "id": "speaker_profile:uuid",
    "name": "tech_experts",
    "description": "Two technical experts for tech discussions",
    "tts_provider": "openai",
    "tts_model": "tts-1",
    "speakers": [
      {
        "name": "Dr. Alex Chen",
        "voice_id": "nova",
        "backstory": "Senior AI researcher...",
        "personality": "Analytical, clear communicator..."
      }
    ],
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z"
  }
]
```

### POST /api/podcasts

Create a new podcast episode.

**Request Body**:
```json
{
  "name": "AI Discussion Episode",
  "briefing": "Discuss the latest AI developments...",
  "episode_profile_id": "episode_profile:uuid",
  "source_ids": ["source:uuid1", "source:uuid2"],
  "note_ids": ["note:uuid1"]
}
```

**Response**:
```json
{
  "id": "episode:uuid",
  "name": "AI Discussion Episode",
  "briefing": "Discuss the latest AI developments...",
  "episode_profile": {...},
  "speaker_profile": {...},
  "command": "command:uuid",
  "created": "2024-01-01T00:00:00Z",
  "updated": "2024-01-01T00:00:00Z"
}
```

### GET /api/podcasts/{episode_id}

Get a specific podcast episode.

**Path Parameters**:
- `episode_id` (string): Episode ID

**Response**: Same as POST response

### GET /api/podcasts/{episode_id}/audio

Download the generated audio file.

**Path Parameters**:
- `episode_id` (string): Episode ID

**Response**: Audio file download (MP3 format)

## 🎛️ Settings API

Manage application settings and configuration.

### GET /api/settings

Get current application settings.

**Response**:
```json
{
  "default_content_processing_engine_doc": "docling",
  "default_content_processing_engine_url": "firecrawl",
  "default_embedding_option": "auto",
  "auto_delete_files": "false",
  "youtube_preferred_languages": ["en", "es"]
}
```

### PUT /api/settings

Update application settings.

**Request Body** (all fields optional):
```json
{
  "default_content_processing_engine_doc": "docling",
  "default_content_processing_engine_url": "firecrawl",
  "default_embedding_option": "auto",
  "auto_delete_files": "true",
  "youtube_preferred_languages": ["en", "fr", "de"]
}
```

**Response**: Same as GET response

## 📐 Context API

Manage context configuration for AI operations.

### POST /api/context

Get context information for a notebook.

**Request Body**:
```json
{
  "notebook_id": "notebook:uuid",
  "context_config": {
    "sources": {
      "source:uuid1": "full",
      "source:uuid2": "summary"
    },
    "notes": {
      "note:uuid1": "full"
    }
  }
}
```

**Context Levels**:
- `full`: Include complete content
- `summary`: Include summary only
- `exclude`: Exclude from context

**Response**:
```json
{
  "notebook_id": "notebook:uuid",
  "sources": [
    {
      "id": "source:uuid",
      "title": "Source Title",
      "content": "Source content...",
      "inclusion_level": "full"
    }
  ],
  "notes": [
    {
      "id": "note:uuid",
      "title": "Note Title",
      "content": "Note content...",
      "inclusion_level": "full"
    }
  ],
  "total_tokens": 1500
}
```

## 🔨 Commands API

Monitor and manage background jobs.

### GET /api/commands

Get all commands (background jobs).

**Query Parameters**:
- `status` (string, optional): Filter by status
- `limit` (integer, optional): Maximum results

**Response**:
```json
[
  {
    "id": "command:uuid",
    "name": "podcast_generation",
    "status": "completed",
    "progress": 100,
    "result": {...},
    "error": null,
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z"
  }
]
```

### GET /api/commands/{command_id}

Get a specific command by ID.

**Path Parameters**:
- `command_id` (string): Command ID

**Response**: Same as array item above

### DELETE /api/commands/{command_id}

Cancel/delete a command.

**Path Parameters**:
- `command_id` (string): Command ID

**Response**:
```json
{
  "message": "Command deleted successfully"
}
```

## 🏷️ Embedding API

Manage vector embeddings for content.

### POST /api/embed

Generate embeddings for an item.

**Request Body**:
```json
{
  "item_id": "source:uuid",
  "item_type": "source"
}
```

**Item Types**:
- `source`: Source content
- `note`: Note content

**Response**:
```json
{
  "success": true,
  "message": "Embedding generated successfully",
  "item_id": "source:uuid",
  "item_type": "source"
}
```

## 🚨 Error Responses

### Common Error Codes

**400 Bad Request**:
```json
{
  "detail": "Invalid input data"
}
```

**401 Unauthorized**:
```json
{
  "detail": "Authentication required"
}
```

**404 Not Found**:
```json
{
  "detail": "Resource not found"
}
```

**422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**500 Internal Server Error**:
```json
{
  "detail": "Internal server error occurred"
}
```

## 📋 Usage Examples

### Complete Workflow Example

```bash
# 1. Create a notebook
NOTEBOOK_ID=$(curl -X POST http://localhost:5055/api/notebooks \
  -H "Content-Type: application/json" \
  -d '{"name": "AI Research", "description": "Research on AI applications"}' \
  | jq -r '.id')

# 2. Add a source
SOURCE_ID=$(curl -X POST http://localhost:5055/api/sources \
  -H "Content-Type: application/json" \
  -d "{\"notebook_id\": \"$NOTEBOOK_ID\", \"type\": \"link\", \"url\": \"https://example.com/ai-article\", \"embed\": true}" \
  | jq -r '.id')

# 3. Create a model
MODEL_ID=$(curl -X POST http://localhost:5055/api/models \
  -H "Content-Type: application/json" \
  -d '{"name": "gpt-4o-mini", "provider": "openai", "type": "language"}' \
  | jq -r '.id')

# 4. Search for content
curl -X POST http://localhost:5055/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence", "type": "vector", "limit": 5}'

# 5. Ask a question
curl -X POST http://localhost:5055/api/search/ask/simple \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What are the main AI applications?\", \"strategy_model\": \"$MODEL_ID\", \"answer_model\": \"$MODEL_ID\", \"final_answer_model\": \"$MODEL_ID\"}"
```

### Podcast Generation Example

```bash
# 1. Get episode profiles
curl -X GET http://localhost:5055/api/episode-profiles

# 2. Create a podcast
EPISODE_ID=$(curl -X POST http://localhost:5055/api/podcasts \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"AI Discussion\", \"briefing\": \"Discuss AI trends\", \"episode_profile_id\": \"episode_profile:tech_discussion\", \"source_ids\": [\"$SOURCE_ID\"]}" \
  | jq -r '.id')

# 3. Check command status
curl -X GET http://localhost:5055/api/commands

# 4. Download audio when ready
curl -X GET http://localhost:5055/api/podcasts/$EPISODE_ID/audio -o podcast.mp3
```

## 📡 WebSocket Support

Currently, Open Notebook uses Server-Sent Events (SSE) for real-time updates in the Ask endpoint. WebSocket support may be added in future versions for more interactive features.

## 📈 Rate Limiting

The API currently doesn't enforce rate limiting, but it's recommended to implement rate limiting in production deployments to prevent abuse.

## 🔄 Versioning

The API uses semantic versioning. Breaking changes will increment the major version number. The current API version is included in the OpenAPI documentation at `/docs`.

---

This API reference provides comprehensive coverage of Open Notebook's REST API. For additional examples and integration patterns, check the [GitHub repository](https://github.com/lfnovo/open-notebook) and join our [Discord community](https://discord.gg/37XJPXfz2w).