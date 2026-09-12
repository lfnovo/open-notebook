# Research runtime baseline

This document characterizes the interactive research runtimes in Open
Notebook as they exist on `main` at commit `62b071b` (July 26, 2026):
Notebook Chat, Source Chat, and ASK. It is an observation baseline, not a
redesign proposal.

Source Chat has one deliberate exception: the corrected behavior specified by
[issue #1224](https://github.com/lfnovo/open-notebook/issues/1224) is the
**future baseline**. The current behavior and that target are recorded
separately so later work does not accidentally preserve the known context
loss.

## At a glance

| Concern | Notebook Chat | Source Chat | ASK |
|---|---|---|---|
| API entry | `POST /api/chat/execute` | `POST /api/sources/{source_id}/chat/sessions/{session_id}/messages` | `POST /api/search/ask`; non-streaming variant at `/api/search/ask/simple` |
| Topology | `START → agent → END` | `START → source_chat_agent → END` | `START → agent → Send(provide_answer)* → write_final_answer → END` |
| Invocation | Synchronous graph `invoke` moved to a worker thread | Synchronous graph `invoke` moved to a worker thread | Async graph `astream(..., stream_mode="updates")` |
| Context source | Context payload assembled by `/api/chat/context` and sent back by the client | Source and insights rebuilt from the database on every turn | Vector search per planned query across sources and notes |
| Durable session row | SurrealDB `chat_session` related to a notebook by `refers_to` | SurrealDB `chat_session` related to a source by `refers_to` | None |
| Conversation checkpoint | SQLite `SqliteSaver`, keyed by the normalized `chat_session:*` thread ID | SQLite `SqliteSaver`, keyed by the normalized `chat_session:*` thread ID | None |
| Models | One chat model | One chat model | Strategy, per-search answer, and final-answer models |
| Transport output | One JSON response containing the complete message list | SSE events | SSE events, or one `AskResponse` from the simple endpoint |

The two chat graphs open separate SQLite connections to the same
`LANGGRAPH_CHECKPOINT_FILE`, currently
`./data/sqlite-db/checkpoints.sqlite`. ASK compiles without a checkpointer.

## Notebook Chat

### Topology and request path

```text
client
  ├─ POST /api/chat/context
  │    └─ build_notebook_context(notebook, context_config)
  └─ POST /api/chat/execute
       ├─ load chat_session and its refers_to notebook
       ├─ load LangGraph checkpoint by thread_id
       ├─ append HumanMessage
       ├─ START → agent → END
       ├─ save chat_session (updates its timestamp)
       └─ return all checkpointed messages as JSON
```

Context selection and response execution are separate calls. The context
endpoint returns the structured `{"sources": [...], "notes": [...]}` payload
plus estimated token and character counts. The execute endpoint trusts the
context payload sent by the caller; the graph itself performs no database
search or context construction.

### Inputs, state, and context

The API input is:

```python
{
    "session_id": str,
    "message": str,
    "context": dict,
    "model_override": str | None,
}
```

The graph state is:

```python
{
    "messages": list,                 # add_messages reducer
    "notebook": Notebook | None,
    "context": str | None,            # receives the API's dict at runtime
    "context_config": dict | None,    # declared but not populated by execute
    "model_override": str | None,
}
```

`build_notebook_context` has two policies:

- With an explicit config, status strings select no context, source insights
  (`Source.get_context("short")`), or full source content
  (`Source.get_context("long")`). Notes are included only for `full content`.
- Without a config, every notebook source and note is included with short
  context. Source insights are batch-fetched before formatting.

Per-item context failures are logged and skipped. The token count returned by
the context endpoint is informational; it does not truncate the payload.

The `chat/system.jinja` prompt receives notebook name/description, the supplied
context, and the complete checkpointed message history. A `SystemMessage` is
prepended for the model call.

### Models, outputs, persistence, and events

The router resolves model precedence as request override, then session
override. The graph gives `config.configurable.model_id` precedence over the
state override and provisions purpose `chat` with `max_tokens=8192`.
Provisioning can still select the configured large-context model when the
serialized payload exceeds 105,000 tokens.

The model is invoked synchronously. Extended-thinking markup is removed from
the returned `AIMessage`, and LangGraph checkpoints the updated state. The API
returns:

```python
{"session_id": str, "messages": list[ChatMessage]}
```

Notebook Chat has no SSE event contract. Its observable completion is the
single JSON response. SurrealDB persists session metadata and the notebook
relationship; SQLite persists graph messages and the other state values.
Deleting the session row does not explicitly delete its SQLite checkpoints.

## Source Chat

### Topology and request path

```text
client POST .../messages
  ├─ verify source, chat_session, and refers_to relation in SurrealDB
  ├─ save chat_session (updates its timestamp)
  └─ SSE generator
       ├─ load LangGraph checkpoint by thread_id
       ├─ append HumanMessage and emit user_message
       ├─ START → source_chat_agent → END
       │    ├─ build_source_context(source_id, max_tokens=50_000)
       │    ├─ format source + insights
       │    └─ invoke one chat model
       ├─ emit ai_message event(s)
       ├─ emit context_indicators
       └─ emit complete
```

### Inputs, state, and current context behavior

The message API accepts `message` and an optional model override; source and
session IDs are path parameters. The graph state is:

```python
{
    "messages": list,                         # add_messages reducer
    "source_id": str,
    "source": Source | None,
    "insights": list[SourceInsight] | None,
    "context": str | None,
    "model_override": str | None,
    "context_indicators": {
        "sources": list[str],
        "insights": list[str],
        "notes": list[str],
    } | None,
}
```

The context is rebuilt on every turn rather than reused from the checkpoint.
The current builder:

1. loads the source from SurrealDB;
2. calls `Source.get_context(context_size="short")`, which normally returns ID,
   title, and embedded insights but **not `full_text`**;
3. separately loads source insights;
4. counts the string representation of each item;
5. when over 50,000 tokens, removes insights from the end and can ultimately
   remove the source itself;
6. formats the retained values for `source_chat/system.jinja`.

The formatter has a second policy: if a source dict happens to contain
`full_text`, it cuts that text at 5,000 characters and appends
`[Content truncated]`. Consequently the token budget and character budget can
compound. In normal domain behavior, the earlier `short` context call means
the formatter usually has no source text to include at all.

Context indicators contain IDs for the retained source and separately loaded
insights. They indicate item inclusion, not proof that substantive source text
reached the model.

### Models, outputs, persistence, and events

The request override uses truthy precedence over the session override. The
graph provisions purpose `chat` with `max_tokens=8192`; the configurable model
ID wins over the state override. The model is invoked synchronously and
extended-thinking content is removed.

SurrealDB persists the session row and its source relationship. SQLite
checkpoints messages, source/context snapshots, and context indicators. As in
Notebook Chat, deleting the SurrealDB session does not explicitly clear the
checkpoint.

The SSE contract is:

1. `user_message`
2. zero or more `ai_message`
3. optional `context_indicators`
4. `complete`

On failure it emits `error` and no `complete`. The adapter iterates every AI
message in the graph result, which is the accumulated message state; on later
turns it can therefore re-emit earlier AI messages before the new one.

### Future baseline: issue #1224

The future Source Chat baseline is the corrected contract, not the lossy
behavior above:

- a source that fits within the context budget reaches the prompt in full;
- an oversized source is truncated deterministically and explicitly;
- there is one context budget, preferably token-based, with no second silent
  formatter cut;
- insights are preserved within the remaining budget;
- missing text produces an honest state instead of implying content is
  available;
- context indicators describe what the model actually received.

This baseline does not add single-source RAG, mentions, or structured
citations. The characterization suite includes a strict expected failure for
this future contract. It should be converted to a normal passing regression
test when #1224 lands; current-behavior assertions that encode the 5,000
character cut should be updated in the same change.

## ASK

### Topology and request path

```text
question
  └─ agent: plan up to five searches
       └─ Send(provide_answer) for each search
            ├─ vector_search(term, 10, source=True, note=True)
            └─ answer model for non-empty results
                 └─ write_final_answer after fan-in
                      └─ final-answer model
```

ASK is a request-scoped research graph. It has no session row, conversation
history, durable state, or checkpoint. The graph state is:

```python
{
    "question": str,
    "strategy": Strategy,
    "answers": list[str],       # operator.add reducer across fan-out branches
    "final_answer": str,
}
```

Each `Search` contains a term and extraction instructions. The strategy prompt
allows up to five searches, but this limit is prompt guidance rather than a
Pydantic length constraint.

### Models and search

The API requires explicit IDs for three model roles and verifies all three
`Model` records in SurrealDB before streaming. It also requires a configured
embedding model.

| Stage | Model purpose | Limit | Input/output |
|---|---|---:|---|
| Strategy | `tools` | 2,000 tokens | Question → structured JSON `Strategy` |
| Per-query answer | `tools` | 2,000 tokens | Question + instructions + vector results → cited partial answer |
| Final answer | `tools` | 2,000 tokens | Question + strategy + accumulated partial answers → synthesis |

Every planned search uses `vector_search(term, 10, True, True)`, including
source chunks and notes with the vector-search default minimum score of `0.2`.
The vector path generates a query embedding and calls SurrealDB's
`fn::vector_search`. A query with no results contributes an empty answer list
and does not invoke the per-query answer model.

All model calls are async and thinking markup is removed. Retrieved result IDs
are included in the per-query prompt; citation correctness remains a prompt
contract rather than structured output validation.

### Outputs and events

The streaming endpoint emits graph updates as:

1. `strategy` with reasoning and searches;
2. one `answer` per partial answer;
3. `final_answer`;
4. `complete`, repeating the final answer.

On failure it emits `error` and no `complete`. The simple endpoint consumes the
same update stream internally and returns only:

```python
{"answer": str, "question": str}
```

No ASK question, strategy, retrieval result, partial answer, or final answer is
persisted by this runtime.

## Characterization test seams

`tests/test_research_runtime_characterization.py` avoids provider and live
database dependencies:

- model provisioning returns mocked LangChain models;
- SurrealDB record reads and vector search are mocked at their runtime
  boundaries;
- checkpoint state is represented by a mocked graph state where API behavior
  is under test;
- the compiled graphs are still inspected or invoked to freeze node topology,
  reducers, fan-out, prompts, model-role selection, and outputs;
- SSE adapters are consumed as async generators to freeze event order and
  terminal behavior.

The tests intentionally record surprising current behavior (Source Chat's
secondary truncation and replay of accumulated AI messages). They should
change only alongside an intentional runtime change.
