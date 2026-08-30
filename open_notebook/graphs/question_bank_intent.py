"""
Bank Batch Intent Planner (Bank Batch only).

Step 7B/7C: derive bank intents, filter on concept+objective, calibrated adherence.
Step 8: novelty brief + delayed intent retirement after repeated duplicates.
Step 5: meaningful variety diagnostics on the same novelty/intent path (not a second planner).
Step 9: expandable catalog cache + chunk-based replenishment (Bank Batch only).

Does NOT replace validators. Does NOT affect Final Paper.
Does NOT change Step 3B duplicate thresholds.
Diversity planner (Step 2) remains a separate, default-OFF feature.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.ai.llm_usage import (
    LLM_STAGE_INTENT_PLANNER_CATALOG,
    LLM_STAGE_INTENT_PLANNER_REPLENISH,
    build_prompt_composition,
)
from open_notebook.config import DATA_FOLDER
from open_notebook.graphs.question_paper_blueprint import (
    _DIFFICULTY_RANK,
    _extract_intent_words,
    _semantic_intent_overlap,
    extract_chapter_concept_catalog,
    intent_fingerprint,
    normalize_difficulty,
)

INTENT_PLANNER_VERSION = "v2"

# Soft target multiplier for catalog size (not a hard requirement).
INTENT_CATALOG_SIZE_MULTIPLIER = 1.5
INTENT_CATALOG_HARD_MULTIPLIER = 2.0
INTENT_CATALOG_SCHEMA_VERSION = "expandable-v1"
INTENT_CATALOG_STATUS_COMPLETE = "complete"
INTENT_CATALOG_STATUS_FAILED = "failed"
INTENT_CATALOG_STATUS_PARTIAL = "partial"


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Step 9 replenishment (Bank Batch). Overridable via env.
INTENT_REPLENISH_BATCH_SIZE = _env_int("QUESTION_BANK_INTENT_REPLENISH_BATCH", 10)
INTENT_MAX_PLANNER_CALLS_PER_BATCH = _env_int(
    "QUESTION_BANK_INTENT_MAX_PLANNER_CALLS", 5
)
INTENT_MAX_REPLENISH_ROUNDS = _env_int(
    "QUESTION_BANK_INTENT_MAX_REPLENISH_ROUNDS", 4
)
INTENT_REPLENISH_UNUSED_THRESHOLD = _env_int(
    "QUESTION_BANK_INTENT_REPLENISH_UNUSED_THRESHOLD", 4
)
INTENT_INITIAL_CATALOG_TARGET_CAP = _env_int(
    "QUESTION_BANK_INTENT_INITIAL_CATALOG_CAP", 24
)

# Objective-similarity threshold (aligned with semantic duplicate spirit).
INTENT_OBJECTIVE_OVERLAP_THRESHOLD = 0.75

# Variety/paraphrase diagnostic overlap — NOT a duplicate-validation gate.
VARIETY_PARAPHRASE_WORD_OVERLAP = 0.55

# Minimum content-word overlap for grounding concept/objective in a chunk.
INTENT_GROUNDING_OVERLAP_THRESHOLD = 0.35

ADHERENCE_STRONG = "STRONG ADHERENCE"
ADHERENCE_PARTIAL = "PARTIAL ADHERENCE"
ADHERENCE_DRIFTED = "DRIFTED"

INTENT_DRIFT_REJECTION = (
    "intent adherence drift: generated question does not test the assigned objective"
)

COGNITIVE_FORMS_BY_DIFFICULTY: Dict[str, List[str]] = {
    "easy": [
        "recall a taught fact",
        "identify a concept",
        "recognize an example/non-example",
        "direct comprehension",
        "direct one-step application",
    ],
    "medium": [
        "apply a concept in a short scenario",
        "interpret information using a taught concept",
        "compare related taught concepts",
        "explain a taught relationship",
    ],
    "difficult": [
        "multi-step application",
        "analyze a scenario using integrated concepts",
        "evaluate options using chapter principles",
        "infer a conclusion from taught material",
    ],
}


# Bank Batch Easy only — lightweight, no LLM. Medium/Difficult unused.
EASY_SAFE_COGNITIVE_FORMS = frozenset(
    COGNITIVE_FORMS_BY_DIFFICULTY["easy"]
)
BANK_BATCH_EASY_INTENT_RULES = """
EASY INTENT RULES (Bank Batch, target difficulty Easy only):
Prefer recall, identify, recognize, direct comprehension, simple example/non-example,
and straightforward one-step application.

Each Easy intent MUST normally have:
- one primary concept
- familiar/direct context
- 0–1 meaningful reasoning step
- minimal interpretation
- minimal decision making
- minimal concept integration

Do NOT create Easy intents whose objective inherently requires:
- multi-step reasoning
- analysis of several facts
- evaluation / best-decision judgement
- comparison across several concepts (including distinguish A vs B in terms of multiple dimensions)
- inference
- integrated application of multiple concepts
- causal “identify how X affects Y” or conditional scenarios (“when one asset underperforms”)

Those objectives belong in Medium/Difficult pools. Keep Easy objectives as taught-fact
recall, naming a concept, recognizing a direct example, or one-step application of a
single taught rule.
"""

_EASY_UNSAFE_FORM_RE = re.compile(
    r"\b("
    r"distinguish|evaluat\w*|infer|analy[sz]\w*|multi-?step|multi-?stage|"
    r"integrat|scenario|interpret information|explain a taught relationship|"
    r"optimal\s+choice|best\s+decision"
    r")\b",
    re.I,
)
_EASY_UNSAFE_OBJECTIVE_RE = re.compile(
    r"\b("
    r"distinguish|versus|\bvs\b|evaluat\w*|infer|analy[sz]\w*|"
    r"multi-?step|multi-?stage|integrat\w*|judg(?:e|ment)|"
    r"best\s+(?:option|choice|decision)|optimal\s+choice|"
    r"several\s+(?:ideas|concepts|facts|dimensions)|"
    r"multiple\s+(?:concepts|dimensions|strategies)|"
    r"two\s+financial\s+strateg|"
    r"causal|trade-?off|weigh|"
    r"compar(?:e|ison).{0,80}(dimension|several|multiple|optimal|best|versus|scenario|strateg)|"
    r"identify how|how\s+.+\s+affect|when\s+one|underperform|"
    r"apply knowledge|using historical|relationship between|depends? on|"
    r"both\s+\w+\s+and\s+\w+"
    r")\b",
    re.I,
)


def intent_is_easy_safe(intent: Optional[Dict[str, Any]]) -> bool:
    """True if the intent's form/objective is Easy-safe. Medium-style intents fail."""
    if not isinstance(intent, dict):
        return False
    form = str(intent.get("cognitive_form") or "").strip().lower()
    objective = str(intent.get("objective") or "").strip()
    concept = str(intent.get("concept") or "").strip()
    probe = f"{form} {objective} {concept}"
    if form and form not in EASY_SAFE_COGNITIVE_FORMS:
        if _EASY_UNSAFE_FORM_RE.search(form):
            return False
        medium_forms = {f.lower() for f in COGNITIVE_FORMS_BY_DIFFICULTY["medium"]}
        difficult_forms = {f.lower() for f in COGNITIVE_FORMS_BY_DIFFICULTY["difficult"]}
        if form in medium_forms or form in difficult_forms:
            return False
    if _EASY_UNSAFE_OBJECTIVE_RE.search(objective) or _EASY_UNSAFE_OBJECTIVE_RE.search(
        probe
    ):
        return False
    return bool(objective or concept)


def classify_intent_vs_difficulty(
    intent: Optional[Dict[str, Any]],
    difficulty: str,
) -> str:
    """ok | over-demand | under-demand. Easy over-demand reuses intent_is_easy_safe."""
    if not isinstance(intent, dict):
        return "ok"
    diff = normalize_difficulty(difficulty)
    form = str(intent.get("cognitive_form") or "").strip().lower()
    easy_forms = {f.lower() for f in COGNITIVE_FORMS_BY_DIFFICULTY["easy"]}
    if diff == "easy":
        return "ok" if intent_is_easy_safe(intent) else "over-demand"
    if form in easy_forms and form.startswith("recall"):
        return "under-demand"
    objective = str(intent.get("objective") or "").lower()
    if form in easy_forms and re.search(r"\b(recall|recognize|identify)\b", form):
        if re.search(r"\b(recall|recognize|name|define)\b", objective) and not re.search(
            r"\b(apply|interpret|analy|evaluat|integrat|multi)\b", objective
        ):
            if diff in {"medium", "difficult"}:
                return "under-demand"
    return "ok"


_MEDIUM_DEMAND_CRITERIA = (
    "reasoning",
    "application",
    "interpretation",
    "decision_making",
)


def _medium_meaningful_demand_dimensions(scores: Dict[str, int]) -> int:
    return sum(1 for k in _MEDIUM_DEMAND_CRITERIA if int(scores.get(k) or 1) >= 2)


def _stem_has_interpretive_medium_demand(stem: str) -> bool:
    """True when the stem requires interpretation/comparison beyond bare calculation."""
    low = (stem or "").lower()
    patterns = (
        r"\bwhich (?:envelopes|statements|incidents|split|allocation|combination)",
        r"\b(most (?:likely|suitable|appropriate|closely))",
        r"\b(prioriti[sz]|depleted|eligible for a claim)",
        r"\b(compare|contrast|difference between|differ from|relationship between)",
        r"\b(rent-free|pay-yourself-first|50/30/20|envelope|assessment year|financial year)",
        r"\b(has|have).{0,50}(prioriti|funded before|needs over wants)",
    )
    return any(re.search(p, low) for p in patterns)


def _stem_is_arithmetic_only_medium(stem: str) -> bool:
    """Direct formula or repeated-calculation patterns without interpretive demand."""
    low = (stem or "").lower()
    if _stem_has_interpretive_medium_demand(stem):
        return False
    patterns = (
        r"what (?:is|was) (?:the )?(?:capital gain|total capital gain)",
        r"how much (?:capital gain|interest|did .{0,40}(?:earn|receive|make))",
        r"(?:capital gain|annual interest|interest earned).*(?:from this|from the sale|after one year)",
        r"fixed deposit.{0,120}fixed deposit",
        r"dividend of .* per share.*(?:at least|which of the following share holdings)",
        r"which statement is correct about the annual interest",
    )
    return any(re.search(p, low) for p in patterns)


def classify_medium_generated_demand(
    *,
    scores: Dict[str, int],
    question: Dict[str, Any],
    assigned_intent: Optional[Dict[str, Any]] = None,
) -> str:
    """
    ok | under-demand for target Medium when the summed score band is already Medium.

    Does not change the 13–18 score mapping; rejects thin recall/arithmetic items
    that reached Medium via context/distractor inflation.
    """
    if isinstance(assigned_intent, dict):
        if classify_intent_vs_difficulty(assigned_intent, "medium") == "under-demand":
            return "under-demand"

    stem = str((question or {}).get("question") or "")
    meaningful = _medium_meaningful_demand_dimensions(scores)

    if len(stem) > 320 and meaningful < 2:
        return "under-demand"
    if len(re.findall(r"\d", stem)) >= 10 and meaningful < 2:
        return "under-demand"

    if meaningful < 2:
        return "under-demand"

    if _stem_is_arithmetic_only_medium(stem):
        return "under-demand"

    form = str((assigned_intent or {}).get("cognitive_form") or "").strip().lower()
    easy_forms = {f.lower() for f in COGNITIVE_FORMS_BY_DIFFICULTY["easy"]}
    if form in easy_forms and form.startswith("recall"):
        return "under-demand"

    return "ok"


def _record_objective_form_key(record: Dict[str, Any]) -> Tuple[str, str]:
    """Normalized (objective fingerprint, cognitive form) for variety scoring."""
    objective = str(record.get("assigned_objective") or record.get("objective") or "")
    obj_fp = planned_intent_fingerprint({"objective": objective}) if objective else ""
    form = str(
        record.get("assigned_cognitive_form")
        or record.get("cognitive_form")
        or question_task_form(record.get("question") or "")
    ).strip().lower()
    return obj_fp, form


def intent_objective_form_usage_count(
    intent: Optional[Dict[str, Any]],
    usage_questions: Optional[Sequence[Dict[str, Any]]],
) -> int:
    """How often this intent's objective+cognitive_form pair appears in usage."""
    if not isinstance(intent, dict):
        return 0
    left_obj, left_form = _record_objective_form_key(
        {
            "objective": intent.get("objective"),
            "assigned_objective": intent.get("objective"),
            "cognitive_form": intent.get("cognitive_form"),
            "assigned_cognitive_form": intent.get("cognitive_form"),
        }
    )
    if not left_obj and not left_form:
        return 0
    n = 0
    for q in usage_questions or []:
        if not isinstance(q, dict):
            continue
        if not intents_share_objective(intent, q):
            continue
        right_obj, right_form = _record_objective_form_key(q)
        if left_form and right_form and left_form == right_form:
            n += 1
        elif left_obj and right_obj and left_obj == right_obj:
            n += 1
    return n


def intent_selection_usage_key(
    intent: Dict[str, Any],
    usage_questions: Optional[Sequence[Dict[str, Any]]],
) -> Tuple[int, int, int]:
    """Sort key: prefer lower concept usage, then objective+form, then objective-only."""
    concept = intent_concept_usage_count(intent, usage_questions)
    obj_form = intent_objective_form_usage_count(intent, usage_questions)
    objective_only = sum(
        1
        for q in (usage_questions or [])
        if isinstance(q, dict) and intents_share_objective(intent, q)
    )
    return concept, obj_form, objective_only


def _record_easy_intent_skip(diagnostics: Optional[Dict[str, Any]]) -> None:
    if diagnostics is None:
        return
    diagnostics["easy_intents_skipped_unsafe"] = int(
        diagnostics.get("easy_intents_skipped_unsafe") or 0
    ) + 1


