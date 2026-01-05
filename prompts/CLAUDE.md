# Prompts Module

Jinja2 prompt templates for multi-provider AI workflows in Open Notebook.

## Purpose

Centralized prompt repository using `ai_prompter` library to:
1. Separate prompt engineering from Python application logic
2. Provide reusable Jinja2 templates with variable injection
3. Support multi-stage prompt chains (orchestrated by LangGraph workflows)
4. Ensure consistency across similar workflows (chat, search, content generation)

## Architecture Overview

**Template Organization by Workflow**:
- **`ask/`**: Multi-stage search synthesis (entry → query_process → final_answer)
- **`chat/`**: Conversational agent with notebook context (system prompt only)
- **`source_chat/`**: Source-focused chat with insight injection (system prompt only)
- **`podcast/`**: Podcast generation pipeline (outline → transcript)

**Rendering Pattern** (all workflows):
```python
from ai_prompter import Prompter

# Load template + render with variables
system_prompt = Prompter(prompt_template="ask/entry", parser=parser).render(
    data=state
)

# Then invoke LLM
model = await provision_langchain_model(system_prompt, ...)
response = await model.ainvoke(system_prompt)
```

See detailed workflow integration in `open_notebook/graphs/CLAUDE.md` for how each template fits into chat.py, ask.py, source_chat.py.

## Prompt Engineering Patterns

### 1. Multi-Stage Chain (Ask Workflow)

Three-template chain for intelligent search:

```
entry.jinja (user question → search strategy)
    ↓
query_process.jinja (run each search, generate sub-answer)
    ↓ (multiple parallel)
final_answer.jinja (synthesize all results into final response)
```

**Key pattern**: `entry.jinja` generates JSON-structured reasoning (via PydanticOutputParser). Each `query_process.jinja` invocation receives one search term + retrieved results. `final_answer.jinja` combines all answers with proper source citation.

### 2. Conditional Variable Injection (Podcast Workflow)

Templates accept optional variables for context assembly:

```jinja
{% if notebook %}
# PROJECT INFORMATION
{{ notebook }}
{% endif %}

{% if context %}
# CONTEXT
{{ context }}
{% endif %}
```

Enabled by Jinja2's conditional blocks. Critical for podcast outline (handles list or string context) and source_chat (injects variable notebook/insight data).

### 3. Repeated Emphasis on Citation Format (Ask & Chat)

All response-generating templates emphasize source citation rules:
- Document ID syntax: `[source:id]`, `[note:id]`, `[insight:id]`
- "Do not make up document IDs" repeated multiple times
- Example citations provided inline

**Rationale**: LLMs naturally hallucinate citations without explicit guidance; repetition + examples reduce hallucination.

### 4. Format Instructions Delegation

Templates accept external `{{ format_instructions }}` variable:

```jinja
# OUTPUT FORMATTING
{{ format_instructions }}
```

Allows caller to inject JSON schema, XML format, or other output constraints without modifying template. Decouples prompt from output format evolution.

### 5. JSON Output with Extended Thinking Support

Podcast templates include extended thinking pattern:

```jinja
IMPORTANT OUTPUT FORMAT:
- If you use extended thinking with <think> tags, put ALL your reasoning inside <think></think> tags
- Put the final JSON output OUTSIDE and AFTER any <think> tags
```

Guides models with extended thinking capability to separate reasoning from output (cleaner parsing downstream).

## File Catalog

**`ask/` - Search Synthesis Pipeline**:
- **entry.jinja**: Analyzes user question, generates search strategy with JSON output (term + instructions per search)
- **query_process.jinja**: Accepts one search term + retrieved results, generates sub-answer with citations
- **final_answer.jinja**: Combines all sub-answers into coherent final response, enforces source citation

**`chat/` - Conversational Agent**:
- **system.jinja**: Single system prompt for general chat. Uses conditional blocks for optional notebook context. Emphasizes citation format.

**`source_chat/` - Source-Focused Chat**:
- **system.jinja**: Single system prompt for source-specific discussion. Injects source metadata (ID, title, topics) + selected context. Conditional blocks for optional notebook/context data.

