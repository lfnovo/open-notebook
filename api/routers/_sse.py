"""Server-Sent Events helpers for the streaming chat endpoint.

`POST /api/chat/execute/stream` answers one turn as an SSE stream. Generation
stays inside the LangGraph chat graph: the endpoint consumes
`graph.astream(..., stream_mode="messages")` and forwards the node's model
deltas. That keeps every future graph feature (loops, tools) on the streaming
path, and it means cancelling the consumer cancels the provider request.

The event contract (mirrored by the frontend SSE consumer):

    user_message -> token… -> (context_indicators) -> complete
    error                                        (on failure)

`token` events carry filtered model deltas — `thinking` markup has been stripped
by `ThinkingFilter` — and `complete` carries the cleaned final text that was
checkpointed. Consumers replace the streamed text with `complete` (or with the
refetched thread after a stop).

Generation runs in a queue-fed task rather than inside the response generator:
the generator stays free to write keepalives and poll for disconnects, and
cancelling the task closes the provider connection instead of only detaching
the reader.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional, Tuple

from langchain_core.messages import AIMessage, AIMessageChunk

from open_notebook.exceptions import OpenNotebookError
from open_notebook.utils.error_classifier import classify_error

# Keepalive cadence. Long prefill on a slow local model means minutes with no
# token on the wire; anything longer than a typical proxy idle timeout (60s for
# Cloudflare) gets the connection cut, so ping comfortably under it.
KEEPALIVE_INTERVAL_SECONDS = 15.0

# How often to poll `is_disconnected` while waiting for the model. Stop has to
# bite during prefill, when no token is flowing to hang the check off.
DISCONNECT_POLL_SECONDS = 1.0

# Hard ceiling for a single turn, keepalives included. Local models can be slow
# but not unbounded; without this a wedged provider holds the SSE stream (and
# the client's Stop button) hostage indefinitely.
MAX_STREAM_SECONDS = 900.0

# Longest typed error message forwarded to a client.
MAX_ERROR_CHARS = 200

# Raised when a turn streams successfully but ends up with no text.
EMPTY_REPLY_MESSAGE = (
    "The model returned an empty response. Try again, or pick a different "
    "model if this keeps happening."
)

# Queue item: ("token", text) while streaming, then exactly one of
# ("done", payload) or ("error", exception).
QueueItem = Tuple[str, Any]

OPEN_TAG = " thinking"
CLOSE_TAG = "</think>"

# While the stream is still at its beginning, hold text back until we know
# whether it is a tagless thinking preamble (``reasoning</think>answer``).
# Past this many characters it is treated as an answer and flushed.
LEAD_BUFFER_LIMIT = 400


def sse(payload: Dict[str, Any]) -> str:
    """Encode a payload as an SSE `data:` frame."""
    return f"data: {json.dumps(payload)}\n\n"


def sse_keepalive() -> str:
    """An SSE comment frame.

    Ignored by EventSource/fetch consumers, but it puts bytes on the wire and
    resets idle timers in intermediate proxies.
    """
    return ": ping\n\n"


def clean_stream_chunk(content: Any) -> str:
    """Normalize a streamed chunk's content to a plain string.

    Some providers (Anthropic, Gemini, …) return content as a list of
    content-block dicts rather than a string. Mirrors the normalization
    `extract_text_content` does for a whole message.
    """
    if isinstance(content, list):
        return "".join(
            c.get("text", "") if isinstance(c, dict) else str(c) for c in content
        )
    return content or ""


def _partial_tag_suffix(text: str, tag: str) -> int:
    """Length of the longest suffix of `text` that is a proper prefix of `tag`."""
    for size in range(min(len(tag) - 1, len(text)), 0, -1):
        if text.endswith(tag[:size]):
            return size
    return 0


class ThinkingFilter:
    """Strip ` thinking…</think>` from a token stream across chunk boundaries.

    A tag can be split between chunks, so text is buffered until it is resolvable
    and only then returned. Two shapes are handled beyond the well-formed one:
    a tagless preamble ending in `</think>` (stripped while still at the start,
    up to `LEAD_BUFFER_LIMIT` characters) and an unterminated ` thinking` block
    (dropped at `flush`, matching `parse_thinking_content`).
    """

    _LEAD = "lead"
    _BODY = "body"
    _THINKING = "thinking"

    def __init__(self) -> None:
        self._buf = ""
        self._state = self._LEAD

    def feed(self, text: str) -> str:
        """Consume a chunk and return the answer text it released."""
        if not text:
            return ""
        self._buf += text
        out: list[str] = []
        while self._buf:
            if self._state == self._THINKING:
                end = self._buf.find(CLOSE_TAG)
                if end < 0:
                    keep = _partial_tag_suffix(self._buf, CLOSE_TAG)
                    self._buf = self._buf[-keep:] if keep else ""
                    break
                self._buf = self._buf[end + len(CLOSE_TAG) :]
                self._state = self._BODY
                continue

            if self._state == self._LEAD:
                opened = self._buf.find(OPEN_TAG)
                closed = self._buf.find(CLOSE_TAG)
                if opened >= 0 and (closed < 0 or opened < closed):
                    out.append(self._buf[:opened])
                    self._buf = self._buf[opened + len(OPEN_TAG) :]
                    self._state = self._THINKING
                    continue
                if closed >= 0:
                    # Tagless preamble: everything up to here was thinking.
                    self._buf = self._buf[closed + len(CLOSE_TAG) :]
                    self._state = self._BODY
                    continue
                if len(self._buf) > LEAD_BUFFER_LIMIT:
                    out.append(self._buf)
                    self._buf = ""
                    self._state = self._BODY
                break

            # Body: a stray opening tag still starts a thinking block.
            opened = self._buf.find(OPEN_TAG)
            if opened >= 0:
                out.append(self._buf[:opened])
                self._buf = self._buf[opened + len(OPEN_TAG) :]
                self._state = self._THINKING
                continue
            keep = _partial_tag_suffix(self._buf, OPEN_TAG)
            if keep:
                out.append(self._buf[:-keep])
                self._buf = self._buf[-keep:]
            else:
                out.append(self._buf)
                self._buf = ""
            break
        return "".join(out)

    def flush(self) -> str:
        """Release whatever is left when the stream ends."""
        if self._state == self._THINKING:
            return ""
        rest, self._buf = self._buf, ""
        return rest


def format_error_event(error: BaseException) -> str:
    """Build an `error` event without leaking internals to the client.

    Typed `OpenNotebookError`s already carry a user-facing message; anything
    else (raw provider exception, transport error) goes through the classifier.
    """
    if isinstance(error, OpenNotebookError):
        message = str(error)[:MAX_ERROR_CHARS]
    else:
        _, message = classify_error(error)
    return sse({"type": "error", "message": message})


def stream_headers() -> Dict[str, str]:
    """Headers that stop buffering/compression on the way to the browser.

    SSE is served through a dedicated Next.js route handler rather than the
    `rewrites()` proxy, which gzips the stream to completion. `no-transform`
    and `X-Accel-Buffering: no` also cover nginx and other reverse proxies.
    """
    return {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


@dataclass
class StreamOutcome:
    """How a stream ended. Read by the caller after the pump returns."""

    kind: str = "pending"  # pending | done | error | disconnected | timeout
    payload: Any = None


async def run_graph(
    queue: "asyncio.Queue[QueueItem]",
    graph: Any,
    state: Any,
    config: Any,
    node: str,
    parts: list,
    thinking_filter: ThinkingFilter,
) -> None:
    """Stream one graph run into `queue`, collecting answer text in `parts`.

    Only chunks produced by `node` are forwarded. Never raises into the caller:
    task creation is fire-and-forget, so failures are delivered as an
    `("error", exc)` item. Cancellation is re-raised so the task ends cancelled
    rather than as a bogus error.
    """
    try:
        raw = ""
        async for chunk, metadata in graph.astream(
            state, config, stream_mode="messages"
        ):
            if metadata.get("langgraph_node") != node:
                continue
            chunk_text = clean_stream_chunk(getattr(chunk, "content", None))
            if not chunk_text:
                continue

            # A non-streaming model emits one complete `AIMessage` instead of
            # deltas; after deltas the node's return value is also replayed as
            # a complete message. Only the former should be forwarded.
            is_complete_message = isinstance(chunk, AIMessage) and not isinstance(
                chunk, AIMessageChunk
            )
            if is_complete_message:
                if raw:
                    continue
                text = thinking_filter.feed(chunk_text) + thinking_filter.flush()
                if text:
                    raw = chunk_text
                    parts.append(text)
                    await queue.put(("token", text))
                continue

            raw += chunk_text
            text = thinking_filter.feed(chunk_text)
            if text:
                parts.append(text)
                await queue.put(("token", text))
        tail = thinking_filter.flush()
        if tail:
            parts.append(tail)
            await queue.put(("token", tail))
        await queue.put(("done", None))
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - delivered as an SSE error event
        await queue.put(("error", exc))


async def stream_events(
    queue: "asyncio.Queue[QueueItem]",
    outcome: StreamOutcome,
    *,
    is_disconnected: Optional[Callable[[], Awaitable[bool]]] = None,
    interval: Optional[float] = None,
    timeout: Optional[float] = None,
) -> AsyncGenerator[str, None]:
    """Pump `queue` into SSE frames until the turn ends.

    Emits `token` frames as they arrive and a keepalive comment while the model
    is silent. Returns (leaving `outcome` set) when the worker signals done, on
    client disconnect, on timeout, or on worker error — the caller owns the
    envelope events, persistence and error rendering.
    """
    # Resolved per call (not as defaults) so tests and operators can tune the
    # module constants without re-binding arguments.
    ping = KEEPALIVE_INTERVAL_SECONDS if interval is None else interval
    limit = MAX_STREAM_SECONDS if timeout is None else timeout
    poll = DISCONNECT_POLL_SECONDS if is_disconnected is not None else ping
    loop = asyncio.get_running_loop()
    deadline = loop.time() + limit
    next_ping = loop.time() + ping
    while True:
        # Enforced on every iteration, not just when the queue is idle: a model
        # that never stops producing tokens must still hit the ceiling.
        if loop.time() > deadline:
            outcome.kind = "timeout"
            return
        if is_disconnected is not None and await is_disconnected():
            outcome.kind = "disconnected"
            return
        if loop.time() >= next_ping:
            next_ping = loop.time() + ping
            yield sse_keepalive()
        try:
            kind, payload = await asyncio.wait_for(
                queue.get(), timeout=min(poll, max(0.001, deadline - loop.time()))
            )
        except asyncio.TimeoutError:
            continue
        if kind == "token":
            yield sse({"type": "token", "content": payload})
            continue
        outcome.kind = kind
        outcome.payload = payload
        return


async def stop_task(task: Optional["asyncio.Task[Any]"]) -> None:
    """Cancel a generation task and wait for it to unwind."""
    if task is None or task.done():
        return
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def finalize_stream(
    task: Optional["asyncio.Task[Any]"], settle: Callable[[], Awaitable[None]]
) -> None:
    """Stop generation and run the turn's teardown, cancellation-proof.

    Starlette cancels the response task when the client disconnects, and inside
    an already-cancelled task every fresh `await` raises immediately: a bare
    `finally` would be cut off at `stop_task` and the partial answer never
    persisted. Running the teardown in its own task behind `shield` lets it
    finish after the response task is gone.
    """

    async def _run() -> None:
        # Stops the provider request too, not just the reader.
        await stop_task(task)
        await settle()

    await asyncio.shield(_run())
