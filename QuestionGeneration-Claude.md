# Open Notebook - CLAUDE.md

## Project Overview

Open Notebook is a privacy-focused AI research assistant. Three-tier architecture:
- **Frontend**: Next.js 16 + React 19, Zustand, TanStack Query, Tailwind + Shadcn/ui — port 3000
- **API**: FastAPI 0.104+, Python 3.11+, LangGraph workflows, Surreal-Commands job queue — port 5055
- **Database**: SurrealDB with vector embeddings and semantic search — port 8000

AI providers via **Esperanto** (OpenAI, Anthropic, Google, Groq, Ollama, Mistral, DeepSeek, xAI). All model calls go through `provision_langchain_model()` — never instantiate providers directly.

All DB operations are async. Migrations run automatically on API startup.

**Key files to understand before touching anything:**
- `api/CLAUDE.md` — FastAPI routers, service pattern
- `open_notebook/graphs/CLAUDE.md` — LangGraph workflow design
- `open_notebook/ai/CLAUDE.md` — ModelManager, Esperanto usage
- `open_notebook/database/CLAUDE.md` — SurrealDB async patterns

---

## Feature: Question Paper Generator

> NFO-specific feature. Automates question paper creation via a multi-agent LangGraph pipeline to replace manual authoring. Solves the repetition problem of single-prompt generation by giving each agent a clean, scoped context.

### Why multi-agent

Single-prompt generation degrades because all previously generated questions accumulate in context — the model pattern-matches against its own output and converges on similar stems, structures, and distractors. The fix is architectural: each agent gets only what it needs, nothing more.

### Pipeline: `open_notebook/graphs/question_paper.py`

Five agents wired as a LangGraph state machine:

```
Syllabus + Config
      │
      ▼
Agent 1 — Generator        ◄─── retry with failure reason (max 3x)
      │                              │
      ▼                              │
Agent 2 — Deduplicator              │
      │                              │
      ▼                              │
Agent 3 — Quality Reviewer ─────────┘ (FAIL path loops back)
      │ (PASS path)
      ▼
Agent 4 — Assembler
      │
      ▼
Agent 5 — Validator + Answer Key
      │
      ▼
Final Paper + Answer Key
```

### State shape

```python
class PaperState(TypedDict):
    topic: str
    difficulty: str                    # easy | medium | hard
    target_marks: int
    section_config: dict               # e.g. {"mcq": 10, "short": 5, "scenario": 3}
    used_stems: list[str]              # running list of question openers — passed to generator
    raw_questions: list[dict]
    deduplicated: list[dict]
    approved: list[dict]
    rejected_with_feedback: list[dict]
    final_paper: dict
    answer_key: list[dict]
    retry_count: int                   # guards against infinite loops
```

### Agent 1 — Generator

**Job**: Raw question generation only. No reviewing, no deduplication.

**Key technique — forced variety**: Pass `used_stems` (collected across all prior batches this session) so the model cannot reuse an opening stem. Also enforce question type rotation in the prompt: definition → application → analysis → scenario → calculation.

Generate in small topic-scoped batches (5–8 questions per call), not one giant call. Each batch starts with a clean context — only the topic, difficulty, and the forbidden stems list.

```python
GENERATOR_SYSTEM = """
You are a question generator for financial literacy exams (NFO curriculum).

MANDATORY VARIETY RULES:
- Rotate question types: definition → application → analysis → scenario → calculation
- Never start a question with a stem from this list: {used_stems}
- For MCQs: all 3 distractors must be plausible to someone with partial knowledge
- Distribute difficulty: 40% recall, 40% application, 20% analysis

Topic: {topic}
Difficulty: {difficulty}
Batch size: {batch_size}

Return JSON array. Each item: {question, type, options (if MCQ), answer, explanation, topic, difficulty}
"""
```

Use `claude-haiku-4-5` here — high volume, cheap, fast.

### Agent 2 — Deduplicator

**Job**: Remove semantic near-duplicates from the current batch AND against the persistent question bank in SurrealDB.

Two-pass approach:
1. **Embedding similarity**: Query SurrealDB vector search for each new question. Flag any pair with cosine similarity > 0.87 as a duplicate candidate.
2. **LLM semantic check**: Send flagged pairs to the model to confirm — embeddings can false-positive on questions that share vocabulary but test different concepts.

```python
DEDUP_SYSTEM = """
You are a deduplication agent. Given these questions, identify:
1. Exact duplicates
2. Questions testing the same concept with different wording
3. Questions where knowing one's answer trivially reveals another's

Return: {kept: [...], removed: [{question, reason}]}
Do not remove questions that share a topic but test genuinely different aspects.
"""
```

### Agent 3 — Quality Reviewer

**Job**: Score each question on a rubric. Return PASS or FAIL with a specific rewrite instruction for failures. The rewrite instruction is fed back to Agent 1 on retry — not a generic "try again".