def filter_easy_safe_intents(
    intents: Sequence[Dict[str, Any]],
    *,
    difficulty: str,
    diagnostics: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Drop Medium-style intents from an Easy catalog. No-op for other difficulties."""
    if normalize_difficulty(difficulty) != "easy":
        return [dict(x) for x in (intents or [])]
    kept: List[Dict[str, Any]] = []
    for intent in intents or []:
        if intent_is_easy_safe(intent):
            kept.append(dict(intent))
        else:
            _record_easy_intent_skip(diagnostics)
    return kept


def ensure_easy_safe_assigned_intent(
    active_intent: Optional[Dict[str, Any]],
    remaining: List[Dict[str, Any]],
    *,
    target_difficulty: str,
    retired_ids: Optional[set] = None,
    assigned_values: Optional[Sequence[Dict[str, Any]]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    assignments: Optional[Dict[str, Dict[str, Any]]] = None,
    slot_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Bank Batch Easy only: if the assigned intent is Medium-style, skip it and
    pick another grounded Easy-safe intent. Does not run for Medium/Difficult.
    """
    if normalize_difficulty(target_difficulty) != "easy":
        return active_intent
    current = active_intent
    while current and not intent_is_easy_safe(current):
        _record_easy_intent_skip(diagnostics)
        current = take_next_unused_intent(
            remaining,
            retired_ids=retired_ids,
            assigned_values=assigned_values,
            target_difficulty="easy",
            diagnostics=diagnostics,
        )
    if assignments is not None and slot_key:
        if current:
            assignments[slot_key] = current
        else:
            assignments.pop(slot_key, None)
    return current


class IntentDraft(BaseModel):
    """LLM output item — no full MCQ."""

    topic: str
    sub_topic: str = ""
    concept: str
    objective: str
    cognitive_form: str
    source_section: str = ""
    chunk_index: int = 0


class IntentCatalogLLMOutput(BaseModel):
    intents: List[IntentDraft] = Field(default_factory=list)


def is_bank_intent_planner_enabled() -> bool:
    """Bank Batch intent planner. Default ON; set QUESTION_BANK_INTENT_PLANNER=0 to disable."""
    raw = (os.environ.get("QUESTION_BANK_INTENT_PLANNER") or "").strip().lower()
    if not raw:
        return True
    return raw not in {"0", "false", "no", "off"}


def empty_intent_diagnostics() -> Dict[str, Any]:
    return {
        "planner_version": INTENT_PLANNER_VERSION,
        "enabled": False,
        "cache_hit": False,
        "catalog_size": 0,
        "grounded_intents": 0,
        "ungrounded_discarded": 0,
        "bank_intents_derived": 0,
        "intents_filtered_already_in_bank": 0,
        "intents_assigned": 0,
        "intents_retired_after_duplicate": 0,
        "catalog_exhaustion_count": 0,
        "questions_accepted_from_assigned_intent": 0,
        "adherence_strong": 0,
        "adherence_partial": 0,
        "adherence_drifted": 0,
        "adherence_partial_continued": 0,
        "drift_early_exits": 0,
        "initial_cached_catalog_size": 0,
        "cache_expansion_count": 0,
        "replenishment_rounds": 0,
        "planner_calls": 0,
        "intents_requested_per_replenish": 0,
        "raw_intents_returned": 0,
        "grounded_new_intents": 0,
        "duplicate_intents_removed": 0,
        "per_chunk_intent_counts": {},
        "unused_intents_before_replenish": 0,
        "unused_intents_after_replenish": 0,
        "novelty_briefs_created": 0,
        "novelty_avoid_stems_included": 0,
        "duplicate_retry_same_intent": 0,
        "duplicate_retry_changed_question_form": 0,
        "intents_retired_after_repeated_duplicates": 0,
        "variety_low_novelty_retries": 0,
        "easy_intents_skipped_unsafe": 0,
        "target_catalog_size": 0,
        "content_hash": "",
        "cache_key": "",
        # Yield optimization diagnostics (validators unchanged)
        "intents_retired_after_academic_failure": 0,
        "academic_failure_family_retries": 0,
        "saturation_influenced_selections": 0,
        "academic_failure_events": [],
    }


def chapter_content_hash(chapter_text: str) -> str:
    return hashlib.sha256((chapter_text or "").encode("utf-8")).hexdigest()[:24]


def intent_cache_key(
    *,
    book_id: str,
    chapter: int,
    difficulty: str,
    content_hash: str,
    planner_version: str = INTENT_PLANNER_VERSION,
) -> str:
    raw = (
        f"{book_id}|{int(chapter)}|{normalize_difficulty(difficulty)}|"
        f"{content_hash}|{planner_version}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _cache_dir() -> Path:
    path = Path(DATA_FOLDER) / "intent-catalog-cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(cache_key: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", cache_key)[:64]
    return _cache_dir() / f"{safe}.json"


def _normalize_catalog_status(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {
        INTENT_CATALOG_STATUS_COMPLETE,
        INTENT_CATALOG_STATUS_FAILED,
        INTENT_CATALOG_STATUS_PARTIAL,
    }:
        return raw
    return ""


def intent_catalog_record_status(record: Optional[Dict[str, Any]]) -> str:
    """Resolve cache status; empty legacy files are failed (not reusable)."""
    if not isinstance(record, dict):
        return INTENT_CATALOG_STATUS_FAILED
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    explicit = _normalize_catalog_status(meta.get("status"))
    if explicit:
        return explicit
    intents = record.get("intents") or []
    if isinstance(intents, list) and any(isinstance(x, dict) for x in intents):
        return INTENT_CATALOG_STATUS_COMPLETE
    return INTENT_CATALOG_STATUS_FAILED


def is_reusable_intent_catalog_record(record: Optional[Dict[str, Any]]) -> bool:
    """Reuse only a successfully completed catalog with at least one grounded intent."""
    if not isinstance(record, dict):
        return False
    if intent_catalog_record_status(record) != INTENT_CATALOG_STATUS_COMPLETE:
        return False
    intents = record.get("intents") or []
    grounded = [x for x in intents if isinstance(x, dict)]
    if not grounded:
        return False
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    if int(meta.get("grounded_count") or len(grounded) or 0) <= 0:
        return False
    return True


def load_cached_intent_catalog(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    record = load_intent_catalog_record(cache_key)
    if not is_reusable_intent_catalog_record(record):
        return None
    return [dict(x) for x in (record.get("intents") or []) if isinstance(x, dict)]


def load_intent_catalog_record(cache_key: str) -> Optional[Dict[str, Any]]:
    """Load expandable catalog record (intents + meta)."""
    path = _cache_file(cache_key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("planner_version") != INTENT_PLANNER_VERSION:
            return None
        if data.get("cache_key") != cache_key:
            return None
        intents = data.get("intents")
        if not isinstance(intents, list):
            return None
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        return {
            "intents": [dict(x) for x in intents if isinstance(x, dict)],
            "meta": dict(meta),
        }
    except Exception as e:
        logger.warning(f"Intent catalog cache read failed: {e}")
        return None


def chunk_intent_counts(
    catalog: Sequence[Dict[str, Any]],
    *,
    n_chunks: Optional[int] = None,
) -> Dict[int, int]:
    """Count catalog intents per chunk_index."""
    counts: Dict[int, int] = {}
    if n_chunks:
        for i in range(int(n_chunks)):
            counts[i] = 0
    for intent in catalog or []:
        if not isinstance(intent, dict):
            continue
        try:
            idx = int(intent.get("chunk_index") if intent.get("chunk_index") is not None else 0)
        except (TypeError, ValueError):
            idx = 0
        counts[idx] = int(counts.get(idx) or 0) + 1
    return counts


def save_cached_intent_catalog(
    cache_key: str,
    intents: Sequence[Dict[str, Any]],
    *,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    catalog = list(intents)
    counts = chunk_intent_counts(catalog)
    merged_meta = dict(meta or {})
    merged_meta.setdefault("catalog_version", INTENT_CATALOG_SCHEMA_VERSION)
    merged_meta["total_catalog_intents"] = len(catalog)
    merged_meta["grounded_count"] = len(catalog)
    merged_meta["chunks_covered"] = sorted(i for i, n in counts.items() if n > 0)
    merged_meta["sections_covered"] = sorted(
        {
            str(x.get("source_section") or "").strip()
            for x in catalog
            if str(x.get("source_section") or "").strip()
        }
    )
    merged_meta.setdefault("planner_calls_used", 0)
    status = _normalize_catalog_status(merged_meta.get("status"))
    if not status:
        status = (
            INTENT_CATALOG_STATUS_COMPLETE
            if catalog
            else INTENT_CATALOG_STATUS_FAILED
        )
    if status == INTENT_CATALOG_STATUS_COMPLETE and not catalog:
        status = INTENT_CATALOG_STATUS_FAILED
    merged_meta["status"] = status
    payload = {
        "planner_version": INTENT_PLANNER_VERSION,
        "cache_key": cache_key,
        "intents": catalog,
        "meta": merged_meta,
    }
    path = _cache_file(cache_key)
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Intent catalog cache write failed: {e}")


def planned_intent_fingerprint(intent: Dict[str, Any]) -> str:
    """Fingerprint of planned objective (not a full question stem)."""
    parts = [
        str(intent.get("cognitive_form") or ""),
        str(intent.get("concept") or ""),
        str(intent.get("objective") or ""),
    ]
    return intent_fingerprint(" ".join(parts))


def planned_intent_words(intent: Dict[str, Any]) -> set:
    """Content words for objective comparison (exclude shared cognitive_form noise)."""
    return _extract_intent_words(
        f"{intent.get('concept') or ''} {intent.get('objective') or ''}"
    )


def question_used_intent_words(question: Dict[str, Any]) -> set:
    words = _extract_intent_words(question.get("question") or "")
    words |= _extract_intent_words(question.get("objective") or "")
    words |= _extract_intent_words(question.get("concept") or "")
    fp = (question.get("intent_fingerprint") or question.get("matched_intent_fingerprint") or "").strip()
    if fp:
        words |= set(fp.split())
    return words


def _bank_intent_cache_dir() -> Path:
    path = Path(DATA_FOLDER) / "intent-bank-derived-cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _bank_intent_cache_key(question: Dict[str, Any]) -> str:
    qid = str(question.get("id") or "").strip()
    stem = str(question.get("question") or "").strip()
    raw = f"{qid}|{stem}|{INTENT_PLANNER_VERSION}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _load_cached_bank_intent(cache_key: str) -> Optional[Dict[str, Any]]:
    path = _bank_intent_cache_dir() / f"{cache_key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("planner_version") != INTENT_PLANNER_VERSION:
            return None
        intent = data.get("intent")
        return dict(intent) if isinstance(intent, dict) else None
    except Exception:
        return None


def _save_cached_bank_intent(cache_key: str, intent: Dict[str, Any]) -> None:
    path = _bank_intent_cache_dir() / f"{cache_key}.json"
    try:
        path.write_text(
            json.dumps(
                {"planner_version": INTENT_PLANNER_VERSION, "intent": intent},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"Bank intent cache write failed: {e}")


def _strip_trailing_question_clause(text: str) -> str:
    t = (text or "").strip().rstrip("?.!").strip()
    # Drop leading "which of the following ..." wrappers when capturing focus noun
    t = re.sub(
        r"^(?:which of the following|select all(?: of the following)?|"
        r"identify(?: which)?|choose the best)\s+",
        "",
        t,
        flags=re.I,
    ).strip()
    return t


def _cognitive_form_from_task(task: str, difficulty: str = "easy") -> str:
    diff = normalize_difficulty(difficulty)
    forms = COGNITIVE_FORMS_BY_DIFFICULTY.get(diff) or COGNITIVE_FORMS_BY_DIFFICULTY["easy"]
    task = (task or "").lower()
    mapping = {
        "define": "recall a taught fact",
        "recall": "recall a taught fact",
        "identify": "identify a concept",
        "example": "recognize an example/non-example",
        "distinguish": (
            "identify a concept"
            if diff == "easy"
            else "distinguish two taught concepts"
        ),
        "apply": "direct one-step application",
        "explain": "identify a concept",
    }
    preferred = mapping.get(task, forms[0])
    return preferred if preferred in forms else forms[0]


def _objective_from_stem(stem: str, concept: str) -> Tuple[str, str]:
    """
    Deterministic objective + task-family from a bank stem.
    Returns (objective, task_family).
    """
    s = (stem or "").strip()
    low = s.lower()
    concept = (concept or "").strip()

    m = re.search(
        r"difference between\s+(.+?)\s+and\s+(.+?)(?:\?|$)",
        s,
        flags=re.I,
    )
    if m:
        a, b = m.group(1).strip(), m.group(2).strip()
        return f"Distinguish between {a} and {b}", "distinguish"

    if re.search(r"\b(distinguish|contrast|versus|\bvs\b)\b", low):
        focus = concept or "the two taught concepts"
        return f"Distinguish {focus}", "distinguish"

    m = re.search(r"what does\s+(.+?)\s+mean\b", s, flags=re.I)
    if m:
        focus = _strip_trailing_question_clause(m.group(1))
        return f"Define {focus}", "define"

    m = re.search(
        r"(?:what is the meaning of|definition of)\s+(.+?)(?:\?|$)",
        s,
        flags=re.I,
    )
    if m:
        focus = _strip_trailing_question_clause(m.group(1))
        return f"Define {focus}", "define"

    m = re.search(r"^what is\s+(?:the\s+)?(.+?)(?:\?|$)", s, flags=re.I)
    if m and not re.search(r"\b(example|reason|function|advantage)\b", low):
        focus = _strip_trailing_question_clause(m.group(1))
        # Avoid "What is the main reason..." as define
        if not re.match(r"^(main|primary|best|most)\b", focus, flags=re.I):
            return f"Define {focus}", "define"

    m = re.search(
        r"(?:example of|examples of)\s+(.+?)(?:\?|$)",
        s,
        flags=re.I,
    )
    if m:
        focus = _strip_trailing_question_clause(m.group(1))
        return f"Recognize an example of {focus}", "example"

    if "which of the following are" in low or "select all" in low:
        focus = concept or "the taught concept"
        return f"Identify correct aspects of {focus}", "identify"

    if re.search(r"\bwhy\b", low):
        focus = concept or "the taught concept"
        return f"Identify why {focus} matters or was used", "identify"

    if re.search(r"\b(function|functions) of\b", low):
        focus = concept or "money"
        return f"Identify the functions of {focus}", "identify"

    if concept:
        # Compact stem-derived objective using concept + task cue from stem words
        fam = _task_family(_extract_intent_words(s))
        if fam == "define":
            return f"Define {concept}", "define"
        if fam == "example":
            return f"Recognize an example of {concept}", "example"
        if fam == "distinguish":
            return f"Distinguish {concept} from a related concept", "distinguish"
        if fam == "apply":
            return f"Apply {concept} in a simple case", "apply"
        return f"Identify a key fact about {concept}", "identify"

    # Last resort: compress stem into objective-like phrase (not wording change of bank Q)
    compact = _strip_trailing_question_clause(s)
    if len(compact) > 120:
        compact = compact[:117] + "..."
    return f"Test: {compact}", "identify"


_GENERIC_SUBTOPIC_LABELS = {
    "definition",
    "definitions",
    "meaning",
    "overview",
    "introduction",
    "general",
    "basics",
    "concept",
}


def _preferred_bank_concept(question: Dict[str, Any]) -> str:
    existing = str(question.get("concept") or "").strip()
    if existing:
        return existing
    sub = str(question.get("sub_topic") or "").strip()
    topic = str(question.get("topic") or "").strip()
    if sub and sub.lower() not in _GENERIC_SUBTOPIC_LABELS:
        return sub
    return topic or sub


def derive_intent_from_bank_question(
    question: Dict[str, Any],
    *,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Derive compact intent metadata for an existing bank question.

    Does not modify historical question wording. Prefer deterministic derivation.
    Uses the same normalize_intent_dict / fingerprint as planner intents.
    """
    q = dict(question or {})
    existing_obj = str(q.get("objective") or "").strip()
    existing_concept = str(q.get("concept") or "").strip()
    existing_fp = str(q.get("intent_fingerprint") or "").strip()
    if existing_obj and existing_concept and existing_fp:
        return normalize_intent_dict(
            {
                "intent_id": q.get("intent_id") or f"bank-{q.get('id') or 'seed'}",
                "topic": q.get("topic") or "",
                "sub_topic": q.get("sub_topic") or "",
                "concept": existing_concept,
                "objective": existing_obj,
                "cognitive_form": q.get("cognitive_form") or "",
                "intent_fingerprint": existing_fp,
                "chunk_index": q.get("source_chunk_index") or 0,
            }
        )

    cache_key = _bank_intent_cache_key(q) if use_cache else ""
    if use_cache and cache_key:
        cached = _load_cached_bank_intent(cache_key)
        if cached:
            return cached

    topic = str(q.get("topic") or "").strip()
    sub_topic = str(q.get("sub_topic") or "").strip()
    concept = _preferred_bank_concept(q)
    stem = str(q.get("question") or "").strip()
    objective, task = _objective_from_stem(stem, concept)
    if existing_obj:
        objective = existing_obj
    cognitive_form = str(q.get("cognitive_form") or "").strip() or _cognitive_form_from_task(
        task, str(q.get("target_difficulty") or q.get("difficulty") or "easy")
    )
    derived = normalize_intent_dict(
        {
            "intent_id": f"bank-{q.get('id') or uuid.uuid4().hex[:8]}",
            "topic": topic,
            "sub_topic": sub_topic,
            "concept": concept,
            "objective": objective,
            "cognitive_form": cognitive_form,
            "source_section": sub_topic or topic,
            "chunk_index": q.get("source_chunk_index") or 0,
        }
    )
    derived["_intent_derived"] = True
    if use_cache and cache_key:
        _save_cached_bank_intent(cache_key, derived)
    return derived


def enrich_bank_questions_with_intents(
    questions: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Return copies of bank questions with concept/objective/fingerprint filled for filtering.
    Does not alter stored historical wording fields beyond adding intent metadata keys.
    """
    out: List[Dict[str, Any]] = []
    derived_n = 0
    for q in questions or []:
        if not isinstance(q, dict):
            continue
        row = dict(q)
        had_full = bool(
            str(row.get("objective") or "").strip()
            and str(row.get("concept") or "").strip()
            and str(row.get("intent_fingerprint") or "").strip()
        )
        intent = derive_intent_from_bank_question(row)
        row["concept"] = intent.get("concept") or row.get("concept") or ""
        row["objective"] = intent.get("objective") or row.get("objective") or ""
        row["cognitive_form"] = intent.get("cognitive_form") or row.get("cognitive_form") or ""
        row["intent_fingerprint"] = (
            intent.get("intent_fingerprint") or row.get("intent_fingerprint") or ""
        )
        if not had_full:
            derived_n += 1
        out.append(row)
    return out, derived_n


_DEFINITION_TASK_WORDS = {
    "define",
    "defin",
    "definition",
    "mean",
    "meaning",
    "means",
    "what",
    "identify",  # only when paired with definitional framing — handled below
}
_DISTINGUISH_TASK_WORDS = {
    "distinguish",
    "differ",
    "difference",
    "contrast",
    "versus",
    "vs",
    "between",
    "compare",
}


def _task_family(words: set) -> str:
    if words & _DISTINGUISH_TASK_WORDS:
        return "distinguish"
    if words & {"define", "defin", "definition", "mean", "meaning", "means"}:
        return "define"
    if words & {"example", "non", "nonexample", "recognize"}:
        return "example"
    if words & {"apply", "application", "calculate", "use"}:
        return "apply"
    if words & {"recall", "remember", "fact"}:
        return "recall"
    return ""


def intents_share_objective(
    left: Dict[str, Any],
    right_words_or_intent: Any,
    *,
    threshold: float = INTENT_OBJECTIVE_OVERLAP_THRESHOLD,
) -> bool:
    """
    True when two intents test substantially the same objective.

    Same topic/concept alone is NOT enough. Objective text drives the decision;
    definitional paraphrases of the same concept count as the same intent.
    """
    if not isinstance(left, dict):
        return False

    left_obj = _extract_intent_words(
        left.get("objective") or left.get("assigned_objective") or ""
    )
    left_concept = _extract_intent_words(
        left.get("concept") or left.get("assigned_concept") or ""
    )
    left_all = planned_intent_words(left) or question_used_intent_words(left)

    if isinstance(right_words_or_intent, dict):
        right = right_words_or_intent
        right_obj = _extract_intent_words(
            right.get("objective") or right.get("assigned_objective") or ""
        )
        if not right_obj:
            # Question-shaped records without derived objective: stem as proxy
            right_obj = _extract_intent_words(right.get("question") or "")
        right_concept = _extract_intent_words(
            right.get("concept") or right.get("assigned_concept") or ""
        )
        if not right_concept:
            right_concept = _extract_intent_words(
                f"{right.get('sub_topic') or ''} {right.get('topic') or ''}"
            )
        right_all = planned_intent_words(right) or question_used_intent_words(right)
    else:
        right_obj = set(right_words_or_intent or set())
        right_concept = set()
        right_all = set(right_words_or_intent or set())

    if not left_obj and not left_all:
        return False
    if not right_obj and not right_all:
        return False

    # 1) Direct objective overlap (preferred)
    probe_l = left_obj or left_all
    probe_r = right_obj or right_all
    obj_overlap = _semantic_intent_overlap(probe_l, probe_r)
    if obj_overlap >= threshold:
        # Guard: shared concept noun alone with different task families ≠ same intent
        fam_l = _task_family(probe_l)
        fam_r = _task_family(probe_r)
        if fam_l and fam_r and fam_l != fam_r:
            return False
        return True

    # 2) Definitional paraphrase of the same concept
    fam_l = _task_family(probe_l)
    fam_r = _task_family(probe_r)
    if fam_l and fam_l == fam_r == "define":
        concepts = left_concept | _extract_intent_words(left.get("topic") or "")
        other_concepts = right_concept
        if not other_concepts:
            other_concepts = probe_r - _DEFINITION_TASK_WORDS - {"taught", "fact", "concept"}
        if concepts and other_concepts and (concepts & other_concepts):
            return True

    # 3) Fallback: full planned fingerprint overlap, still respecting task-family guard
    full_overlap = _semantic_intent_overlap(left_all, right_all)
    if full_overlap >= threshold:
        if fam_l and fam_r and fam_l != fam_r:
            return False
        # Require more than a single shared topic/concept token
        shared = left_all & right_all
        if len(shared) <= 1 and (left_concept & right_all or right_concept & left_all):
            return False
        return True
    return False


def normalize_intent_dict(raw: Dict[str, Any], *, index: int = 0) -> Dict[str, Any]:
    topic = str(raw.get("topic") or "").strip()
    concept = str(raw.get("concept") or "").strip() or topic
    objective = str(raw.get("objective") or "").strip()
    cognitive_form = str(raw.get("cognitive_form") or "").strip().lower()
    sub_topic = str(raw.get("sub_topic") or "").strip()
    source_section = str(raw.get("source_section") or "").strip()
    try:
        chunk_index = int(raw.get("chunk_index") if raw.get("chunk_index") is not None else 0)
    except (TypeError, ValueError):
        chunk_index = 0
    intent_id = str(raw.get("intent_id") or "").strip() or f"intent-{index+1}-{uuid.uuid4().hex[:8]}"
    out = {
        "intent_id": intent_id,
        "topic": topic,
        "sub_topic": sub_topic,
        "concept": concept,
        "objective": objective,
        "cognitive_form": cognitive_form,
        "source_section": source_section,
        "chunk_index": chunk_index,
    }
    out["intent_fingerprint"] = (
        str(raw.get("intent_fingerprint") or "").strip() or planned_intent_fingerprint(out)
    )
    return out


def ground_intent(
    intent: Dict[str, Any],
    chunks: Sequence[str],
) -> Optional[Dict[str, Any]]:
    """
    Require a valid chunk_index and that concept/objective are supported by that chunk.
    Returns a grounded copy or None if ungrounded/hallucinated.
    """
    if not chunks:
        return None
    try:
        idx = int(intent.get("chunk_index"))
    except (TypeError, ValueError):
        return None
    if idx < 0 or idx >= len(chunks):
        return None
    chunk = chunks[idx] or ""
    chunk_words = _extract_intent_words(chunk)
    if not chunk_words:
        return None

    concept = (intent.get("concept") or "").strip()
    objective = (intent.get("objective") or "").strip()
    if not concept and not objective:
        return None

    concept_words = _extract_intent_words(concept)
    objective_words = _extract_intent_words(objective)
    probe = concept_words | objective_words
    if not probe:
        return None

    overlap = len(probe & chunk_words) / max(len(probe), 1)
    # Also accept if a short concept phrase appears literally (case-insensitive)
    literal_ok = False
    low_chunk = chunk.lower()
    if concept and len(concept) >= 3 and concept.lower() in low_chunk:
        literal_ok = True
    if not literal_ok and overlap < INTENT_GROUNDING_OVERLAP_THRESHOLD:
        # Try remapping to a better chunk that supports the concept
        best_i = None
        best_score = 0.0
        for i, ch in enumerate(chunks):
            cw = _extract_intent_words(ch)
            if not cw:
                continue
            score = len(probe & cw) / max(len(probe), 1)
            if concept and concept.lower() in (ch or "").lower():
                score = max(score, 0.9)
            if score > best_score:
                best_score = score
                best_i = i
        if best_i is None or best_score < INTENT_GROUNDING_OVERLAP_THRESHOLD:
            return None
        idx = best_i
        chunk = chunks[idx]

    grounded = dict(intent)
    grounded["chunk_index"] = idx
    if not grounded.get("source_section"):
        # Prefer first non-empty line-ish heading hint from chunk
        for line in (chunk or "").splitlines()[:8]:
            s = line.strip().lstrip("#").strip()
            if 3 <= len(s) <= 80:
                grounded["source_section"] = s[:80]
                break
    grounded["intent_fingerprint"] = planned_intent_fingerprint(grounded)
    return grounded


def ground_intent_catalog(
    raw_intents: Sequence[Dict[str, Any]],
    chunks: Sequence[str],
) -> Tuple[List[Dict[str, Any]], int]:
    grounded: List[Dict[str, Any]] = []
    discarded = 0
    seen_fps: set = set()
    for i, raw in enumerate(raw_intents or []):
        if not isinstance(raw, dict):
            discarded += 1
            continue
        norm = normalize_intent_dict(raw, index=i)
        g = ground_intent(norm, chunks)
        if not g:
            discarded += 1
            continue
        fp = g.get("intent_fingerprint") or ""
        # Dedup near-identical planned objectives inside the catalog itself
        if fp and any(
            intents_share_objective(g, existing) for existing in grounded
        ):
            discarded += 1
            continue
        if fp:
            seen_fps.add(fp)
        grounded.append(g)
    return grounded, discarded


def filter_intents_against_used(
    catalog: Sequence[Dict[str, Any]],
    *,
    bank_questions: Sequence[Dict[str, Any]] = (),
    assigned_intents: Sequence[Dict[str, Any]] = (),
    accepted_questions: Sequence[Dict[str, Any]] = (),
    rejected_attempts: Sequence[Dict[str, Any]] = (),
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Remove intents whose objective is already represented in bank / batch / history.

    Compares mainly concept + objective (same normalization as planner intents).
    Same topic alone does NOT filter.
    """
    used_intents: List[Dict[str, Any]] = []
    enriched_bank, _ = enrich_bank_questions_with_intents(bank_questions)
    used_intents.extend(enriched_bank)
    for q in accepted_questions or []:
        if isinstance(q, dict):
            enriched, _ = enrich_bank_questions_with_intents([q])
            used_intents.extend(enriched)
    for intent in assigned_intents or []:
        if isinstance(intent, dict):
            used_intents.append(normalize_intent_dict(intent))
    for r in rejected_attempts or []:
        if not isinstance(r, dict):
            continue
        enriched, _ = enrich_bank_questions_with_intents([r])
        used_intents.extend(enriched)
        mfp = (r.get("matched_intent_fingerprint") or "").strip()
        if mfp:
            used_intents.append(
                {
                    "concept": r.get("matched_topic") or r.get("topic") or "",
                    "objective": " ".join(mfp.split()),
                    "intent_fingerprint": mfp,
                }
            )

    available: List[Dict[str, Any]] = []
    filtered = 0
    for intent in catalog or []:
        hit = False
        for used in used_intents:
            if intents_share_objective(intent, used):
                hit = True
                break
        if hit:
            filtered += 1
            continue
        # Also avoid assigning two near-identical remaining intents
        if any(intents_share_objective(intent, a) for a in available):
            filtered += 1
            continue
        available.append(dict(intent))
    return available, filtered


def assign_intents_to_slots(
    slots: Sequence[Any],
    available: Sequence[Dict[str, Any]],
    *,
    usage_questions: Optional[Sequence[Dict[str, Any]]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]], int]:
    """
    Assign one unused intent per slot (by question_number key as str).
    When usage_questions is provided, pool is ordered to prefer underrepresented
    concepts first (never drops a valid intent).
    Returns (assignments, remaining, assigned_count).
    """
    del diagnostics  # reserved for future assignment diagnostics
    pool = [dict(x) for x in available]
    if usage_questions is not None:
        pool = sort_intents_prefer_underrepresented(pool, usage_questions)
    assignments: Dict[str, Dict[str, Any]] = {}
    assigned = 0
    for slot in slots or []:
        if isinstance(slot, dict):
            qn = slot.get("question_number")
        else:
            qn = getattr(slot, "question_number", None)
        if qn is None:
            continue
        key = str(int(qn))
        if not pool:
            break
        intent = pool.pop(0)
        assignments[key] = intent
        assigned += 1
    return assignments, pool, assigned


def intent_concept_usage_count(
    intent: Optional[Dict[str, Any]],
    usage_questions: Optional[Sequence[Dict[str, Any]]],
) -> int:
    """How often this intent's concept/topic already appears in bank + batch usage."""
    if not isinstance(intent, dict):
        return 0
    concept = str(intent.get("concept") or intent.get("topic") or "").strip().lower()
    if not concept:
        return 0
    n = 0
    for q in usage_questions or []:
        if not isinstance(q, dict):
            continue
        labels = (
            str(q.get("assigned_concept") or ""),
            str(q.get("topic") or ""),
            str(q.get("concept") or ""),
        )
        if any(concept and concept == lab.strip().lower() for lab in labels if lab):
            n += 1
            continue
        if any(concept and concept in lab.strip().lower() for lab in labels if lab):
            n += 1
    return n


def sort_intents_prefer_underrepresented(
    intents: Sequence[Dict[str, Any]],
    usage_questions: Optional[Sequence[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Stable sort: lower concept/objective-form usage first. Does not drop any intent."""
    indexed = list(enumerate(dict(x) for x in intents))
    indexed.sort(
        key=lambda pair: (
            *intent_selection_usage_key(pair[1], usage_questions),
            pair[0],
        )
    )
    return [item for _, item in indexed]


def take_next_unused_intent(
    remaining: List[Dict[str, Any]],
    *,
    retired_ids: Optional[set] = None,
    assigned_values: Optional[Sequence[Dict[str, Any]]] = None,
    target_difficulty: Optional[str] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    usage_questions: Optional[Sequence[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Pop next eligible intent from the remaining pool (mutates remaining).

    When usage_questions is provided, prefers underrepresented concepts among
    currently eligible candidates. Never permanently excludes a valid concept
    solely for being represented — only skip if retired, objective-colliding,
    or Easy-unsafe.
    """
    retired_ids = retired_ids or set()
    assigned_values = list(assigned_values or [])
    easy_guard = normalize_difficulty(target_difficulty or "") == "easy"

    def _eligible(candidate: Dict[str, Any]) -> Optional[str]:
        """Return None if eligible, else skip reason: retired|objective|easy_unsafe."""
        cid = str(candidate.get("intent_id") or "")
        if cid and cid in retired_ids:
            return "retired"
        if any(intents_share_objective(candidate, a) for a in assigned_values):
            return "objective"
        if easy_guard and not intent_is_easy_safe(candidate):
            return "easy_unsafe"
        return None

    # Legacy path: sequential pop (preserves prior behavior).
    if usage_questions is None:
        while remaining:
            candidate = remaining.pop(0)
            skip = _eligible(candidate)
            if skip == "easy_unsafe":
                _record_easy_intent_skip(diagnostics)
                continue
            if skip:
                continue
            return candidate
        return None

    # Saturation-aware: choose least-used among currently eligible; leave
    # ineligible (objective collision) in the pool for later slots.
    eligible_indices: List[int] = []
    remove_indices: List[int] = []
    for i, candidate in enumerate(remaining):
        skip = _eligible(candidate)
        if skip in {"retired", "easy_unsafe"}:
            if skip == "easy_unsafe":
                _record_easy_intent_skip(diagnostics)
            remove_indices.append(i)
            continue
        if skip == "objective":
            continue
        eligible_indices.append(i)

    for i in reversed(remove_indices):
        remaining.pop(i)
        # Adjust eligible indices after removals
        eligible_indices = [
            (idx - 1 if idx > i else idx) for idx in eligible_indices if idx != i
        ]

    if not eligible_indices:
        return None

    usage_scores = [
        (*intent_selection_usage_key(remaining[idx], usage_questions), idx)
        for idx in eligible_indices
    ]
    min_key = min(row[:-1] for row in usage_scores)
    chosen_pos = eligible_indices[0]
    saturation_influenced = False
    for key, idx in ((row[:-1], row[-1]) for row in usage_scores):
        if key == min_key:
            chosen_pos = idx
            if idx != eligible_indices[0]:
                saturation_influenced = True
            break

    if saturation_influenced and diagnostics is not None:
        diagnostics["saturation_influenced_selections"] = (
            int(diagnostics.get("saturation_influenced_selections") or 0) + 1
        )
        diagnostics["last_saturation_selection"] = {
            "intent_id": remaining[chosen_pos].get("intent_id"),
            "concept": remaining[chosen_pos].get("concept"),
            "prior_concept_usage_count": intent_concept_usage_count(
                remaining[chosen_pos], usage_questions
            ),
            "saturation_influenced": True,
        }

    return remaining.pop(chosen_pos)

def format_assigned_intent_guidance(intent: Dict[str, Any]) -> str:
    """Prompt block: generator must primarily test this assigned intent."""
    return (
        "\nASSIGNED QUESTION INTENT (Bank Batch — REQUIRED; still obey all quality/"
        "validation rules):\n"
        f"- intent_id: {intent.get('intent_id')}\n"
        f"- topic: {intent.get('topic')}\n"
        f"- sub_topic: {intent.get('sub_topic') or '(derive if needed)'}\n"
        f"- concept: {intent.get('concept')}\n"
        f"- objective: {intent.get('objective')}\n"
        f"- cognitive_form: {intent.get('cognitive_form')}\n"
        f"- source_section: {intent.get('source_section') or '(from chunk)'}\n"
        "You MUST write ONE MCQ that:\n"
        "1) tests the assigned CONCEPT,\n"
        "2) tests the assigned OBJECTIVE (not a different learning task),\n"
        "3) uses the assigned COGNITIVE FORM,\n"
        "4) stays grounded in the provided chapter chunk.\n"
        "Before writing, be able to answer: What concept is this testing? "
        "What should the student know or understand to answer it?\n"
        "Do NOT replace the assigned objective with a simpler familiar definition "
        "question, a different function-of-money stem, or another saturated Easy "
        "pattern unless that IS the assigned objective.\n"
        "Prefer the given topic/sub_topic/concept labels when they fit the chunk.\n"
    )


# ---------------------------------------------------------------------------
# Step 8 — Novelty brief (Bank Batch generation guidance only)
# ---------------------------------------------------------------------------

INTENT_DUPLICATE_HITS_BEFORE_RETIRE = 2
INTENT_FAMILY_HITS_BEFORE_RETIRE = 2

# Academic failure families that can retire an intent after repeated hits.
# Provider/length/structural/duplicate are intentionally excluded.
FAILURE_FAMILY_DISTRACTOR = "distractor"
FAILURE_FAMILY_SUBJECTIVE_BEST = "subjective_best"
FAILURE_FAMILY_COGNITIVE = "cognitive"
FAILURE_FAMILY_GROUNDING = "grounding"
FAILURE_FAMILY_GRADE = "grade"
FAILURE_FAMILY_BLIND_ANSWER = "blind_answer"
ACADEMIC_FAILURE_FAMILIES = (
    FAILURE_FAMILY_DISTRACTOR,
    FAILURE_FAMILY_SUBJECTIVE_BEST,
    FAILURE_FAMILY_COGNITIVE,
    FAILURE_FAMILY_GROUNDING,
    FAILURE_FAMILY_GRADE,
    FAILURE_FAMILY_BLIND_ANSWER,
)


def question_task_form(text: str) -> str:
    """Detect a coarse question-task form from stem/objective text."""
    raw = set(re.sub(r"[^\w\s]", " ", (text or "").lower()).split())
    return _task_family(raw) or ""


def should_retire_intent_after_duplicate_hits(hits: int) -> bool:
    """Retire only after repeated duplicates prove the intent is exhausted."""
    try:
        return int(hits) >= INTENT_DUPLICATE_HITS_BEFORE_RETIRE
    except (TypeError, ValueError):
        return False


def select_closest_bank_stems_for_intent(
    assigned: Dict[str, Any],
    existing_questions: Sequence[Dict[str, Any]],
    *,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Pick a small number of nearest existing bank questions for avoid guidance.

    Ranking uses concept/objective word overlap against stem text. Does not send
    the full bank — top ``limit`` only.
    """
    if not isinstance(assigned, dict) or limit <= 0:
        return []
    planned = planned_intent_words(assigned)
    concept_w = _extract_intent_words(assigned.get("concept") or "")
    obj_w = _extract_intent_words(assigned.get("objective") or "")
    probe = planned | concept_w | obj_w
    if not probe:
        return []

    scored: List[Tuple[float, Dict[str, Any]]] = []
    seen_stems: set = set()
    for q in existing_questions or []:
        if not isinstance(q, dict):
            continue
        stem = " ".join(str(q.get("question") or "").split())
        if not stem:
            continue
        key = stem.lower()
        if key in seen_stems:
            continue
        seen_stems.add(key)
        stem_w = _extract_intent_words(stem)
        if not stem_w:
            continue
        topic = str(q.get("topic") or "").strip().lower()
        concept = str(assigned.get("concept") or "").strip().lower()
        topic_boost = 0.15 if concept and concept in topic else 0.0
        if concept:
            for cw in concept_w:
                if cw and cw in stem_w:
                    topic_boost = max(topic_boost, 0.2)
                    break
        ov = _semantic_intent_overlap(probe, stem_w)
        score = ov + topic_boost
        if score < 0.2:
            continue
        form = question_task_form(stem)
        scored.append(
            (
                score,
                {
                    "question": stem,
                    "topic": q.get("topic") or "",
                    "sub_topic": q.get("sub_topic") or "",
                    "intent_fingerprint": (q.get("intent_fingerprint") or "")
                    or intent_fingerprint(stem),
                    "question_form": form,
                    "overlap_score": round(ov, 3),
                },
            )
        )
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def format_bank_batch_novelty_brief(
    assigned: Dict[str, Any],
    *,
    chapter_excerpt: str = "",
    closest_bank: Sequence[Dict[str, Any]] = (),
    rejected_stems: Sequence[str] = (),
    matched_stems: Sequence[str] = (),
    used_forms: Sequence[str] = (),
    target_difficulty: str = "easy",
) -> str:
    """
    Compact Bank Batch-only novelty context for the generator.

    Soft guidance only — Step 3B duplicate checks remain the hard gate.
    """
    if not isinstance(assigned, dict):
        return ""
    diff = normalize_difficulty(target_difficulty)
    chunk_focus = " ".join((chapter_excerpt or "").split())
    if len(chunk_focus) > 420:
        chunk_focus = chunk_focus[:417] + "..."

    avoid_lines: List[str] = []
    for i, item in enumerate(closest_bank or [], start=1):
        if not isinstance(item, dict):
            continue
        stem = " ".join(str(item.get("question") or "").split())
        if not stem:
            continue
        if len(stem) > 140:
            stem = stem[:137] + "..."
        form = item.get("question_form") or question_task_form(stem)
        fp = (item.get("intent_fingerprint") or "").strip()
        bit = f"{i}) {stem}"
        if form:
            bit += f" [form={form}]"
        if fp:
            bit += f" [intent={fp[:60]}]"
        avoid_lines.append(bit)

    for stem in list(matched_stems or [])[:2]:
        s = " ".join(str(stem).split())
        if not s:
            continue
        if len(s) > 140:
            s = s[:137] + "..."
        line = f"- Matched duplicate: {s}"
        if line not in avoid_lines:
            avoid_lines.append(line)

    avoid_joined = " ".join(avoid_lines).lower()
    for stem in list(rejected_stems or [])[:3]:
        s = " ".join(str(stem).split())
        if not s:
            continue
        if len(s) > 140:
            s = s[:137] + "..."
        if s.lower() in avoid_joined:
            continue
        line = f"- Prior failed attempt: {s}"
        avoid_lines.append(line)
        avoid_joined += " " + s.lower()

    forms = [f for f in (used_forms or []) if f]
    unique_forms = list(dict.fromkeys(forms))[:6]
    forms_line = ", ".join(unique_forms) if unique_forms else "(none detected yet)"

    avoid_block = (
        "\n".join(avoid_lines)
        if avoid_lines
        else "(no close bank stems for this concept yet)"
    )

    if diff == "easy":
        prefer = (
            "Prefer legitimate differences such as: definition→recognition, "
            "recognition→example/non-example, different facts or features, "
            "recognition vs identification, basic classification, direct "
            "one-step application, or different legitimate examples — while "
            "staying within easy difficulty.\n"
            "Do NOT use evaluation, multi-step reasoning, complex comparison, "
            "or multi-concept integration merely to add variety.\n"
        )
        forms_hint = (
            "Compatible Easy forms may include (use only if Grade, Easy "
            "difficulty, chapter content, and the learning objective support "
            "them; do not force all forms): direct knowledge, concept "
            "identification, recognition, classification, example selection, "
            "one-step application, cause and effect when the chapter teaches "
            "it directly.\n"
        )
    else:
        prefer = (
            "Prefer legitimate differences such as: definition→recognition, "
            "recognition→example/non-example, concept identification→comparison, "
            "direct fact→simple application, or one context→another context that "
            "still requires the same taught concept — while staying within "
            f"{diff} difficulty.\n"
        )
        forms_hint = (
            "Compatible forms may include (use only if Grade, requested "
            "difficulty, chapter content, and the learning objective support "
            "them; do not force all forms): direct knowledge, concept "
            "identification, recognition, classification, concept comparison, "
            "application, scenario application, cause and effect, consequence, "
            "interpretation, calculation, multi-step application, "
            "decision-making, error identification, example selection, "
            "relationship, prediction, analysis, evaluation.\n"
        )

    return (
        "\nNOVELTY BRIEF (Bank Batch — generation guidance; validators still apply):\n"
        f"- concept: {assigned.get('concept')}\n"
        f"- objective: {assigned.get('objective')}\n"
        f"- cognitive_form: {assigned.get('cognitive_form')}\n"
        f"- topic/subtopic: {assigned.get('topic') or ''} / "
        f"{assigned.get('subtopic') or assigned.get('sub_topic') or ''}\n"
        f"- target_difficulty: {diff} (do not raise cognitive level just to be different)\n"
        f"- source_chunk_focus: {chunk_focus or '(chunk provided separately)'}\n"
        f"- previously used question forms: {forms_line}\n"
        "Track variety by concept + learning objective + cognitive form + "
        "application/scenario type. Wording changes alone are not variety.\n"
        "Already covered — do NOT paraphrase these objectives/forms:\n"
        f"{avoid_block}\n"
        "Required: test the assigned objective using a meaningfully different "
        "question task or context.\n"
        "Cosmetic-only changes are NOT enough: renaming characters, changing "
        "numbers, reordering options, or lightly rewording the same stem.\n"
        "Do not reuse the same scenario structure with different names "
        "(Riya buys / Aman buys / Neha buys is the same question).\n"
        "Avoid repeatedly starting stems with 'Which of the following...'. "
        "Also avoid repeating 'Which statement...', 'What is...', "
        "'Which option...', or scenario-after-scenario. Vary naturally when "
        "the concept supports it (What does..., Which example..., "
        "A student notices..., Identify..., What would happen..., "
        "Which feature...). Do not force unnatural stem diversity.\n"
        f"{prefer}"
        f"{forms_hint}"
        "Never accept a weaker question for variety. Priority remains: "
        "grounding, correctness, Grade appropriateness, requested difficulty, "
        "option/distractor quality, then uniqueness/variety. If the chapter "
        "only supports a limited Easy form set, prefer a smaller valid pool.\n"
        "Build distractors around THIS novel question task (realistic "
        "misconceptions of the concept as tested here); do not recycle generic "
        "distractors from similar questions.\n"
    )


_STEM_OPENER_KEEP = frozenset(
    {
        "which",
        "what",
        "who",
        "whom",
        "whose",
        "how",
        "why",
        "where",
        "when",
        "identify",
        "select",
        "choose",
        "according",
        "based",
        "consider",
        "read",
        "if",
        "a",
        "an",
        "the",
    }
)

_EASY_UNSAFE_VARIETY_MARKERS = re.compile(
    r"\b(evaluat\w*|integrat\w*|multi[\s-]?step|complex\s+comparison|"
    r"multi[\s-]?concept|synthesi\w*)\b",
    re.I,
)


def scenario_pattern_key(stem: str) -> str:
    """Normalize a stem so name/number swaps share one scenario pattern."""
    tokens: List[str] = []
    for raw in (stem or "").split():
        digits = re.sub(r"[^0-9.]", "", raw)
        if re.fullmatch(r"\d+(?:\.\d+)?", digits or ""):
            tokens.append("NUM")
            continue
        bare = re.sub(r"[^A-Za-z]", "", raw)
        if (
            bare
            and bare[0].isupper()
            and len(bare) >= 3
            and bare.lower() not in _STEM_OPENER_KEEP
        ):
            tokens.append("NAME")
            continue
        lowered = raw.lower()
        if re.sub(r"[^a-z]", "", lowered) in {
            "he",
            "she",
            "his",
            "her",
            "him",
            "hers",
            "their",
            "they",
            "them",
        }:
            tokens.append("PRON")
            continue
        tokens.append(lowered)
    return " ".join(tokens)


def stem_opener_family(stem: str) -> str:
    s = " ".join((stem or "").lower().split())
    if s.startswith("which of the following"):
        return "which_of_the_following"
    if s.startswith("which statement"):
        return "which_statement"
    if s.startswith("what is"):
        return "what_is"
    if s.startswith("which option"):
        return "which_option"
    return ""


def easy_variety_form_allowed(
    cognitive_form: str = "",
    stem: str = "",
    target_difficulty: str = "easy",
) -> bool:
    """True when Easy variety would not introduce Medium/Difficult demand."""
    if normalize_difficulty(target_difficulty) != "easy":
        return True
    blob = f"{cognitive_form or ''} {stem or ''}"
    return not bool(_EASY_UNSAFE_VARIETY_MARKERS.search(blob))


def variety_counts_toward_intent_retirement(
    diag: Optional[Dict[str, Any]],
) -> bool:
    """Paraphrase / same-scenario repeats reuse existing duplicate-hit retirement."""
    if not isinstance(diag, dict):
        return False
    if diag.get("novelty") != "low":
        return False
    labels = set(diag.get("labels") or [])
    return bool(labels & {"paraphrase", "repeated_scenario_pattern"})


def attach_variety_diagnostics(
    record: Dict[str, Any],
    diag: Optional[Dict[str, Any]],
    assigned: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Diagnostic fields only — not a quality reject reason."""
    if not isinstance(record, dict) or not isinstance(diag, dict):
        return record
    assigned = assigned if isinstance(assigned, dict) else {}
    record["variety_novelty"] = diag.get("novelty")
    record["variety_labels"] = list(diag.get("labels") or [])
    record["closest_prior_stem"] = diag.get("closest_prior_stem") or ""
    record["assigned_concept"] = assigned.get("concept") or diag.get("concept")
    record["assigned_objective"] = assigned.get("objective") or diag.get("objective")
    record["assigned_cognitive_form"] = (
        assigned.get("cognitive_form") or diag.get("cognitive_form")
    )
    record["assigned_topic"] = assigned.get("topic") or diag.get("topic")
    record["assigned_subtopic"] = (
        assigned.get("subtopic")
        or assigned.get("sub_topic")
        or diag.get("subtopic")
    )
    record["intent_reuse_count"] = diag.get("intent_reuse_count")
    record["variety_reason"] = diag.get("variety_reason") or ""
    return record


def classify_variety_relation(
    assigned: Dict[str, Any],
    candidate_stem: str,
    prior_questions: Sequence[Any] = (),
    *,
    target_difficulty: str = "easy",
) -> Dict[str, Any]:
    """
    Diagnostic variety relation vs prior stems.

    Duplicate validators remain the hard uniqueness gate. This does not
    accept or reject a question by itself.
    """
    assigned = assigned if isinstance(assigned, dict) else {}
    stem = str(candidate_stem or "").strip()
    labels: List[str] = []
    closest_stem = ""
    closest_overlap = 0.0
    closest_pattern = ""
    closest_rec: Dict[str, Any] = {}
    cand_pattern = scenario_pattern_key(stem)
    cand_words = _extract_intent_words(
        cand_pattern.replace("NAME", " ").replace("NUM", " ").replace("PRON", " ")
    )
    cand_form = (
        str(assigned.get("cognitive_form") or "").strip().lower()
        or question_task_form(stem)
        or ""
    )
    opener = stem_opener_family(stem)

    priors: List[Dict[str, Any]] = []
    for item in prior_questions or []:
        if isinstance(item, str):
            rec = {"question": item}
        elif isinstance(item, dict):
            rec = item
        else:
            continue
        q = str(rec.get("question") or "").strip()
        if q:
            priors.append(rec)

    reuse = 0
    opener_hits = 0
    for rec in priors:
        prior_stem = str(rec.get("question") or "")
        if intents_share_objective(assigned, rec) or (
            _extract_intent_words(assigned.get("concept") or "")
            & _extract_intent_words(
                f"{rec.get('concept') or ''} {rec.get('topic') or ''} {prior_stem}"
            )
        ):
            reuse += 1
        prior_pattern = scenario_pattern_key(prior_stem)
        prior_words = _extract_intent_words(
            prior_pattern.replace("NAME", " ").replace("NUM", " ").replace("PRON", " ")
        )
        overlap = (
            _semantic_intent_overlap(cand_words, prior_words)
            if cand_words and prior_words
            else 0.0
        )
        if overlap > closest_overlap:
            closest_overlap = overlap
            closest_stem = prior_stem
            closest_pattern = prior_pattern
            closest_rec = rec
        if opener and stem_opener_family(prior_stem) == opener:
            opener_hits += 1

    same_objective = False
    if closest_stem:
        same_objective = intents_share_objective(assigned, closest_rec or {"question": closest_stem})

    assigned_concept = _extract_intent_words(assigned.get("concept") or "")
    closest_concept = _extract_intent_words(
        f"{closest_rec.get('concept') or ''} {closest_rec.get('topic') or ''}"
    )
    if not closest_concept and closest_stem:
        closest_concept = _extract_intent_words(closest_stem)
    same_concept = bool(
        assigned_concept and closest_concept and (assigned_concept & closest_concept)
    )

    closest_form = ""
    if closest_rec:
        closest_form = (
            str(
                closest_rec.get("assigned_cognitive_form")
                or closest_rec.get("cognitive_form")
                or ""
            )
            .strip()
            .lower()
            or (question_task_form(closest_stem) if closest_stem else "")
        )
    elif closest_stem:
        closest_form = question_task_form(closest_stem)
    if cand_pattern and closest_pattern and cand_pattern == closest_pattern:
        labels.append("repeated_scenario_pattern")
    if (
        closest_stem
        and closest_overlap >= VARIETY_PARAPHRASE_WORD_OVERLAP
        and same_objective
    ):
        labels.append("paraphrase")
    if same_concept:
        labels.append("repeated_concept")
    if same_objective:
        labels.append("repeated_objective")
    if cand_form and closest_form and cand_form == closest_form:
        labels.append("repeated_cognitive_form")
    if same_objective and cand_form and closest_form and cand_form == closest_form:
        labels.append("repeated_objective_and_form")
    if opener == "which_of_the_following" and opener_hits:
        labels.append("repeated_stem_opener")
    if not easy_variety_form_allowed(
        str(assigned.get("cognitive_form") or ""),
        stem,
        target_difficulty,
    ):
        labels.append("easy_unsafe_variety_form")

    novelty = (
        "low"
        if (
            "paraphrase" in labels
            or "repeated_scenario_pattern" in labels
            or "repeated_objective_and_form" in labels
        )
        else "ok"
    )

    if novelty == "low" and "paraphrase" in labels:
        reason = "paraphrase"
    elif novelty == "low" and "repeated_objective_and_form" in labels:
        reason = "repeated_objective_and_form"
    elif novelty == "low":
        reason = "repeated_scenario_pattern"
    elif same_objective:
        reason = "same_objective_different_wording_check"
    else:
        reason = "distinct_objective_or_application"

    return {
        "novelty": novelty,
        "labels": list(dict.fromkeys(labels)),
        "closest_prior_stem": closest_stem,
        "closest_overlap": round(closest_overlap, 3),
        "concept": assigned.get("concept") or "",
        "objective": assigned.get("objective") or "",
        "cognitive_form": assigned.get("cognitive_form") or cand_form,
        "topic": assigned.get("topic") or "",
        "subtopic": assigned.get("subtopic") or assigned.get("sub_topic") or "",
        "intent_reuse_count": reuse,
        "variety_reason": reason,
    }


def duplicate_intent_keep_feedback(
    assigned: Dict[str, Any],
    *,
    dup_match: Optional[Dict[str, Any]] = None,
) -> str:
    """Feedback when keeping the same intent after a wording duplicate."""
    parts = [
        "INTENT NOVELTY RETRY: Keep the SAME assigned intent "
        f"(concept={assigned.get('concept')}; objective={assigned.get('objective')}). "
        "Do not retire this learning objective yet. "
        "Change the question TASK/FORM or context — not cosmetic rewording."
    ]
    if dup_match:
        ms = (dup_match.get("matched_stem") or "").strip()
        if ms:
            if len(ms) > 120:
                ms = ms[:117] + "..."
            parts.append(f"Add to avoid list (matched duplicate): {ms}")
        mfp = (dup_match.get("matched_intent_fingerprint") or "").strip()
        if mfp:
            parts.append(f"Avoid reproducing intent={mfp[:80]}")
    return " ".join(parts)


def apply_duplicate_intent_policy(
    *,
    active_intent: Dict[str, Any],
    intent_dup_hits: Dict[str, int],
    intent_retired_ids: set,
    intent_remaining: List[Dict[str, Any]],
    intent_assignments: Dict[str, Dict[str, Any]],
    slot_key: str,
    intent_diagnostics: Dict[str, Any],
    dup_match: Optional[Dict[str, Any]] = None,
    target_difficulty: Optional[str] = None,
    usage_questions: Optional[Sequence[Dict[str, Any]]] = None,
) -> Tuple[Optional[Dict[str, Any]], str, bool]:
    """
    Step 8 duplicate policy: keep valid intent after first wording duplicate;
    retire only after repeated duplicates.

    Returns (new_active_intent, extra_feedback, retired).
    """
    rid = str(active_intent.get("intent_id") or "")
    hits = int(intent_dup_hits.get(rid, 0) or 0) + 1
    if rid:
        intent_dup_hits[rid] = hits

    if should_retire_intent_after_duplicate_hits(hits):
        if rid:
            intent_retired_ids.add(rid)
        intent_diagnostics["intents_retired_after_duplicate"] = (
            int(intent_diagnostics.get("intents_retired_after_duplicate") or 0) + 1
        )
        intent_diagnostics["intents_retired_after_repeated_duplicates"] = (
            int(intent_diagnostics.get("intents_retired_after_repeated_duplicates") or 0)
            + 1
        )
        nxt = take_next_unused_intent(
            intent_remaining,
            retired_ids=intent_retired_ids,
            assigned_values=list(intent_assignments.values()),
            target_difficulty=target_difficulty,
            diagnostics=intent_diagnostics,
            usage_questions=usage_questions,
        )
        if nxt:
            intent_assignments[slot_key] = nxt
            return nxt, "", True
        intent_assignments.pop(slot_key, None)
        intent_diagnostics["catalog_exhaustion_count"] = (
            int(intent_diagnostics.get("catalog_exhaustion_count") or 0) + 1
        )
        return None, "", True

    intent_diagnostics["duplicate_retry_same_intent"] = (
        int(intent_diagnostics.get("duplicate_retry_same_intent") or 0) + 1
    )
    extra = duplicate_intent_keep_feedback(active_intent, dup_match=dup_match)
    return active_intent, extra, False


def classify_intent_adherence(
    assigned: Dict[str, Any],
    generated: Dict[str, Any],
) -> str:
    """
    Step 7C calibrated adherence (Bank Batch guidance, not a hard quality validator).

    Returns:
      STRONG ADHERENCE — proceed to existing validators
      PARTIAL ADHERENCE — proceed when concept + core objective are preserved
      DRIFTED — true drift only (clearly different concept/objective)

    Wording differences alone must NOT classify as DRIFTED.
    """
    if not isinstance(assigned, dict) or not isinstance(generated, dict):
        return ADHERENCE_DRIFTED
    stem = str(generated.get("question") or "").strip()
    if not stem:
        return ADHERENCE_DRIFTED

    derived = derive_intent_from_bank_question(
        {
            "question": stem,
            "topic": generated.get("topic") or assigned.get("topic") or "",
            "sub_topic": generated.get("sub_topic") or "",
            "target_difficulty": generated.get("target_difficulty") or "easy",
        },
        use_cache=False,
    )
    if intents_share_objective(assigned, derived):
        return ADHERENCE_STRONG

    stem_words = _extract_intent_words(stem)
    obj_words = _extract_intent_words(assigned.get("objective") or "")
    concept_words = _extract_intent_words(assigned.get("concept") or "")
    planned = planned_intent_words(assigned)
    derived_words = planned_intent_words(derived)
    probe = stem_words | derived_words

    obj_ov = _semantic_intent_overlap(obj_words, probe) if obj_words else 0.0
    con_ov = _semantic_intent_overlap(concept_words, probe) if concept_words else 0.0
    full_ov = _semantic_intent_overlap(planned, probe) if planned else 0.0

    # Task family from raw tokens (stopwords like "define" are stripped by intent stems)
    def _raw_words(text: str) -> set:
        return set(re.sub(r"[^\w\s]", " ", (text or "").lower()).split())

    fam_a = _task_family(
        _raw_words(assigned.get("objective") or "")
        | _raw_words(assigned.get("concept") or "")
        | _raw_words(assigned.get("cognitive_form") or "")
    )
    fam_g = _task_family(
        _raw_words(stem) | _raw_words(derived.get("objective") or "")
    )

    # Define vs distinguish on the same noun is a different objective (TRUE DRIFT)
    if fam_a and fam_g and {fam_a, fam_g} == {"define", "distinguish"}:
        return ADHERENCE_DRIFTED

    # Literal concept phrase in stem (handles short concept labels)
    concept = str(assigned.get("concept") or "").strip().lower()
    stem_low = stem.lower()
    concept_literal = bool(concept) and len(concept) >= 4 and concept in stem_low
    # Drop meta words so "Meaning of denominations" still matches stem "denominations"
    concept_core = concept_words - {
        "meaning",
        "mean",
        "definition",
        "definiti",
        "concept",
        "idea",
        "notion",
        "term",
        "example",
        "introduction",
    }
    concept_noun_hit = bool(concept_core & probe)

    concept_preserved = (
        con_ov >= 0.4
        or concept_literal
        or concept_noun_hit
        or (con_ov >= 0.3 and full_ov >= 0.35)
    )
    # Same task family + shared concept noun → objective substantially preserved
    # even when wording differs (define/example/identify paraphrases).
    same_task_family = bool(fam_a and fam_g and fam_a == fam_g)
    objective_preserved = (
        obj_ov >= 0.28
        or full_ov >= 0.35
        or (
            concept_preserved
            and obj_ov >= 0.18
            and (not fam_a or not fam_g or fam_a == fam_g)
        )
        or (concept_preserved and same_task_family and full_ov >= 0.22)
        or (
            concept_preserved
            and same_task_family
            and fam_a in {"define", "example", "identify", "recall"}
        )
    )

    if obj_ov >= 0.55 and concept_preserved:
        return ADHERENCE_STRONG
    if obj_ov >= 0.4 or (con_ov >= 0.5 and obj_ov >= 0.25):
        return ADHERENCE_PARTIAL
    if concept_preserved and objective_preserved:
        return ADHERENCE_PARTIAL
    # Same concept with a related but non-conflicting task framing → PARTIAL
    if concept_preserved and fam_a and fam_g and fam_a != fam_g:
        # Define vs distinguish on the same noun is a different objective (TRUE DRIFT)
        if {fam_a, fam_g} == {"define", "distinguish"}:
            return ADHERENCE_DRIFTED
        if full_ov >= 0.22:
            return ADHERENCE_PARTIAL

    # TRUE DRIFT: clearly different concept/objective
    return ADHERENCE_DRIFTED


def partial_adherence_may_continue(
    assigned: Dict[str, Any],
    generated: Dict[str, Any],
    *,
    target_difficulty: Optional[str] = None,
    answer_type: Optional[str] = None,
) -> bool:
    """
    PARTIAL may proceed to Step 3B / quality validators when concept and core
    objective are preserved and slot difficulty/answer_type stay fixed.
    """
    if classify_intent_adherence(assigned, generated) != ADHERENCE_PARTIAL:
        return False
    # Slot constraints are owned by the pipeline; generated must not imply a change.
    if target_difficulty is not None:
        gen_diff = generated.get("target_difficulty") or generated.get("difficulty")
        if gen_diff and normalize_difficulty(str(gen_diff)) != normalize_difficulty(
            str(target_difficulty)
        ):
            return False
    if answer_type is not None:
        gen_at = generated.get("answer_type")
        if gen_at and str(gen_at).strip() != str(answer_type).strip():
            return False
    return True


def should_early_reject_for_intent_drift(label: str) -> bool:
    """Hard early exit only for TRUE DRIFT (not PARTIAL/STRONG)."""
    return label == ADHERENCE_DRIFTED


def record_adherence_diagnostic(diagnostics: Dict[str, Any], label: str) -> None:
    if label == ADHERENCE_STRONG:
        diagnostics["adherence_strong"] = int(diagnostics.get("adherence_strong") or 0) + 1
    elif label == ADHERENCE_PARTIAL:
        diagnostics["adherence_partial"] = int(diagnostics.get("adherence_partial") or 0) + 1
    elif label == ADHERENCE_DRIFTED:
        diagnostics["adherence_drifted"] = int(diagnostics.get("adherence_drifted") or 0) + 1


def intent_drift_feedback(assigned: Dict[str, Any]) -> str:
    return (
        f"{INTENT_DRIFT_REJECTION}\n\n"
        "INTENT ADHERENCE RETRY: Keep the SAME assigned intent. "
        f"Concept: {assigned.get('concept')}. "
        f"Objective: {assigned.get('objective')}. "
        f"Cognitive form: {assigned.get('cognitive_form')}. "
        "Do not switch to a different familiar definition or topic stem."
    )


def rejection_is_duplicate(reasons: Sequence[str]) -> bool:
    text = " ".join(str(r).lower() for r in (reasons or []))
    return "duplicate" in text or "near-duplicate" in text


def rejection_is_distractor_or_answer(reasons: Sequence[str]) -> bool:
    text = " ".join(str(r).lower() for r in (reasons or []))
    if "duplicate" in text:
        return False
    return (
        "distractor" in text
        or "answer validity" in text
        or "answer_valid" in text
        or "independently derived" in text
        or "defensible option" in text
    )


def rejection_is_cognitive(reasons: Sequence[str]) -> bool:
    text = " ".join(str(r).lower() for r in (reasons or []))
    return "cognitive difficulty mismatch" in text or "difficulty mismatch" in text


def classify_academic_failure_family(
    reasons: Sequence[str],
) -> Optional[str]:
    """
    Map rejection reasons to one academic failure family for intent retirement.

    Returns None for provider/length/structural/duplicate/intent-drift (those must
    not penalize the academic intent via this counter). At most one family per
    rejection — distractor and cognitive never share a counter.
    """
    if not reasons:
        return None
    jl = " | ".join(str(r).lower() for r in reasons)
    if (
        "validator_unavailable" in jl
        or "generation failed" in jl
        or "llm_timeout" in jl
        or "length limit" in jl
        or "lengthfinish" in jl
    ):
        return None
    if rejection_is_duplicate(reasons):
        return None
    if "intent adherence drift" in jl:
        return None
    if "subjective" in jl and "best" in jl:
        return FAILURE_FAMILY_SUBJECTIVE_BEST
    if rejection_is_cognitive(reasons):
        return FAILURE_FAMILY_COGNITIVE
    if (
        "not appropriate for the selected grade" in jl
        or "grade-inappropriate" in jl
    ):
        return FAILURE_FAMILY_GRADE
    if any(
        k in jl
        for k in (
            "not grounded",
            "grounded in the supplied",
            "possible hallucination",
            "unrelated external",
            "concept is not relevant",
            "requires unrelated external",
        )
    ):
        return FAILURE_FAMILY_GROUNDING
    if any(
        k in jl
        for k in (
            "independent solver",
            "defensible option set",
            "multiple defensible",
            "answer validity failed",
            "information insufficient",
            "arithmetic/numerical",
            "unsupported absolute",
            "grade-inappropriate/untaught terminology",
        )
    ) and "distractor" not in jl:
        return FAILURE_FAMILY_BLIND_ANSWER
    if any(
        k in jl
        for k in (
            "distractor",
            "misconception",
            "answer-style clue",
            "option not independently",
            "unclear/irrelevant distractor",
        )
    ):
        return FAILURE_FAMILY_DISTRACTOR
    if "answer validity" in jl or "answer_valid" in jl:
        return FAILURE_FAMILY_BLIND_ANSWER
    return None


def _parse_cognitive_mismatch_diagnostics(
    rejection_reasons: Optional[Sequence[str]],
) -> Tuple[Optional[str], Optional[int], List[str]]:
    """Extract validated band, score, and low demand criteria from mismatch reasons."""
    validated: Optional[str] = None
    score: Optional[int] = None
    low_dims: List[str] = []
    focus = (
        "reasoning",
        "decision_making",
        "concept_integration",
        "interpretation",
        "application",
    )
    for raw in rejection_reasons or []:
        text = str(raw or "")
        low = text.lower()
        if "cognitive difficulty mismatch" not in low and "difficulty mismatch" not in low:
            continue
        m_val = re.search(r"validated=([a-z]+)", low)
        if m_val:
            validated = normalize_difficulty(m_val.group(1))
        m_score = re.search(r"score=(\d+)", low)
        if m_score:
            score = int(m_score.group(1))
        m_crit = re.search(r"criteria=([^;]+)", text)
        if m_crit:
            for part in m_crit.group(1).split(","):
                if "=" not in part:
                    continue
                name, raw_v = part.split("=", 1)
                name = name.strip()
                try:
                    val = int(raw_v.strip())
                except ValueError:
                    continue
                if name in focus and val <= 2 and name not in low_dims:
                    low_dims.append(name)
        break
    return validated, score, low_dims


def _cognitive_demand_direction(
    target_difficulty: str,
    validated: Optional[str],
    rejection_reasons: Optional[Sequence[str]] = None,
) -> str:
    """Return under | over | unknown from explicit demand tag or band ranks."""
    for raw in rejection_reasons or []:
        low = str(raw or "").lower()
        if "demand=over-demand" in low:
            return "over"
        if "demand=under-demand" in low:
            return "under"
    target = normalize_difficulty(target_difficulty)
    if not validated:
        return "unknown"
    t_rank = _DIFFICULTY_RANK.get(target, 1)
    v_rank = _DIFFICULTY_RANK.get(normalize_difficulty(validated), 1)
    if v_rank < t_rank:
        return "under"
    if v_rank > t_rank:
        return "over"
    return "unknown"


def academic_failure_family_correction(
    family: str,
    intent: Optional[Dict[str, Any]] = None,
    *,
    target_difficulty: str = "easy",
    rejection_reasons: Optional[Sequence[str]] = None,
) -> str:
    """Concise first-failure correction for the same assigned intent."""
    concept = (intent or {}).get("concept") or "the assigned concept"
    objective = (intent or {}).get("objective") or "the assigned objective"
    if family == FAILURE_FAMILY_DISTRACTOR:
        return (
            "INTENT RETRY (distractor): Previous candidate failed because distractors "
            "were too obvious, unrelated, or not misconception-based. Keep the same "
            f"concept/objective ({concept}: {objective}) but create a substantially "
            "different question with plausible misconception-based distractors."
        )
    if family == FAILURE_FAMILY_COGNITIVE:
        diff = normalize_difficulty(target_difficulty)
        validated, _score, low_dims = _parse_cognitive_mismatch_diagnostics(
            rejection_reasons
        )
        demand = _cognitive_demand_direction(diff, validated, rejection_reasons)
        # Easy cognitive retries stay over-demand / simplify (unchanged behavior).
        if diff == "easy":
            base = (
                f"INTENT RETRY (cognitive): Previous candidate exceeded {diff} demand. "
                "Keep one primary concept and no more than one meaningful reasoning step."
            )
        elif demand == "under" or (demand == "unknown" and diff == "difficult"):
            if diff == "difficult":
                base = (
                    "INTENT RETRY (cognitive): Previous candidate was not difficult enough. "
                    f"Preserve the grounded objective ({concept}: {objective}), but require "
                    "stronger analysis/inference/evaluation and multiple connected reasoning "
                    "steps. Do not merely lengthen the scenario or wording. Use connected "
                    "chapter concepts only when naturally supported."
                )
                if low_dims:
                    focus = "/".join(low_dims[:3])
                    base += (
                        f" Increase genuine {focus} depth; do not add superficial context."
                    )
            elif diff == "medium":
                base = (
                    "Previous candidate was too direct for Medium. Preserve the grounded "
                    "concept, but require genuine application or interpretation and 1–2 "
                    "meaningful reasoning steps. Do not make it harder only by adding "
                    "numbers, text, or calculation repetition."
                )
            else:
                base = (
                    f"INTENT RETRY (cognitive): Previous candidate was below {diff} demand. "
                    f"Keep concept/objective ({concept}: {objective}) and raise genuine "
                    "application/interpretation to about 1–2 reasoning steps — without "
                    "jumping to Difficult multi-step integration or longer wording alone."
                )
        elif demand == "over":
            if diff == "difficult":
                base = (
                    "INTENT RETRY (cognitive): Previous candidate overshot Difficult demand. "
                    f"Keep concept/objective ({concept}: {objective}); preserve analysis/"
                    "evaluation but avoid obscure vocabulary, tricks, or unrelated concept stacking."
                )
            else:
                base = (
                    f"INTENT RETRY (cognitive): Previous candidate exceeded {diff} demand. "
                    f"Keep concept/objective ({concept}: {objective}); prefer genuine "
                    "1–2 step application/interpretation without Difficult multi-step integration."
                )
        else:
            # Unknown demand on non-easy: neutral, not Easy simplification.
            base = (
                f"INTENT RETRY (cognitive): Adjust the cognitive task to match target "
                f"difficulty={diff} while keeping concept/objective "
                f"({concept}: {objective})."
            )
        if intent:
            return f"{base}\n{cognitive_form_correction_hint(intent, diff)}"
        return base
    if family == FAILURE_FAMILY_GROUNDING:
        return (
            "INTENT RETRY (grounding): Previous candidate introduced unsupported "
            "content. Stay within the assigned chapter concept and use only "
            f"defensible applications of the taught concept ({concept})."
        )
    if family == FAILURE_FAMILY_GRADE:
        return (
            "INTENT RETRY (grade): Previous candidate was not Grade-appropriate. "
            "Rewrite with Grade-appropriate vocabulary, scenarios, and numerical demand "
            f"while keeping concept/objective ({concept}: {objective})."
        )
    if family == FAILURE_FAMILY_BLIND_ANSWER:
        return (
            "INTENT RETRY (answer defensibility): Previous candidate failed independent "
            "answer checks. Keep the same concept/objective but ensure exactly the "
            "keyed answer set is uniquely defensible from the stem and taught concept."
        )
    if family == FAILURE_FAMILY_SUBJECTIVE_BEST:
        return (
            "INTENT RETRY (subjective best): Avoid 'best/most appropriate/most reasonable' "
            "wording unless an explicit objective decision criterion makes exactly one "
            f"answer defensible. Keep concept/objective ({concept}: {objective})."
        )
    return (
        f"INTENT RETRY: Keep the same assigned concept/objective "
        f"({concept}: {objective}); fix the previous rejection."
    )


def apply_academic_failure_intent_policy(
    *,
    active_intent: Dict[str, Any],
    failure_family: str,
    intent_family_hits: Dict[str, Dict[str, int]],
    intent_retired_ids: set,
    intent_remaining: List[Dict[str, Any]],
    intent_assignments: Dict[str, Dict[str, Any]],
    slot_key: str,
    intent_diagnostics: Dict[str, Any],
    target_difficulty: Optional[str] = None,
    usage_questions: Optional[Sequence[Dict[str, Any]]] = None,
    rejection_reasons: Optional[Sequence[str]] = None,
) -> Tuple[Optional[Dict[str, Any]], str, bool]:
    """
    First hit in a failure family → keep intent + correction.
    Second hit in the SAME family for the SAME intent → retire and replace.

    Different families do not share a counter. Returns
    (new_active_intent, extra_feedback, retired).
    """
    if failure_family not in ACADEMIC_FAILURE_FAMILIES:
        return active_intent, "", False

    rid = str(active_intent.get("intent_id") or "") or f"anon:{slot_key}"
    per_intent = intent_family_hits.setdefault(rid, {})
    hits = int(per_intent.get(failure_family, 0) or 0) + 1
    per_intent[failure_family] = hits
    prior_usage = intent_concept_usage_count(active_intent, usage_questions)

    event: Dict[str, Any] = {
        "intent_id": active_intent.get("intent_id"),
        "concept": active_intent.get("concept"),
        "objective": active_intent.get("objective"),
        "failure_family": failure_family,
        "family_count": hits,
        "retired": False,
        "retirement_reason": None,
        "replacement_intent_id": None,
        "replacement_concept": None,
        "prior_concept_usage_count": prior_usage,
        "saturation_influenced": False,
    }

    if hits < INTENT_FAMILY_HITS_BEFORE_RETIRE:
        intent_diagnostics["academic_failure_family_retries"] = (
            int(intent_diagnostics.get("academic_failure_family_retries") or 0) + 1
        )
        extra = academic_failure_family_correction(
            failure_family,
            active_intent,
            target_difficulty=target_difficulty or "easy",
            rejection_reasons=rejection_reasons,
        )
        events = list(intent_diagnostics.get("academic_failure_events") or [])
        events.append(event)
        intent_diagnostics["academic_failure_events"] = events
        return active_intent, extra, False

    if rid and not str(rid).startswith("anon:"):
        intent_retired_ids.add(rid)
    intent_diagnostics["intents_retired_after_academic_failure"] = (
        int(intent_diagnostics.get("intents_retired_after_academic_failure") or 0) + 1
    )
    event["retired"] = True
    event["retirement_reason"] = f"repeated_{failure_family}_failures={hits}"

    sat_before = int(intent_diagnostics.get("saturation_influenced_selections") or 0)
    nxt = take_next_unused_intent(
        intent_remaining,
        retired_ids=intent_retired_ids,
        assigned_values=[
            v for k, v in intent_assignments.items() if k != slot_key
        ],
        target_difficulty=target_difficulty,
        diagnostics=intent_diagnostics,
        usage_questions=usage_questions,
    )
    sat_after = int(intent_diagnostics.get("saturation_influenced_selections") or 0)
    event["saturation_influenced"] = sat_after > sat_before

    if nxt:
        intent_assignments[slot_key] = nxt
        event["replacement_intent_id"] = nxt.get("intent_id")
        event["replacement_concept"] = nxt.get("concept")
        event["prior_concept_usage_count"] = intent_concept_usage_count(
            nxt, usage_questions
        )
        events = list(intent_diagnostics.get("academic_failure_events") or [])
        events.append(event)
        intent_diagnostics["academic_failure_events"] = events
        extra = (
            f"INTENT RETIRED after repeated {failure_family} failures "
            f"(count={hits}). New assigned intent: concept={nxt.get('concept')}; "
            f"objective={nxt.get('objective')}; cognitive_form={nxt.get('cognitive_form')}. "
            "Write a fresh question for the NEW intent; do not reuse the failed stem."
        )
        return nxt, extra, True

    intent_assignments.pop(slot_key, None)
    intent_diagnostics["catalog_exhaustion_count"] = (
        int(intent_diagnostics.get("catalog_exhaustion_count") or 0) + 1
    )
    events = list(intent_diagnostics.get("academic_failure_events") or [])
    events.append(event)
    intent_diagnostics["academic_failure_events"] = events
    return (
        None,
        f"INTENT RETIRED after repeated {failure_family} failures; "
        "no replacement intent available.",
        True,
    )


def cognitive_form_correction_hint(intent: Dict[str, Any], difficulty: str) -> str:
    diff = normalize_difficulty(difficulty)
    forms = COGNITIVE_FORMS_BY_DIFFICULTY.get(diff) or COGNITIVE_FORMS_BY_DIFFICULTY["easy"]
    preferred = intent.get("cognitive_form") or forms[0]
    return (
        f"COGNITIVE FORM CORRECTION: Keep concept/objective "
        f"'{intent.get('concept')}: {intent.get('objective')}' unchanged. "
        f"Adjust the cognitive task toward target difficulty={diff}. "
        f"Preferred form: {preferred}. Allowed forms: {', '.join(forms)}."
    )


def _chunk_previews(chunks: Sequence[str], *, max_chars_per_chunk: int = 900) -> str:
    parts = []
    for i, ch in enumerate(chunks):
        text = (ch or "").strip().replace("\r\n", "\n")
        if len(text) > max_chars_per_chunk:
            text = text[: max_chars_per_chunk - 20] + "\n...[truncated]..."
        parts.append(f"--- CHUNK {i} ---\n{text}\n")
    return "\n".join(parts)


def build_intent_planner_prompts(
    *,
    grade: str,
    subject: str,
    chapter: int,
    chapter_title: str,
    difficulty: str,
    requested_count: int,
    chunks: Sequence[str],
    concept_catalog: Optional[Dict[str, Any]] = None,
    target_n: Optional[int] = None,
) -> Tuple[str, str]:
    diff = normalize_difficulty(difficulty)
    forms = COGNITIVE_FORMS_BY_DIFFICULTY.get(diff) or COGNITIVE_FORMS_BY_DIFFICULTY["easy"]
    if target_n is None:
        uncapped = max(1, int(round(int(requested_count) * INTENT_CATALOG_SIZE_MULTIPLIER)))
        target_n = min(uncapped, max(1, INTENT_INITIAL_CATALOG_TARGET_CAP))
    catalog = concept_catalog or extract_chapter_concept_catalog(
        "\n".join(chunks) if chunks else ""
    )
    los = catalog.get("learning_outcomes") or []
    sections = catalog.get("sections") or []
    system = (
        "You plan exam QUESTION INTENTS for a question bank. "
        "Output structured intents only — NEVER write full MCQs, options, or answers. "
        "Every intent MUST be grounded in the provided chapter chunks. "
        "Use only concepts present in those chunks. "
        "Do not invent learning objectives that are not supported by the text. "
        "Same topic may appear with different objectives; do not create meaningless "
        "paraphrase variants of the same objective just to increase count. "
        "Cover distinct sections and learning outcomes when the chapter supports them."
    )
    if diff == "easy":
        system = system + " " + BANK_BATCH_EASY_INTENT_RULES
    user = f"""Plan candidate question intents for this Bank Batch.

Grade: {grade or 'unspecified'}
Subject: {subject}
Chapter: {chapter} — {chapter_title}
Target difficulty: {diff}
Requested questions: {requested_count}
Catalog target: about {target_n} distinct grounded intents (~{INTENT_CATALOG_SIZE_MULTIPLIER}× requested).
Produce as many DISTINCT grounded intents as the chapter genuinely supports, aiming for ~{target_n}.
If the chapter cannot support that many without hollow paraphrases, return fewer — quality over padding.

Allowed cognitive_form values for {diff}:
{chr(10).join(f'- {f}' for f in forms)}

Known section headings (hints only): {sections[:20]}
Known learning-outcome lines (hints only): {los[:15]}

Chapter chunks (use chunk_index exactly):
{_chunk_previews(chunks)}

For each intent provide:
topic, sub_topic, concept, objective (one clear question task),
cognitive_form (from the allowed list), source_section (if known),
chunk_index (integer referring to a chunk that supports the concept).

Prefer diverse objectives across sections. Same topic with different tasks is allowed
(e.g. recall a taught definition vs recognize a direct example of the same concept).
Do NOT manufacture filler intents or near-paraphrases of the same objective.
"""
    return system, user


async def generate_intent_catalog_via_llm(
    *,
    grade: str,
    subject: str,
    chapter: int,
    chapter_title: str,
    difficulty: str,
    requested_count: int,
    chunks: Sequence[str],
    concept_catalog: Optional[Dict[str, Any]] = None,
    model_id: Optional[str] = None,
    cost_diagnostics: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """One structured LLM call → raw intent drafts (ungrounded)."""
    # Local import avoids circular import at module load (question_paper ↔ intent).
    from open_notebook.graphs.question_paper import _invoke_structured

    system, user = build_intent_planner_prompts(
        grade=grade,
        subject=subject,
        chapter=chapter,
        chapter_title=chapter_title,
        difficulty=difficulty,
        requested_count=requested_count,
        chunks=chunks,
        concept_catalog=concept_catalog,
    )
    result: IntentCatalogLLMOutput = await _invoke_structured(
        system,
        user,
        model_id,
        IntentCatalogLLMOutput,
        max_tokens=6144,
        temperature=0.35,
        llm_stage=LLM_STAGE_INTENT_PLANNER_CATALOG,
        cost_diagnostics=cost_diagnostics,
        bank_batch_mode=True,
        prompt_composition=build_prompt_composition(
            system_prompt=system,
            user_prompt=user,
            grounding_text=_chunk_previews(chunks),
            static_system_instructions=system,
            intent_objective_form=user,
        ),
    )
    drafts = []
    for i, item in enumerate(result.intents or []):
        drafts.append(normalize_intent_dict(item.model_dump(), index=i))
    return drafts


def catalog_soft_cap(requested_count: int) -> int:
    return max(1, int(round(int(requested_count) * INTENT_CATALOG_SIZE_MULTIPLIER)))


def catalog_hard_cap(requested_count: int) -> int:
    return max(1, int(round(int(requested_count) * INTENT_CATALOG_HARD_MULTIPLIER)))


def should_replenish_catalog(
    *,
    unused_intents: int,
    missing_slots: int,
    catalog_size: int,
    requested_count: int,
    planner_calls: int,
    replenish_rounds: int,
    unused_threshold: Optional[int] = None,
    require_capacity_for_missing: bool = False,
) -> bool:
    """
    True when missing slots remain, unused pool is too small, and budget remains.

    cache_hit alone is never a reason to skip replenishment.

    Prepare-time (require_capacity_for_missing=True): expand when usable
    intents cannot cover the request (e.g. 26 cached vs 50 requested).

    Fill-time (False): expand only when unused remaining falls to the
    threshold, so a 20Q job with leftover unused intents does not keep
    growing the catalog.
    """
    if missing_slots <= 0:
        return False
    if planner_calls >= INTENT_MAX_PLANNER_CALLS_PER_BATCH:
        return False
    if replenish_rounds >= INTENT_MAX_REPLENISH_ROUNDS:
        return False
    if catalog_size >= catalog_hard_cap(requested_count):
        return False
    thresh = (
        INTENT_REPLENISH_UNUSED_THRESHOLD
        if unused_threshold is None
        else int(unused_threshold)
    )
    if unused_intents <= max(0, thresh):
        return True
    if require_capacity_for_missing and unused_intents < missing_slots:
        return True
    return False


def select_undercovered_chunk_indices(
    catalog: Sequence[Dict[str, Any]],
    chunks: Sequence[str],
    *,
    retired_intents: Sequence[Dict[str, Any]] = (),
    accepted_intents: Sequence[Dict[str, Any]] = (),
) -> List[int]:
    """Prefer chunks with the fewest catalog intents (later chunks on ties)."""
    n = len(list(chunks or []))
    if n <= 0:
        return []
    cat_counts = chunk_intent_counts(catalog, n_chunks=n)
    ret_counts = chunk_intent_counts(retired_intents, n_chunks=n)
    acc_counts = chunk_intent_counts(accepted_intents, n_chunks=n)
    ranked = []
    for i in range(n):
        text = (chunks[i] or "").strip()
        if not text:
            continue
        ranked.append(
            (
                cat_counts.get(i, 0),
                acc_counts.get(i, 0),
                ret_counts.get(i, 0),
                -i,
                i,
            )
        )
    ranked.sort()
    return [t[-1] for t in ranked]


def compact_avoid_objectives(
    intents: Sequence[Dict[str, Any]],
    *,
    limit: int = 24,
) -> List[str]:
    lines: List[str] = []
    seen = set()
    for intent in intents or []:
        if not isinstance(intent, dict):
            continue
        concept = str(intent.get("concept") or "").strip()
        obj = str(intent.get("objective") or "").strip()
        if not obj:
            continue
        key = f"{concept}|{obj}".lower()
        if key in seen:
            continue
        seen.add(key)
        bit = f"{concept}: {obj}" if concept else obj
        if len(bit) > 140:
            bit = bit[:137] + "..."
        lines.append(bit)
        if len(lines) >= limit:
            break
    return lines


def merge_grounded_catalog(
    existing: Sequence[Dict[str, Any]],
    newcomers: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    """Append newcomers whose concept+objective is not already represented."""
    merged = [dict(x) for x in existing or [] if isinstance(x, dict)]
    removed = 0
    for raw in newcomers or []:
        if not isinstance(raw, dict):
            removed += 1
            continue
        if any(intents_share_objective(raw, ex) for ex in merged):
            removed += 1
            continue
        merged.append(dict(raw))
    return merged, removed


def filter_replenished_against_used(
    candidates: Sequence[Dict[str, Any]],
    *,
    catalog: Sequence[Dict[str, Any]] = (),
    bank_questions: Sequence[Dict[str, Any]] = (),
    retired_intents: Sequence[Dict[str, Any]] = (),
    accepted_questions: Sequence[Dict[str, Any]] = (),
) -> Tuple[List[Dict[str, Any]], int]:
    available, filtered = filter_intents_against_used(
        candidates,
        bank_questions=bank_questions,
        assigned_intents=list(catalog or []) + list(retired_intents or []),
        accepted_questions=accepted_questions,
    )
    return available, filtered


def build_replenish_prompts(
    *,
    grade: str,
    subject: str,
    chapter: int,
    chapter_title: str,
    difficulty: str,
    chunk_index: int,
    chunk_text: str,
    batch_size: int,
    avoid_objectives: Sequence[str],
    heavy_topics: Sequence[str],
) -> Tuple[str, str]:
    diff = normalize_difficulty(difficulty)
    forms = COGNITIVE_FORMS_BY_DIFFICULTY.get(diff) or COGNITIVE_FORMS_BY_DIFFICULTY["easy"]
    excerpt = (chunk_text or "").strip()
    if len(excerpt) > 2800:
        excerpt = excerpt[:2780] + "\n...[truncated]..."
    avoid = "\n".join(f"- {x}" for x in (avoid_objectives or [])[:24]) or "- (none)"
    heavy = ", ".join(heavy_topics[:12]) if heavy_topics else "(none)"
    n = max(8, min(12, int(batch_size or INTENT_REPLENISH_BATCH_SIZE)))
    system = (
        "You plan additional exam QUESTION INTENTS for a question bank. "
        "Output structured intents only — NEVER write full MCQs. "
        "Every intent MUST be grounded in the SINGLE chapter chunk provided. "
        "Create NEW legitimate learning objectives from under-covered content. "
        "Do NOT paraphrase objectives listed as already covered. "
        "Same topic with a different objective is allowed."
    )
    if diff == "easy":
        system = system + " " + BANK_BATCH_EASY_INTENT_RULES
    user = f"""Add about {n} DISTINCT grounded question intents from this under-covered chunk.

Grade: {grade or 'unspecified'}
Subject: {subject}
Chapter: {chapter} — {chapter_title}
Target difficulty: {diff}
Required chunk_index for every intent: {chunk_index}

Allowed cognitive_form values:
{chr(10).join(f'- {f}' for f in forms)}

Heavily represented topics/concepts (prefer others when the chunk allows): {heavy}

Already covered — do NOT paraphrase these concept/objective pairs:
{avoid}

--- CHUNK {chunk_index} ---
{excerpt}
--- END CHUNK ---

Return at most {n} intents. Prefer genuine new tasks still at {diff} difficulty
{"(recall / identify / recognize / one-step application — not compare/evaluate/infer)." if diff == "easy" else "(definition vs example vs compare vs simple application)." }
"""
    return system, user


async def generate_replenish_intents_via_llm(
    *,
    grade: str,
    subject: str,
    chapter: int,
    chapter_title: str,
    difficulty: str,
    chunk_index: int,
    chunk_text: str,
    batch_size: int,
    avoid_objectives: Sequence[str],
    heavy_topics: Sequence[str],
    model_id: Optional[str] = None,
    cost_diagnostics: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    from open_notebook.graphs.question_paper import _invoke_structured

    system, user = build_replenish_prompts(
        grade=grade,
        subject=subject,
        chapter=chapter,
        chapter_title=chapter_title,
        difficulty=difficulty,
        chunk_index=chunk_index,
        chunk_text=chunk_text,
        batch_size=batch_size,
        avoid_objectives=avoid_objectives,
        heavy_topics=heavy_topics,
    )
    result: IntentCatalogLLMOutput = await _invoke_structured(
        system,
        user,
        model_id,
        IntentCatalogLLMOutput,
        max_tokens=3072,
        temperature=0.4,
        llm_stage=LLM_STAGE_INTENT_PLANNER_REPLENISH,
        cost_diagnostics=cost_diagnostics,
        bank_batch_mode=True,
        prompt_composition=build_prompt_composition(
            system_prompt=system,
            user_prompt=user,
            grounding_text=chunk_text or "",
            static_system_instructions=system,
            intent_objective_form=user,
        ),
    )
    drafts = []
    for i, item in enumerate(result.intents or []):
        data = item.model_dump()
        data["chunk_index"] = int(chunk_index)
        drafts.append(normalize_intent_dict(data, index=i))
    return drafts


def _heavy_topics(catalog: Sequence[Dict[str, Any]], *, min_count: int = 3) -> List[str]:
    counts: Dict[str, int] = {}
    for intent in catalog or []:
        t = str(intent.get("topic") or "").strip()
        c = str(intent.get("concept") or "").strip()
        if t:
            counts[t] = counts.get(t, 0) + 1
        if c:
            counts[c] = counts.get(c, 0) + 1
    return [k for k, n in sorted(counts.items(), key=lambda kv: -kv[1]) if n >= min_count]


async def replenish_intent_catalog_once(
    *,
    catalog: List[Dict[str, Any]],
    chunks: Sequence[str],
    requested_count: int,
    grade: str,
    subject: str,
    chapter: int,
    chapter_title: str,
    difficulty: str,
    bank_questions: Sequence[Dict[str, Any]] = (),
    retired_intents: Sequence[Dict[str, Any]] = (),
    accepted_questions: Sequence[Dict[str, Any]] = (),
    diagnostics: Optional[Dict[str, Any]] = None,
    model_id: Optional[str] = None,
    batch_size: Optional[int] = None,
    cost_diagnostics: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    One chunk-based replenishment round. Returns (new_catalog, grounded_added).
    """
    diag = diagnostics if diagnostics is not None else empty_intent_diagnostics()
    size = max(8, min(12, int(batch_size or INTENT_REPLENISH_BATCH_SIZE)))
    unused_before = int(diag.get("unused_intents_before_replenish") or 0)
    preferred = select_undercovered_chunk_indices(
        catalog,
        chunks,
        retired_intents=retired_intents,
        accepted_intents=accepted_questions,
    )
    if not preferred:
        return list(catalog), 0

    chunk_index = preferred[0]
    chunk_text = chunks[chunk_index] if 0 <= chunk_index < len(chunks) else ""
    avoid = compact_avoid_objectives(list(catalog) + list(retired_intents or []))
    for extra in compact_avoid_objectives(list(bank_questions or []), limit=12):
        if extra not in avoid:
            avoid.append(extra)
    avoid = avoid[:24]

    diag["planner_calls"] = int(diag.get("planner_calls") or 0) + 1
    diag["replenishment_rounds"] = int(diag.get("replenishment_rounds") or 0) + 1
    diag["intents_requested_per_replenish"] = size
    diag["cache_expansion_count"] = int(diag.get("cache_expansion_count") or 0) + 1

    try:
        raw = await generate_replenish_intents_via_llm(
            grade=grade,
            subject=subject,
            chapter=chapter,
            chapter_title=chapter_title,
            difficulty=difficulty,
            chunk_index=chunk_index,
            chunk_text=chunk_text,
            batch_size=size,
            avoid_objectives=avoid,
            heavy_topics=_heavy_topics(catalog),
            model_id=model_id,
            cost_diagnostics=cost_diagnostics,
        )
    except Exception as e:
        logger.error(f"Intent replenish LLM failed: {e}")
        raw = []

    diag["raw_intents_returned"] = int(diag.get("raw_intents_returned") or 0) + len(raw)
    grounded, discarded_g = ground_intent_catalog(raw, chunks)
    unique, dup_removed = filter_replenished_against_used(
        grounded,
        catalog=catalog,
        bank_questions=bank_questions,
        retired_intents=retired_intents,
        accepted_questions=accepted_questions,
    )
    merged, merge_dups = merge_grounded_catalog(catalog, unique)
    hard = catalog_hard_cap(requested_count)
    if len(merged) > hard:
        extra = len(merged) - hard
        merged = merged[:hard]
        merge_dups += extra
    added = max(0, len(merged) - len(catalog))
    diag["grounded_new_intents"] = int(diag.get("grounded_new_intents") or 0) + added
    diag["duplicate_intents_removed"] = int(diag.get("duplicate_intents_removed") or 0) + (
        dup_removed + merge_dups + discarded_g
    )
    diag["per_chunk_intent_counts"] = {
        str(k): v for k, v in chunk_intent_counts(merged, n_chunks=len(chunks)).items()
    }
    diag["unused_intents_after_replenish"] = unused_before + added
    logger.info(
        f"Intent replenish chunk={chunk_index} raw={len(raw)} grounded={len(grounded)} "
        f"added={added} catalog={len(merged)}"
    )
    return merged, added


async def expand_intent_catalog_for_request(
    *,
    catalog: List[Dict[str, Any]],
    chunks: Sequence[str],
    requested_count: int,
    missing_slots: int,
    unused_intents: int,
    grade: str,
    subject: str,
    chapter: int,
    chapter_title: str,
    difficulty: str,
    bank_questions: Sequence[Dict[str, Any]] = (),
    retired_intents: Sequence[Dict[str, Any]] = (),
    accepted_questions: Sequence[Dict[str, Any]] = (),
    diagnostics: Optional[Dict[str, Any]] = None,
    model_id: Optional[str] = None,
    cache_key: str = "",
    book_id: str = "",
    content_hash: str = "",
    require_capacity_for_missing: bool = True,
    cost_diagnostics: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Expand catalog while unused pool cannot cover missing slots / threshold."""
    diag = diagnostics if diagnostics is not None else empty_intent_diagnostics()
    pool = list(catalog)
    rounds_start = int(diag.get("replenishment_rounds") or 0)
    while should_replenish_catalog(
        unused_intents=unused_intents,
        missing_slots=missing_slots,
        catalog_size=len(pool),
        requested_count=requested_count,
        planner_calls=int(diag.get("planner_calls") or 0),
        replenish_rounds=int(diag.get("replenishment_rounds") or 0),
        require_capacity_for_missing=require_capacity_for_missing,
    ):
        if int(diag.get("replenishment_rounds") or 0) - rounds_start >= INTENT_MAX_REPLENISH_ROUNDS:
            break
        if len(pool) >= catalog_soft_cap(requested_count) and unused_intents >= missing_slots:
            break
        diag["unused_intents_before_replenish"] = unused_intents
        new_pool, added = await replenish_intent_catalog_once(
            catalog=pool,
            chunks=chunks,
            requested_count=requested_count,
            grade=grade,
            subject=subject,
            chapter=chapter,
            chapter_title=chapter_title,
            difficulty=difficulty,
            bank_questions=bank_questions,
            retired_intents=retired_intents,
            accepted_questions=accepted_questions,
            diagnostics=diag,
            model_id=model_id,
            cost_diagnostics=cost_diagnostics,
        )
        if added <= 0:
            break
        pool = new_pool
        unused_intents = unused_intents + added
        if cache_key:
            save_cached_intent_catalog(
                cache_key,
                pool,
                meta={
                    "book_id": book_id,
                    "chapter": chapter,
                    "difficulty": normalize_difficulty(difficulty),
                    "content_hash": content_hash,
                    "catalog_version": INTENT_CATALOG_SCHEMA_VERSION,
                    "planner_calls_used": int(diag.get("planner_calls") or 0),
                    "status": INTENT_CATALOG_STATUS_COMPLETE,
                },
            )
    diag["catalog_size"] = len(pool)
    diag["grounded_intents"] = len(pool)
    diag["unused_intents_after_replenish"] = unused_intents
    return pool


async def replenish_running_pool(
    *,
    catalog: List[Dict[str, Any]],
    remaining: List[Dict[str, Any]],
    missing_slots: int,
    requested_count: int,
    chunks: Sequence[str],
    grade: str,
    subject: str,
    chapter: int,
    chapter_title: str,
    difficulty: str,
    bank_questions: Sequence[Dict[str, Any]] = (),
    retired_intents: Sequence[Dict[str, Any]] = (),
    accepted_questions: Sequence[Dict[str, Any]] = (),
    diagnostics: Optional[Dict[str, Any]] = None,
    model_id: Optional[str] = None,
    cache_key: str = "",
    book_id: str = "",
    content_hash: str = "",
    cost_diagnostics: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Top up remaining unused intents during fill/refill. Preserves existing remaining order."""
    diag = diagnostics if diagnostics is not None else empty_intent_diagnostics()
    unused = len(remaining)
    if not should_replenish_catalog(
        unused_intents=unused,
        missing_slots=missing_slots,
        catalog_size=len(catalog),
        requested_count=requested_count,
        planner_calls=int(diag.get("planner_calls") or 0),
        replenish_rounds=int(diag.get("replenishment_rounds") or 0),
        require_capacity_for_missing=False,
    ):
        return catalog, remaining
    old_ids = {str(x.get("intent_id") or "") for x in catalog}
    expanded = await expand_intent_catalog_for_request(
        catalog=catalog,
        chunks=chunks,
        requested_count=requested_count,
        missing_slots=missing_slots,
        unused_intents=unused,
        grade=grade,
        subject=subject,
        chapter=chapter,
        chapter_title=chapter_title,
        difficulty=difficulty,
        bank_questions=bank_questions,
        retired_intents=retired_intents,
        accepted_questions=accepted_questions,
        diagnostics=diag,
        model_id=model_id,
        cache_key=cache_key,
        book_id=book_id,
        content_hash=content_hash,
        require_capacity_for_missing=False,
        cost_diagnostics=cost_diagnostics,
    )
    extra = [
        x
        for x in expanded
        if str(x.get("intent_id") or "") not in old_ids
    ]
    remaining = list(remaining) + extra
    return expanded, remaining


async def build_or_load_base_intent_catalog(
    *,
    book_id: str,
    chapter: int,
    difficulty: str,
    chapter_text: str,
    chunks: Sequence[str],
    grade: str,
    subject: str,
    chapter_title: str,
    requested_count: int,
    concept_catalog: Optional[Dict[str, Any]] = None,
    model_id: Optional[str] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    cost_diagnostics: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Return grounded base catalog for book/chapter/difficulty (cached).

    Does NOT filter against the live Question Bank — that happens per batch.
    """
    diag = diagnostics if diagnostics is not None else empty_intent_diagnostics()
    diag["enabled"] = True
    c_hash = chapter_content_hash(chapter_text)
    key = intent_cache_key(
        book_id=book_id or "unknown-book",
        chapter=chapter,
        difficulty=difficulty,
        content_hash=c_hash,
    )
    diag["content_hash"] = c_hash
    diag["cache_key"] = key
    diag["target_catalog_size"] = max(
        1, int(round(int(requested_count) * INTENT_CATALOG_SIZE_MULTIPLIER))
    )

    cached = load_cached_intent_catalog(key)
    if cached is not None:
        grounded, discarded = ground_intent_catalog(cached, chunks)
        if grounded:
            diag["cache_hit"] = True
            diag["initial_cached_catalog_size"] = len(grounded)
            diag["catalog_size"] = len(cached)
            diag["grounded_intents"] = len(grounded)
            diag["ungrounded_discarded"] = int(diag.get("ungrounded_discarded") or 0) + discarded
            diag["per_chunk_intent_counts"] = {
                str(k): v
                for k, v in chunk_intent_counts(grounded, n_chunks=len(chunks)).items()
            }
            logger.info(
                f"Intent catalog cache HIT key={key[:12]}… grounded={len(grounded)} "
                f"(cache_hit does not imply catalog is large enough for this request)"
            )
            return grounded
        logger.info(
            f"Intent catalog cache IGNORED key={key[:12]}… "
            f"(empty or not reusable; will rebuild)"
        )

    diag["cache_hit"] = False
    diag["initial_cached_catalog_size"] = 0
    planner_error: Optional[str] = None
    try:
        raw = await generate_intent_catalog_via_llm(
            grade=grade,
            subject=subject,
            chapter=chapter,
            chapter_title=chapter_title,
            difficulty=difficulty,
            requested_count=requested_count,
            chunks=chunks,
            concept_catalog=concept_catalog,
            model_id=model_id,
            cost_diagnostics=cost_diagnostics,
        )
        diag["planner_calls"] = int(diag.get("planner_calls") or 0) + 1
        diag["raw_intents_returned"] = int(diag.get("raw_intents_returned") or 0) + len(
            raw
        )
    except Exception as e:
        logger.error(f"Intent catalog LLM failed: {e}")
        planner_error = str(e)
        raw = []

    grounded, discarded = ground_intent_catalog(raw, chunks)
    diag["catalog_size"] = len(raw)
    diag["grounded_intents"] = len(grounded)
    diag["ungrounded_discarded"] = discarded
    diag["per_chunk_intent_counts"] = {
        str(k): v for k, v in chunk_intent_counts(grounded, n_chunks=len(chunks)).items()
    }
    if planner_error:
        status = INTENT_CATALOG_STATUS_FAILED
    elif grounded:
        status = INTENT_CATALOG_STATUS_COMPLETE
    elif raw:
        status = INTENT_CATALOG_STATUS_PARTIAL
    else:
        status = INTENT_CATALOG_STATUS_FAILED
    save_cached_intent_catalog(
        key,
        grounded if status == INTENT_CATALOG_STATUS_COMPLETE else [],
        meta={
            "book_id": book_id,
            "chapter": chapter,
            "difficulty": normalize_difficulty(difficulty),
            "content_hash": c_hash,
            "requested_count": requested_count,
            "catalog_version": INTENT_CATALOG_SCHEMA_VERSION,
            "planner_calls_used": int(diag.get("planner_calls") or 0),
            "status": status,
            "error": (planner_error or "")[:500],
        },
    )
    logger.info(
        f"Intent catalog built key={key[:12]}… raw={len(raw)} grounded={len(grounded)} "
        f"discarded={discarded} status={status}"
    )
    return grounded


def prepare_batch_intent_assignments(
    *,
    base_catalog: Sequence[Dict[str, Any]],
    slots: Sequence[Any],
    bank_questions: Sequence[Dict[str, Any]],
    diagnostics: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Filter base catalog against bank (derived intents) and assign to slots."""
    diag = diagnostics if diagnostics is not None else empty_intent_diagnostics()
    enriched_bank, derived_n = enrich_bank_questions_with_intents(bank_questions)
    diag["bank_intents_derived"] = derived_n
    available, filtered = filter_intents_against_used(
        base_catalog,
        bank_questions=enriched_bank,
    )
    diag["intents_filtered_already_in_bank"] = filtered
    slot0 = slots[0] if slots else None
    if isinstance(slot0, dict):
        slot_diff = str(slot0.get("target_difficulty") or "")
    else:
        slot_diff = str(getattr(slot0, "target_difficulty", "") or "")
    available = filter_easy_safe_intents(
        available, difficulty=slot_diff, diagnostics=diag
    )
    assignments, remaining, assigned_n = assign_intents_to_slots(
        slots,
        available,
        usage_questions=enriched_bank,
        diagnostics=diag,
    )
    diag["intents_assigned"] = assigned_n
    diag["grounded_intents"] = len(list(base_catalog or []))
    diag["catalog_size"] = max(int(diag.get("catalog_size") or 0), len(list(base_catalog or [])))
    return assignments, remaining, diag
