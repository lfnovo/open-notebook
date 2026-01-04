# API Reference

Complete REST API for Open Notebook. All endpoints are served from the API backend (default: `http://localhost:5055`).

**Base URL**: `http://localhost:5055` (development) or environment-specific production URL

**Interactive Docs**: Use FastAPI's built-in Swagger UI at `http://localhost:5055/docs` for live testing and exploration. This is the primary reference for all endpoints, request/response schemas, and real-time testing.

---

## Quick Start

### 1. Authentication

Simple password-based (development only):

```bash
curl http://localhost:5055/api/notebooks \
  -H "Authorization: Bearer your_password"
```

**⚠️ Production**: Replace with OAuth/JWT. See [Security Configuration](../5-CONFIGURATION/security.md) for details.

### 2. Base API Flow

Most operations follow this pattern:
1. Create a **Notebook** (container for research)
2. Add **Sources** (PDFs, URLs, text)
3. Query via **Chat** or **Search**
4. View results and **Notes**

### 3. Testing Endpoints

Instead of memorizing endpoints, use the interactive API docs:
- Navigate to `http://localhost:5055/docs`
- Try requests directly in the browser
- See request/response schemas in real-time
- Test with your own data

---

## API Endpoints Overview

### Main Resource Types

**Notebooks** - Research projects containing sources and notes
- `GET/POST /notebooks` - List and create
- `GET/PUT/DELETE /notebooks/{id}` - Read, update, delete

**Sources** - Content items (PDFs, URLs, text)
- `GET/POST /sources` - List and add content
- `GET /sources/{id}` - Fetch source details
- `POST /sources/{id}/retry` - Retry failed processing
- `GET /sources/{id}/download` - Download original file

**Notes** - User-created or AI-generated research notes
- `GET/POST /notes` - List and create
- `GET/PUT/DELETE /notes/{id}` - Read, update, delete

**Chat** - Conversational AI interface
- `GET/POST /chat/sessions` - Manage chat sessions
- `POST /chat/execute` - Send message and get response
- `POST /chat/context/build` - Prepare context for chat

**Search** - Find content by text or semantic similarity
- `POST /search` - Full-text or vector search
- `POST /ask` - Ask a question (search + synthesize)

**Transformations** - Custom prompts for extracting insights
- `GET/POST /transformations` - Create custom extraction rules
- `POST /sources/{id}/insights` - Apply transformation to source

**Models** - Configure AI providers
- `GET /models` - Available models
- `GET /models/defaults` - Current defaults
- `POST /models/config` - Set defaults

**Health & Status**
- `GET /health` - Health check
- `GET /commands/{id}` - Track async operations

---

## Authentication

### Current (Development)

All requests require password header:

```bash
curl -H "Authorization: Bearer your_password" http://localhost:5055/api/notebooks
```

Password configured via `OPEN_NOTEBOOK_PASSWORD` environment variable.

> **📖 See [Security Configuration](../5-CONFIGURATION/security.md)** for complete authentication setup, API examples, and production hardening.

### Production

**⚠️ Not secure.** Replace with:
- OAuth 2.0 (recommended)
- JWT tokens
- API keys

See [Security Configuration](../5-CONFIGURATION/security.md) for production setup.

---

## Common Patterns

### Pagination

```bash
# List sources with limit/offset
curl 'http://localhost:5055/sources?limit=20&offset=10'
```

### Filtering & Sorting

```bash
# Filter by notebook, sort by date
curl 'http://localhost:5055/sources?notebook_id=notebook:abc&sort_by=created&sort_order=asc'
```

### Async Operations

Some operations (source processing, podcast generation) return immediately with a command ID:

```bash
# Submit async operation
curl -X POST http://localhost:5055/sources -F async_processing=true
# Response: {"id": "source:src001", "command_id": "command:cmd123"}

# Poll status
curl http://localhost:5055/commands/command:cmd123
```

### Streaming Responses

The `/ask` endpoint streams responses as Server-Sent Events:

```bash
curl -N 'http://localhost:5055/ask' \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI?"}'

# Outputs: data: {"type":"strategy",...}
#          data: {"type":"answer",...}
#          data: {"type":"final_answer",...}
```

### Multipart File Upload

```bash
curl -X POST http://localhost:5055/sources \
  -F "type=upload" \
  -F "notebook_id=notebook:abc" \
  -F "file=@document.pdf"
```

---

## Error Handling

All errors return JSON with status code:

```json
{"detail": "Notebook not found"}
```

### Common Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Operation completed |
| 400 | Bad Request | Invalid input |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 500 | Server Error | Database/processing error |

---

## Tips for Developers

1. **Start with interactive docs** (`http://localhost:5055/docs`) - this is the definitive reference
2. **Enable logging** for debugging (check API logs: `docker logs`)
3. **Streaming endpoints** require special handling (Server-Sent Events, not standard JSON)
4. **Async operations** return immediately; always poll status before assuming completion
5. **Vector search** requires embedding model configured (check `/models`)
6. **Model overrides** are per-request; set in body, not config
7. **CORS enabled** in development; configure for production

---

## Learning Path

1. **Authentication**: Add `X-Password` header to all requests
2. **Create a notebook**: `POST /notebooks` with name and description
3. **Add a source**: `POST /sources` with file, URL, or text
4. **Query your content**: `POST /chat/execute` to ask questions
5. **Explore advanced features**: Search, transformations, streaming

---

## Production Considerations

- Replace password auth with OAuth/JWT (see [Security](../5-CONFIGURATION/security.md))
- Add rate limiting via reverse proxy (Nginx, CloudFlare, Kong)
- Enable CORS restrictions (currently allows all origins)
- Use HTTPS via reverse proxy (see [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md))
- Set up API versioning strategy (currently implicit)

See [Security Configuration](../5-CONFIGURATION/security.md) and [Reverse Proxy Setup](../5-CONFIGURATION/reverse-proxy.md) for complete production setup.
