"""Server-Sent Events helpers shared by the streaming chat routers.

Both the notebook-chat and source-chat streams emit JSON payloads as SSE
`data:` frames, keep the connection alive with `:` comment pings while the
model is preflighting, and run generation in a cancellable task so a client
disconnect stops it instead of letting the model burn tokens to completion.

The event contract (mirrored by the frontend SSE consumers):

    user_message -> token… -> (context_indicators) -> complete
    error                                        (on failure)

`token` events carry raw model deltas; they are the only events the UI needs in
order to render progressively. `complete` carries the cleaned final text and
means the turn was persisted to the checkpoint — consumers replace the streamed
text with it (streamed text can still hold `thinking` markup that is stripped
before persistence).

Generation runs in a queue-fed task rather than inside the response generator:
the generator stays free to write keepalives and poll for disconnects while the
model streams, and cancelling the task closes the provider connection instead of
only detaching the reader.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional, Tuple

from open_notebook.exceptions import OpenNotebookError
from open_notebook.utils.error_classifier import classify_error

# Keepalive cadence. Long prefill on a slow local model means minutes with no
# token on the wire; anything longer than a typical proxy idle timeout (60s for
# Cloudflare) gets the connection cut, so ping comfortably under it.
KEEPALIVE_INTERVAL_SECONDS = 15.0

# Hard ceiling for a single turn, keepalives included. Local models can be slow
# but not unbounded; without this a wedged provider holds the SSE stream (and
# the client's Stop button) hostage indefinitely.
MAX_STREAM_SECONDS = 900.0

# Raised when a turn streams successfully but ends up with no text.
EMPTY_REPLY_MESSAGE = (
    "The model returned an empty response. Try again, or pick a different "
    "model if this keeps happening."
)

# Queue item: ("token", text) while streaming, then exactly one of
# ("done", payload) or ("error", exception).
QueueItem = Tuple[str, Any]


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


def format_error_event(error: BaseException) -> str:
    """Build an `error` event without leaking internals to the client.

    Typed `OpenNotebookError`s already carry a user-facing message; anything
    else (raw provider exception, transport error) goes through the classifier.
    """
    if isinstance(error, OpenNotebookError):
        message = str(error)
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


async def run_generation(
    queue: "asyncio.Queue[QueueItem]",
    model: Any,
    payload: Any,
    parts: list,
) -> None:
    """Stream `model.astream(payload)` into `queue`, collecting chunks in `parts`.

    Never raises into the caller: task creation is fire-and-forget, so failures
    are delivered as an `("error", exc)` item. Cancellation is re-raised so the
    task ends as cancelled rather than as a bogus error.
    """
    try:
        async for chunk in model.astream(payload):
            text = clean_stream_chunk(getattr(chunk, "content", None))
            if text:
                parts.append(text)
                await queue.put(("token", text))
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
    loop = asyncio.get_running_loop()
    deadline = loop.time() + limit
    while True:
        if is_disconnected is not None and await is_disconnected():
            outcome.kind = "disconnected"
            return
        try:
            kind, payload = await asyncio.wait_for(queue.get(), timeout=ping)
        except asyncio.TimeoutError:
            if loop.time() > deadline:
                outcome.kind = "timeout"
                return
            yield sse_keepalive()
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
