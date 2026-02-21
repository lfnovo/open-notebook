"""
Fake OpenAI-compatible chat completions server.
Returns a plain "hello" for normal requests, and valid JSON when the
prompt asks for structured output (tool calls / json_schema / response_format).

Run with: uv run python scripts/fake_model.py

Configure Open Notebook with:
  - Provider: openai
  - Model: fake-hello
  - Base URL: http://host.docker.internal:9999/v1
  - API Key: fake-key
"""

import json
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


def _make_choice(content: str, model: str) -> dict:
    return {
        "id": "chatcmpl-fake",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "fake-hello")

    # If the caller wants structured / JSON output, return minimal valid JSON
    response_format = body.get("response_format", {})
    tools = body.get("tools", [])

    if response_format.get("type") == "json_object" or tools:
        content = json.dumps({"result": "hello", "status": "ok"})
    elif response_format.get("type") == "json_schema":
        # Return an empty object that matches any schema
        schema = response_format.get("json_schema", {}).get("schema", {})
        props = schema.get("properties", {})
        content = json.dumps({k: "hello" for k in props} if props else {"result": "hello"})
    else:
        content = "hello"

    return JSONResponse(_make_choice(content, model))


@app.get("/v1/models")
async def list_models():
    return JSONResponse({"data": [{"id": "fake-hello", "object": "model"}]})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)
