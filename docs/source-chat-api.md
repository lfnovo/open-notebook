# Source Chat API Documentation

The Source Chat API provides endpoints for creating and managing chat sessions focused on specific sources. Each chat session is contextually aware of the source's content and insights.

## Endpoints

### 1. Create Source Chat Session

**POST** `/api/sources/{source_id}/chat/sessions`

Creates a new chat session for a specific source.

#### Request Body
```json
{
  "source_id": "string",
  "title": "string (optional)",
  "model_override": "string (optional)"
}
```

#### Response
```json
{
  "id": "chat_session:abc123",
  "title": "Source Chat Session",
  "source_id": "source_123",
  "model_override": "gpt-4",
  "created": "2024-01-01T00:00:00Z",
  "updated": "2024-01-01T00:00:00Z",
  "message_count": 0
}
```

### 2. List Source Chat Sessions

**GET** `/api/sources/{source_id}/chat/sessions`

Retrieves all chat sessions for a specific source.

#### Response
```json
[
  {
    "id": "chat_session:abc123",
    "title": "Source Chat Session",
    "source_id": "source_123",
    "model_override": "gpt-4",
    "created": "2024-01-01T00:00:00Z",
    "updated": "2024-01-01T00:00:00Z",
    "message_count": 5
  }
]
```

### 3. Get Source Chat Session with Messages

**GET** `/api/sources/{source_id}/chat/sessions/{session_id}`

Retrieves a specific chat session with its message history and context indicators.

#### Response
```json
{
  "id": "chat_session:abc123",
  "title": "Source Chat Session",
  "source_id": "source_123",
  "model_override": "gpt-4",
  "created": "2024-01-01T00:00:00Z",
  "updated": "2024-01-01T00:00:00Z",
  "message_count": 2,
  "messages": [
    {
      "id": "msg_1",
      "type": "human",
      "content": "What are the key insights from this source?",
      "timestamp": null
    },
    {
      "id": "msg_2",
      "type": "ai",
      "content": "Based on the source content, here are the key insights...",
      "timestamp": null
    }
  ],
  "context_indicators": {
    "sources": ["source:123"],
    "insights": ["insight:456", "insight:789"],
    "notes": []
  }
}
```

### 4. Update Source Chat Session

**PUT** `/api/sources/{source_id}/chat/sessions/{session_id}`

Updates the title and/or model override for a chat session.

#### Request Body
```json
{
  "title": "Updated Session Title (optional)",
  "model_override": "gpt-4-turbo (optional)"
}
```

#### Response
```json
{
  "id": "chat_session:abc123",
  "title": "Updated Session Title",
  "source_id": "source_123",
  "model_override": "gpt-4-turbo",
  "created": "2024-01-01T00:00:00Z",
  "updated": "2024-01-01T00:30:00Z",
  "message_count": 2
}
```

### 5. Delete Source Chat Session

**DELETE** `/api/sources/{source_id}/chat/sessions/{session_id}`

Deletes a chat session and all its messages.

#### Response
```json
{
  "success": true,
  "message": "Source chat session deleted successfully"
}
```

### 6. Send Message to Source Chat (SSE Streaming)

**POST** `/api/sources/{source_id}/chat/sessions/{session_id}/messages`

Sends a message to the chat session and streams the AI response using Server-Sent Events.

#### Request Body
```json
{
  "message": "What are the main themes in this source?",
  "model_override": "gpt-4 (optional)"
}
```

#### SSE Response Stream

The response is streamed as Server-Sent Events with the following event types:

```
data: {"type": "user_message", "content": "What are the main themes?", "timestamp": null}

data: {"type": "ai_message", "content": "Based on the source content...", "timestamp": null}

data: {"type": "context_indicators", "data": {"sources": ["source:123"], "insights": ["insight:456"], "notes": []}}

data: {"type": "complete"}
```

Event Types:
- `user_message`: Echo of the user's message
- `ai_message`: Streaming AI response chunks
- `context_indicators`: Information about which sources/insights were used
- `complete`: Indicates the response is finished
- `error`: Error information if something goes wrong

## Features

### Model Override Support

You can override the default AI model at two levels:

1. **Session Level**: Set `model_override` when creating or updating a session
2. **Message Level**: Set `model_override` when sending individual messages (takes precedence)

### Context Awareness

Each chat session is automatically provided with:
- Full source content (with truncation for very large sources)
- All source insights
- Context indicators showing which content was referenced

### Source Relationship Validation

All endpoints verify that:
- The source exists
- The chat session belongs to the specified source
- The user has access to both resources

## Error Handling

Common HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid input)
- `404`: Source or session not found
- `500`: Internal server error

Error responses include descriptive error messages:

```json
{
  "detail": "Source not found"
}
```

## Integration with LangGraph

The API integrates with the `source_chat_graph` LangGraph implementation:

- Messages are stored in LangGraph's persistent checkpoint system
- Context is built using the `ContextBuilder` utility
- Model provisioning supports dynamic model selection
- Streaming responses use LangGraph's async streaming capabilities

## Usage Examples

### JavaScript/TypeScript Frontend

```typescript
// Create a new chat session
const session = await fetch('/api/sources/source_123/chat/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'Research Discussion',
    model_override: 'gpt-4'
  })
}).then(r => r.json());

// Send a message with streaming response
const eventSource = new EventSource(
  `/api/sources/source_123/chat/sessions/${session.id}/messages`,
  {
    method: 'POST',
    body: JSON.stringify({ message: 'Summarize the key findings' })
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'ai_message':
      updateChatUI(data.content);
      break;
    case 'context_indicators':
      showContextSources(data.data.sources, data.data.insights);
      break;
    case 'complete':
      eventSource.close();
      break;
  }
};
```

### Python Client

```python
import requests
import json

# Create session
response = requests.post('/api/sources/source_123/chat/sessions', json={
    'title': 'Analysis Session',
    'model_override': 'gpt-4'
})
session = response.json()

# Send message (non-streaming)
response = requests.post(
    f'/api/sources/source_123/chat/sessions/{session["id"]}/messages',
    json={'message': 'What are the implications of these findings?'}
)

# For streaming, use requests with stream=True or use SSE client library
```