```python
REVIEWER_SYSTEM = """
Review each question. Score 1–5 on:
- clarity: unambiguous wording
- distractor_quality: wrong options are plausible but clearly wrong to someone who knows
- difficulty_match: matches stated level ({difficulty})
- curriculum_alignment: tests {topic} as specified, not tangential content

FAIL if any dimension scores ≤ 2.
For FAIL: provide a one-sentence rewrite instruction (specific, actionable).

Return JSON: [{question_id, scores, verdict, rewrite_instruction}]
"""
```

Use `claude-sonnet-4-6` here — quality judgment, fewer calls, worth the cost.

### Agent 4 — Assembler

**Job**: Structural composition only. Takes the approved question pool, produces the final ordered paper. No generation.

```python
ASSEMBLER_SYSTEM = """
Assemble a question paper from the approved pool.

Section config: {section_config}
Total marks: {target_marks}

Rules:
- No two consecutive questions from the same topic
- Difficulty ramps within each section (easy → hard)
- Total marks must equal {target_marks} exactly

Return: ordered list with section headers, question numbers, marks per question.
"""
```

### Agent 5 — Validator + Answer Key

**Job**: Coverage audit + answer key generation. Flags syllabus gaps so they can be flagged to the teacher rather than silently shipped.

```python
VALIDATOR_SYSTEM = """
Given this assembled paper:
1. Map each question to a curriculum objective from: {curriculum_objectives}
2. List any objectives with zero coverage — these are gaps
3. Generate the answer key: each answer with a 2-sentence explanation
4. Verify marks total matches {target_marks}

Return: {coverage_map, gaps, answer_key, marks_total, is_valid}
"""
```

### LangGraph conditional edges

```python
def should_retry(state: PaperState) -> str:
    if state["rejected_with_feedback"] and state["retry_count"] < 3:
        return "generate"   # loop back with failure reasons in context
    return "assemble"       # proceed even if some questions failed after 3 tries
```

### Persistent question bank

Every approved question is saved to SurrealDB as a `QuestionRecord`. Before generating a new batch, Agent 2 queries the bank for semantic duplicates — this prevents regenerating questions across sessions, not just within one run.

Migration to add: `migrations/009_question_bank.surql`

```sql
DEFINE TABLE question_bank SCHEMAFULL;
DEFINE FIELD topic ON question_bank TYPE string;
DEFINE FIELD question ON question_bank TYPE string;
DEFINE FIELD type ON question_bank TYPE string;
DEFINE FIELD difficulty ON question_bank TYPE string;
DEFINE FIELD answer ON question_bank TYPE string;
DEFINE FIELD explanation ON question_bank TYPE string;
DEFINE FIELD embedding ON question_bank TYPE array;
DEFINE INDEX question_bank_embedding ON question_bank FIELDS embedding MTREE DIMENSION 1536;
```

---

## API surface: `api/routers/question_paper.py`

```
POST   /papers/generate          — submit config, returns {job_id}
GET    /papers/{job_id}/status   — poll async job status
GET    /papers/{job_id}/result   — fetch completed paper + answer key
GET    /papers/bank/search       — semantic search across question bank
DELETE /papers/bank/{question_id} — remove a question from the bank
```

Job runs via Surreal-Commands (same pattern as podcast generation). Frontend polls `/status` until `status == "complete"`.

---

## Model selection guidance

| Agent | Recommended model | Reason |
|---|---|---|
| Generator | `claude-haiku-4-5` | High volume, many calls per paper |
| Deduplicator | `claude-haiku-4-5` | Simple classification task |
| Reviewer | `claude-sonnet-4-6` | Quality judgment needs stronger reasoning |
| Assembler | `claude-haiku-4-5` | Structural, not generative |
| Validator | `claude-sonnet-4-6` | Coverage analysis + explanation generation |

For local/offline deployment: `qwen2.5:14b` via Ollama is the best local option. The multi-agent structure compensates significantly for weaker model output — focused context beats raw capability.

---

## Files to create

```
open_notebook/graphs/question_paper.py   ← LangGraph pipeline
open_notebook/domain/question_bank.py   ← QuestionRecord model + repo
api/routers/question_paper.py           ← REST endpoints
api/question_paper_service.py           ← job submission + orchestration
migrations/009_question_bank.surql      ← schema migration
```

---

## Adding a new LangGraph workflow (reference)

1. Create `open_notebook/graphs/workflow_name.py`
2. Define `StateDict` and node functions
3. Build graph with `.add_node()` / `.add_edge()` / `.add_conditional_edges()`
4. Invoke in service: `await graph.ainvoke(state, config={...})`
5. Test: `tests/test_graphs.py`

## Adding a new API endpoint (reference)

1. Create `api/routers/feature.py`
2. Create `api/feature_service.py`
3. Define schemas in `api/models.py`
4. Register in `api/main.py`
5. Verify at `http://localhost:5055/docs`