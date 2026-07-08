"""Unit tests for the subscription gateway translation layer (pure functions)."""

from api import subscription_gateway_translate as tr


# --- Anthropic (claude) ----------------------------------------------------


def test_openai_to_anthropic_splits_system_and_messages():
    body = {
        "model": "claude-sonnet-4",
        "messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "Bye"},
        ],
        "temperature": 0.5,
    }
    out = tr.openai_to_anthropic(body)
    # OAuth subscription requires the Claude Code identity as the first system
    # block; the caller's own system prompt follows.
    assert out["system"] == [
        {"type": "text", "text": tr.CLAUDE_CODE_IDENTITY},
        {"type": "text", "text": "You are helpful."},
    ]
    assert out["model"] == "claude-sonnet-4"
    assert out["max_tokens"] == tr.DEFAULT_MAX_TOKENS
    assert out["temperature"] == 0.5
    assert out["messages"] == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "Bye"},
    ]


def test_openai_to_anthropic_injects_claude_code_identity_without_system():
    # Even with no system message, the Claude Code identity must be present as
    # the first (and only) system block, or Anthropic rejects the OAuth token.
    out = tr.openai_to_anthropic(
        {"model": "claude-opus-4-8", "messages": [{"role": "user", "content": "Hi"}]}
    )
    assert out["system"] == [{"type": "text", "text": tr.CLAUDE_CODE_IDENTITY}]


def test_openai_to_anthropic_tools_and_tool_result():
    body = {
        "model": "claude",
        "messages": [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_weather", "arguments": '{"city":"SF"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "72F"},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
                },
            }
        ],
    }
    out = tr.openai_to_anthropic(body)
    assert out["tools"][0]["name"] == "get_weather"
    assert out["tools"][0]["input_schema"]["type"] == "object"
    # tool_use block on assistant
    assistant = out["messages"][0]
    assert assistant["content"][0]["type"] == "tool_use"
    assert assistant["content"][0]["input"] == {"city": "SF"}
    # tool_result on a following user message
    tool_result = out["messages"][1]
    assert tool_result["role"] == "user"
    assert tool_result["content"][0]["type"] == "tool_result"
    assert tool_result["content"][0]["tool_use_id"] == "call_1"


def test_anthropic_to_openai_text_and_usage():
    resp = {
        "id": "msg_123",
        "model": "claude-sonnet-4",
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "Hello world"}],
        "usage": {"input_tokens": 10, "output_tokens": 3},
    }
    out = tr.anthropic_to_openai(resp, "claude")
    assert out["choices"][0]["message"]["content"] == "Hello world"
    assert out["choices"][0]["finish_reason"] == "stop"
    assert out["usage"] == {
        "prompt_tokens": 10,
        "completion_tokens": 3,
        "total_tokens": 13,
    }


def test_anthropic_to_openai_tool_use_maps_to_tool_calls():
    resp = {
        "id": "msg_1",
        "model": "claude",
        "stop_reason": "tool_use",
        "content": [
            {"type": "tool_use", "id": "tu_1", "name": "search", "input": {"q": "x"}}
        ],
        "usage": {"input_tokens": 5, "output_tokens": 2},
    }
    out = tr.anthropic_to_openai(resp, "claude")
    tc = out["choices"][0]["message"]["tool_calls"][0]
    assert tc["function"]["name"] == "search"
    assert tc["function"]["arguments"] == '{"q": "x"}'
    assert out["choices"][0]["finish_reason"] == "tool_calls"


def test_anthropic_sse_text_delta_to_chunk():
    chunk = tr.anthropic_sse_to_openai(
        "content_block_delta",
        {"index": 0, "delta": {"type": "text_delta", "text": "Hi"}},
        "claude",
    )
    assert chunk["choices"][0]["delta"]["content"] == "Hi"
    assert chunk["object"] == "chat.completion.chunk"


def test_anthropic_sse_message_delta_finish():
    chunk = tr.anthropic_sse_to_openai(
        "message_delta", {"delta": {"stop_reason": "end_turn"}}, "claude"
    )
    assert chunk["choices"][0]["finish_reason"] == "stop"


def test_anthropic_headers_no_api_key():
    h = tr.anthropic_headers("tok123")
    assert h["authorization"] == "Bearer tok123"
    assert h["anthropic-beta"] == tr.ANTHROPIC_OAUTH_BETA
    assert "x-api-key" not in h


# --- ChatGPT Responses (chatgpt / Codex) -----------------------------------


def test_openai_to_responses_maps_roles_and_instructions():
    body = {
        "model": "gpt-5-codex",
        "messages": [
            {"role": "system", "content": "Be terse."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ],
        "stream": True,
    }
    out = tr.openai_to_responses(body)
    assert out["instructions"] == "Be terse."
    assert out["stream"] is True
    assert out["input"][0]["role"] == "user"
    assert out["input"][0]["content"][0]["type"] == "input_text"
    assert out["input"][1]["content"][0]["type"] == "output_text"


def test_openai_to_responses_always_has_instructions():
    # The ChatGPT backend requires a non-empty instructions field even when the
    # request has no system message.
    out = tr.openai_to_responses(
        {"model": "gpt-5.5", "messages": [{"role": "user", "content": "hi"}]}
    )
    assert out["instructions"]
    assert isinstance(out["instructions"], str)


def test_responses_to_openai_extracts_output_text():
    resp = {
        "id": "resp_1",
        "model": "gpt-5-codex",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "Answer"}],
            }
        ],
        "usage": {"input_tokens": 4, "output_tokens": 1},
    }
    out = tr.responses_to_openai(resp, "gpt-5-codex")
    assert out["choices"][0]["message"]["content"] == "Answer"
    assert out["usage"]["total_tokens"] == 5


def test_responses_sse_delta_and_completed():
    delta = tr.responses_sse_to_openai(
        "response.output_text.delta", {"delta": "abc"}, "gpt"
    )
    assert delta["choices"][0]["delta"]["content"] == "abc"
    done = tr.responses_sse_to_openai("response.completed", {}, "gpt")
    assert done["choices"][0]["finish_reason"] == "stop"


def test_chatgpt_headers_include_account():
    h = tr.chatgpt_headers("tok", "acct-9")
    assert h["authorization"] == "Bearer tok"
    assert h["chatgpt-account-id"] == "acct-9"


# --- Shared SSE parsing ----------------------------------------------------


def test_iter_sse_events_event_and_data_pairs():
    lines = [
        "event: content_block_delta\n",
        'data: {"index":0,"delta":{"type":"text_delta","text":"Hi"}}\n',
        "\n",
        "data: [DONE]\n",
    ]
    events = list(tr.iter_sse_events(lines))
    assert events[0][0] == "content_block_delta"
    assert events[0][1]["delta"]["text"] == "Hi"
    assert events[-1] == ("done", {})
