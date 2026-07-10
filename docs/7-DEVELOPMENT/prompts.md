# Prompt Engineering

How prompts are organized and the patterns they use. All prompts are Jinja2 templates under
`prompts/`, rendered with the [ai-prompter](https://github.com/lfnovo/ai-prompter) library —
prompt engineering lives in templates, not Python.

## Layout & rendering

Templates are grouped by workflow — `ask/`, `chat/`, `source_chat/`, `podcast/` — and referenced
by path without extension:

```python
from ai_prompter import Prompter
prompt = Prompter(prompt_template="ask/entry", parser=parser).render(data=state)
```

Mechanical rules (path syntax, `data=` key matching, parser injection, no inheritance, cache →
restart) are in [`open_notebook/AGENTS.md`](../../open_notebook/AGENTS.md). This page covers the
*patterns*.

## Pattern: multi-stage chain (ask workflow)

The ask pipeline is three templates orchestrated by `graphs/ask.py`:

```
entry.jinja          user question → JSON search strategy (PydanticOutputParser)
   ↓
query_process.jinja  one search term + retrieved results → sub-answer (parallel, one per search)
   ↓
final_answer.jinja   all sub-answers → synthesized final response with citations
```

The stage boundaries let each prompt do one job well, and the JSON strategy output makes the
fan-out deterministic.

## Pattern: conditional variable injection

Templates accept optional variables via Jinja conditionals, so one template serves several
context shapes (podcast outline handles list or string context; source_chat injects optional
notebook/insight data):

```jinja
{% if notebook %}
# PROJECT INFORMATION
{{ notebook }}
{% endif %}
```

Watch the loose truthiness (`{% if var %}` is false for empty string/list) and the for-loop
assumption (passing a string where a list is expected iterates character by character).

## Pattern: repeated citation emphasis

Response-generating templates (ask, chat) state the citation rules — `[source:id]`, `[note:id]`,
`[insight:id]`, "do not make up document IDs" — **multiple times, with inline examples**. LLMs
hallucinate citations without this; repetition + examples measurably reduces it. Keep the
repetition when editing these templates.

## Pattern: format-instructions delegation

Templates expose an `{{ format_instructions }}` slot filled by the caller's OutputParser. Output
format evolves in Python (Pydantic models) without touching the template. If the placeholder is
missing, the parser is silently ignored — check for it when adding structured output.

## Pattern: extended-thinking separation (podcast)

Podcast templates instruct thinking models to keep reasoning inside `<think>` tags and emit the
JSON after them; `clean_thinking_content()` strips the tags downstream. If a new template expects
structured output from thinking-capable models, include the same instruction block.