**`podcast/` - Podcast Generation**:
- **outline.jinja**: Takes briefing + content + speaker profiles (list support via Jinja2 for-loop). Generates JSON outline with segments (name, description, size).
- **transcript.jinja**: Takes outline + segment index + optional existing transcript. Generates JSON dialogue array (speaker name + dialogue). Iterates speakers with for-loop.

## Key Dependencies

- **ai_prompter**: Prompter class for Jinja2 template rendering with optional OutputParser binding
- **Jinja2** (transitive via ai_prompter): Template syntax (if/for, filters, variable interpolation)
- **No external AI calls**: Templates are pure text; LLM invocation happens in calling code (graphs/)

## How to Add New Template

1. **Create subdirectory** in `prompts/` matching workflow name (e.g., `prompts/new_workflow/`)
2. **Define .jinja file(s)** with Jinja2 syntax:
   - Use `{{ variable_name }}` for scalar injection
   - Use `{% if condition %} ... {% endif %}` for optional sections
   - Use `{% for item in list %} ... {% endfor %}` for iteration
3. **Document template variables** as inline comments (follow existing templates)
4. **Reference in calling code** (graphs/):
   ```python
   from ai_prompter import Prompter
   prompt = Prompter(prompt_template="new_workflow/template_name").render(data=context_dict)
   ```
5. **If structured output needed**: Pass `parser=PydanticOutputParser(...)` to Prompter
6. **Document in graphs/CLAUDE.md** how new template fits into workflow chain

## Important Quirks & Gotchas

1. **Template path syntax**: Uses forward slashes without `.jinja` extension in Prompter. `"ask/entry"` maps to `/prompts/ask/entry.jinja`
2. **Variable key convention**: All data passed as `data=dict` arg to `.render()`. Template accesses variables directly (e.g., `{{ question }}`). Ensure dict keys match template variable names.
3. **OutputParser binding**: When using PydanticOutputParser, Prompter auto-injects `{{ format_instructions }}` into template. If template doesn't have this placeholder, parser is ignored.
4. **Jinja2 whitespace sensitivity**: Template indentation doesn't affect output, but raw newlines do. Use explicit `\n` or trim filters if output formatting matters.
5. **Conditional blocks are loose**: Jinja2 if-condition evaluates any truthy value (non-empty string, list, dict). `{% if variable %}` is False for empty string/"" but True for any non-empty content.
6. **For-loop list assumption**: Templates using `{% for item in list %}` don't validate list type. If caller passes string instead of list, iteration happens character-by-character (bug risk).
7. **No template composition/inheritance**: Templates are flat (no `{% extends %}` or `{% include %}`). Each workflow keeps templates independent to avoid coupling.
8. **Citation ID format is caller's responsibility**: Templates emphasize citation rules but don't validate. If caller returns wrong ID format, template can't catch it upstream.
9. **Parser extraction happens post-render**: OutputParser.parse() is called AFTER `.render()` returns string. If template has syntax errors, render fails before parsing logic runs.
10. **Template cache**: Prompter likely caches loaded templates. File edits require app restart if using cached instance.

## Testing Patterns

**Manual render test**:
```python
from ai_prompter import Prompter

prompt = Prompter(prompt_template="ask/entry").render(
    data={"question": "What is RAG?"}
)
print(prompt)  # Inspect Jinja2 output before sending to LLM
```

**With parser**:
```python
from pydantic import BaseModel
from langchain_core.output_parsers.pydantic import PydanticOutputParser

class Strategy(BaseModel):
    reasoning: str
    searches: list

parser = PydanticOutputParser(pydantic_object=Strategy)
prompt = Prompter(prompt_template="ask/entry", parser=parser).render(
    data={"question": "..."}
)
# prompt now includes {{ format_instructions }} substitution
```

**Integration test** (invoke full graph):
See `open_notebook/graphs/ask.py` for how entry.jinja is invoked inside ask_graph workflow.

## Reference Documentation

- **Jinja2 syntax guide**: See existing templates for for-loop, if-conditional, variable interpolation patterns
- **Graph integration**: `open_notebook/graphs/CLAUDE.md` documents which template is used in which workflow
- **Sub-directory CLAUDE.md files**: `ask/CLAUDE.md`, `chat/CLAUDE.md`, `podcast/CLAUDE.md` (if created) provide template-specific implementation notes
