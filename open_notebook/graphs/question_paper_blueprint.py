"""
Data-driven question-paper blueprint, cognitive scoring, chapter chunking, and audit.

This module is LLM-free so distributions and difficulty mapping can be unit-tested.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter

DIFFICULTIES = ("easy", "medium", "difficult")
ANSWER_TYPES = ("single_correct", "multiple_correct")
COGNITIVE_CRITERIA = (
    "knowledge",
    "reasoning",
    "context",
    "application",
    "interpretation",
    "decision_making",
    "concept_integration",
    "distractor_quality",
)

# Chunk long chapters so later portions remain eligible for generation.
CHAPTER_CHUNK_SIZE = 4000
CHAPTER_CHUNK_OVERLAP = 400
MAX_SLOT_ATTEMPTS = 3
MAX_REFILL_ATTEMPTS = 5
MAX_SLOT_CONCURRENCY = 3

# Centralized cognitive definitions used by the generator (not the validator mapping).
DIFFICULTY_DEFINITIONS = """
EASY — Tests direct recall, recognition, basic comprehension, or straightforward application of one concept.
Normally: one primary concept; familiar/direct context; 0–1 simple reasoning step; information explicitly
covered in the material; no meaningful multi-concept integration; no significant analysis/evaluation.

MEDIUM — Tests genuine application or interpretation.
Normally: recall alone is insufficient; 1–2 meaningful reasoning steps; familiar or moderately modified
context; one main concept, possibly one related concept; requires interpretation/comparison/application;
plausible distractors.

DIFFICULT — Tests higher-order reasoning. Require at least two strong higher-order characteristics such as:
multiple connected reasoning steps; unfamiliar/non-routine context; integration of two or more important
concepts; analysis of relationships; evaluation of alternatives; complex inference; troubleshooting;
transfer of knowledge; selecting the best solution under constraints.

Do NOT create artificial difficulty through confusing wording, unnecessary text, difficult vocabulary,
tricks, excessive arithmetic, or out-of-syllabus information.
"""

VALIDATOR_CRITERION_RUBRIC = """
Score each criterion 1, 2, or 3. Do not compute a total.

1. Knowledge
   1 = Recall of one fact/concept
   2 = Application of learned knowledge
   3 = Integration of multiple concepts

2. Reasoning
   1 = No reasoning or one simple step
   2 = 1–2 reasoning steps
   3 = Multiple connected reasoning steps

3. Context
   1 = Direct and familiar
   2 = Familiar but modified
   3 = Unfamiliar or non-routine

4. Application
   1 = Direct application of known rule/procedure
   2 = Select and apply an appropriate concept/procedure
   3 = Adapt/combine multiple concepts/procedures

5. Interpretation
   1 = Information is explicit
   2 = Requires interpretation
   3 = Requires inference/analysis of complex information

6. Decision Making
   1 = Correct answer directly identifiable
   2 = Selection between plausible alternatives
   3 = Evaluation of competing alternatives

7. Concept Integration
   1 = One concept
   2 = One main concept plus related concept
   3 = Multiple important concepts integrated

8. Distractor Quality
   1 = Incorrect options easily eliminated
   2 = Plausible distractors requiring understanding
   3 = Distractors represent realistic misconceptions

If uncertain/borderline between two levels, score conservatively toward the lower level
unless the higher level is clearly justified.
"""

# Default 50-question examination preset (Chapter × Difficulty + Difficulty × Answer Type).
DEFAULT_PRESET: Dict[str, Any] = {
    "id": "grade_default_50_mcq",
    "total_questions": 50,
    "pass_percentage": 70,
    "options_per_question": 5,
    "format": "mcq",
    "language": "en",
    "chapter_difficulty": {
        "1": {"easy": 3, "medium": 4, "difficult": 2},
        "2": {"easy": 3, "medium": 4, "difficult": 4},
        "3": {"easy": 4, "medium": 5, "difficult": 5},
        "4": {"easy": 4, "medium": 5, "difficult": 7},
    },
    "difficulty_answer_types": {
        "easy": {"single_correct": 12, "multiple_correct": 2},
        "medium": {"single_correct": 13, "multiple_correct": 5},
        "difficult": {"single_correct": 11, "multiple_correct": 7},
    },
}


@dataclass
class QuestionSlot:
    question_number: int
    chapter: int
    chapter_title: str
    target_difficulty: str
    answer_type: str
    grade: str
    subject: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_difficulty(value: Optional[str]) -> str:
    """Map legacy 'hard' to 'difficult'."""
    raw = (value or "medium").strip().lower()
    if raw in ("hard", "difficult"):
        return "difficult"
    if raw in ("easy", "medium"):
        return raw
    return "medium"


def map_cognitive_score(total: int) -> str:
    """Map summed 8-criterion score (8–24) to Easy / Medium / Difficult."""
    if total < 8 or total > 24:
        raise ValueError(f"Cognitive total must be 8–24, got {total}")
    if total <= 12:
        return "easy"
    if total <= 18:
        return "medium"
    return "difficult"


def clamp_criterion_scores(raw: Dict[str, Any]) -> Tuple[Dict[str, int], List[str]]:
    """Validate/clamp each criterion to 1–3. Returns (scores, errors)."""
    scores: Dict[str, int] = {}
    errors: List[str] = []
    for key in COGNITIVE_CRITERIA:
        try:
            value = int(raw.get(key))
        except (TypeError, ValueError):
            errors.append(f"{key}: missing or non-integer")
            scores[key] = 1
            continue
        if value < 1 or value > 3:
            errors.append(f"{key}: {value} not in 1–3")
            value = min(3, max(1, value))
        scores[key] = value
    return scores, errors


def cognitive_total(scores: Dict[str, int]) -> int:
    return sum(scores[k] for k in COGNITIVE_CRITERIA)


def preset_from_dict(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a deep copy of the default preset, optionally overlaid with caller data."""
    preset = copy.deepcopy(DEFAULT_PRESET)
    if not data:
        return preset
    for key in (
        "id",
        "total_questions",
        "pass_percentage",
        "options_per_question",
        "format",
        "language",
        "chapter_difficulty",
        "difficulty_answer_types",
    ):
        if key in data and data[key] is not None:
            preset[key] = copy.deepcopy(data[key])
    # Normalize chapter keys to strings
    preset["chapter_difficulty"] = {
        str(k): {normalize_difficulty(dk): int(dv) for dk, dv in v.items()}
        for k, v in preset["chapter_difficulty"].items()
    }
    preset["difficulty_answer_types"] = {
        normalize_difficulty(dk): {
            "single_correct": int(v.get("single_correct", 0)),
            "multiple_correct": int(v.get("multiple_correct", 0)),
        }
        for dk, v in preset["difficulty_answer_types"].items()
    }
    return preset


def _spread_indices(total: int, k: int) -> List[int]:
    """Spread k distinct indices evenly across [0, total)."""
    if k <= 0 or total <= 0:
        return []
    if k >= total:
        return list(range(total))
    if k == 1:
        return [total // 2]
    raw = [round(i * (total - 1) / (k - 1)) for i in range(k)]
    seen: set[int] = set()
    unique: List[int] = []
    for idx in raw:
        idx = min(total - 1, max(0, idx))
        if idx not in seen:
            seen.add(idx)
            unique.append(idx)
    nxt = 0
    while len(unique) < k and nxt < total:
        if nxt not in seen:
            seen.add(nxt)
            unique.append(nxt)
        nxt += 1
    return sorted(unique)


def required_chapter_count(preset: Optional[Dict[str, Any]] = None) -> int:
    """Number of chapter rows in the blueprint matrix."""
    p = preset_from_dict(preset)
    return len(p["chapter_difficulty"])


def validate_chapter_selection(
    preset: Optional[Dict[str, Any]],
    selected_count: int,
) -> None:
    """Book-grounded generation must use exactly as many chapters as the blueprint has rows."""
    required = required_chapter_count(preset)
    if selected_count != required:
        raise ValueError(
            f"This blueprint requires exactly {required} chapter(s), but {selected_count} were "
            f"selected. Chapters are not merged or dropped. Select exactly {required} chapters, "
            f"or send a blueprint whose chapter_difficulty matrix has {selected_count} rows."
        )


def build_effective_preset(
    preset: Optional[Dict[str, Any]] = None,
    chapter_titles: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    Bind optional chapter titles onto the preset. Does not merge or drop chapters.

    Empty titles = topic-only mode (synthetic Chapter 1..N labels).
    Non-empty titles must match the matrix row count exactly.
    """
    p = preset_from_dict(preset)
    titles = [t for t in (chapter_titles or []) if str(t).strip()]
    if titles:
        validate_chapter_selection(p, len(titles))
        p["chapter_titles"] = list(titles)
    else:
        p["chapter_titles"] = [
            f"Chapter {k}" for k in sorted(p["chapter_difficulty"].keys(), key=int)
        ]
    p["total_questions"] = sum(
        sum(int(v) for v in counts.values()) for counts in p["chapter_difficulty"].values()
    )
    return p


def decide_slot_outcome(passed: bool, attempt: int, max_attempts: int = MAX_SLOT_ATTEMPTS) -> str:
    """Return accept | retry | needs_manual_review. Never changes slot constraints."""
    if passed:
        return "accept"
    if attempt < max_attempts:
        return "retry"
    return "needs_manual_review"


def evaluate_answer_type(answer_type: str, correct_indices: Sequence[int], option_count: int) -> List[str]:
    """Python-side answer-type rules (not LLM)."""
    errors: List[str] = []
    indices = list(correct_indices or [])
    if option_count != 5:
        errors.append(f"expected 5 options, got {option_count}")
    if any(i < 0 or i >= option_count for i in indices):
        errors.append("correct_indices out of range")
    if answer_type == "single_correct" and len(indices) != 1:
        errors.append("single_correct requires exactly one correct answer")
    if answer_type == "multiple_correct" and len(indices) < 2:
        errors.append("multiple_correct requires more than one correct answer")
    if not indices:
        errors.append("no correct answers provided")
    return errors


_GENERIC_TOPIC_RE = re.compile(
    r"^(grade|chapter|section|unit)\s*\d",
    re.IGNORECASE,
)


_SUBJECTIVE_BEST_RE = re.compile(
    r"\b(best|smartest|most\s+appropriate|better)\b",
    re.IGNORECASE,
)

# When a question uses subjective terms like "best", it must also provide an
# objective decision criterion (constraints/targets) in the stem.
_OBJECTIVE_CRITERION_RE = re.compile(
    r"\b(reserve|emergency|budget|spending|constraint|within|at\s+least|at\s+most|maxim(?:i|a)ze|minim(?:i|a)ze|save[s]?|savings|toward)\b",
    re.IGNORECASE,
)

_FINANCIAL_CONTEXT_RE = re.compile(
    r"\b(interest|savings|deposit|loan|budget|spending|reserve|emergency|compounding|principal|bank|account|coins|notes|currency|invest|investment|return|risk)\b",
    re.IGNORECASE,
)

_OFFTOPIC_INDICATORS_RE = re.compile(
    r"\b(manager|temple|gifts?|free\s+gifts?|priest|donation)\b",
    re.IGNORECASE,
)


def validate_topic_metadata(
    topic: str,
    sub_topic: str,
    chapter_title: str,
    subject: Optional[str] = None,
) -> List[str]:
    """Reject generic topic/sub_topic metadata that doesn't name a real concept."""
    errors: List[str] = []
    t = (topic or "").strip()
    st = (sub_topic or "").strip()
    ct = (chapter_title or "").strip().lower()
    subj = (subject or "").strip()

    if not t or _GENERIC_TOPIC_RE.match(t):
        errors.append(f"generic topic metadata: '{t}' — must name an actual concept")
    elif t.lower() == ct or t.lower().replace(" ", "") == ct.replace(" ", ""):
        errors.append(f"topic metadata '{t}' just repeats the chapter title")

    # The generator currently treats `subject` as the exam broad topic. `topic`
    # should be a more specific concept, not a repetition of the subject label.
    if subj and t and t.lower() == subj.lower():
        errors.append(f"topic metadata '{t}' must not equal subject")

    if st and _GENERIC_TOPIC_RE.match(st):
        errors.append(f"generic sub_topic metadata: '{st}'")

    return errors


_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "about",
    "between", "through", "during", "before", "after", "above", "below",
    "it", "its", "this", "that", "these", "those", "what", "which",
    "who", "whom", "how", "when", "where", "why", "not", "no", "nor",
    "but", "or", "and", "if", "then", "than", "so", "yet", "both",
    "each", "every", "all", "any", "few", "more", "most", "some",
    "such", "only", "very", "just", "also", "much", "mean", "means",
    "define", "describe", "explain",
})

_SUFFIX_RE = re.compile(r"(ing|tion|ment|ness|ity|ies|es|ed|ly|er|est|s)$")


def _crude_stem(word: str) -> str:
    """Minimal suffix stripping for intent comparison (not a real lemmatiser)."""
    if len(word) <= 4:
        return word
    stemmed = _SUFFIX_RE.sub("", word)
    return stemmed if len(stemmed) >= 3 else word


def _extract_intent_words(text: str) -> set:
    """Extract stemmed content words for semantic comparison."""
    words = re.sub(r"[^\w\s]", " ", (text or "").lower()).split()
    return {_crude_stem(w) for w in words if w not in _STOP_WORDS and len(w) > 1}


def _semantic_intent_overlap(cand_words: set, ex_words: set) -> float:
    """
    Intent overlap score for semantic duplicate detection.

    Uses min-denominator overlap when intent sets are similar in size (preserves
    short Easy paraphrases such as investment/investing). When one side is much
    shorter than the other, switches to Jaccard so a single shared topic noun
    (e.g. "currency") cannot mark a definition question as a duplicate of a
    longer, different-intent question (e.g. currency-symbol matching).
    """
    if not cand_words or not ex_words:
        return 0.0
    inter = cand_words & ex_words
    if not inter:
        return 0.0
    n_min = min(len(cand_words), len(ex_words))
    n_max = max(len(cand_words), len(ex_words))
    # Length-imbalance guard: short intent subset of a much longer stem
    if n_min <= 2 and n_max >= (2 * n_min + 1):
        return len(inter) / len(cand_words | ex_words)
    if n_min <= 4 and n_max >= (2 * n_min + 1) and len(inter) == n_min:
        # Full subset of a much longer intent → Jaccard (same topic ≠ same objective)
        return len(inter) / len(cand_words | ex_words)
    return len(inter) / n_min


def is_semantic_duplicate(
    candidate: Dict[str, Any],
    existing_questions: Sequence[Dict[str, Any]],
    intent_overlap_threshold: float = 0.75,
) -> bool:
    """
    Detect semantic duplicates by comparing (chapter, topic, question intent).

    Two questions are semantic duplicates when they share the same chapter AND
    their question stems test substantially the same intent (high content-word
    overlap after stop-word removal).

    Conservative: requires same chapter + high intent overlap to avoid
    over-rejecting questions that merely share a topic. Short-vs-long imbalance
    uses Jaccard so same-topic ≠ same question objective.
    """
    cand_chapter = candidate.get("chapter")
    cand_topic = (candidate.get("topic") or "").strip().lower()
    cand_words = _extract_intent_words(candidate.get("question", ""))
    if not cand_words:
        return False

    for existing in existing_questions:
        if existing.get("chapter") != cand_chapter:
            continue

        ex_topic = (existing.get("topic") or "").strip().lower()
        ex_words = _extract_intent_words(existing.get("question", ""))
        if not ex_words:
            continue

        topic_match = (
            cand_topic == ex_topic
            or (cand_topic and ex_topic and (
                cand_topic in ex_topic or ex_topic in cand_topic
            ))
        )
        if not topic_match:
            continue

        overlap = _semantic_intent_overlap(cand_words, ex_words)
        if overlap >= intent_overlap_threshold:
            return True

    return False


def evaluate_blind_solver(
    blind_solver: Optional[Dict[str, Any]],
    generated_correct_indices: Sequence[int],
    answer_type: str,
) -> List[str]:
    """Compare blind solver's independently derived answer with the generated key."""
    if blind_solver is None:
        return []

    errors: List[str] = []

    solver_indices = sorted(blind_solver.get("independently_derived_indices") or [])
    gen_indices = sorted(generated_correct_indices)

    if solver_indices != gen_indices:
        errors.append(
            f"independent solver disagrees with answer key: "
            f"solver={solver_indices}, generated={gen_indices}"
        )

    option_analysis = blind_solver.get("option_analysis") or []
    defensible_indices = []
    for entry in option_analysis:
        if isinstance(entry, dict) and entry.get("defensible"):
            label = (entry.get("option") or "").upper().strip()
            idx = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}.get(label)
            if idx is not None:
                defensible_indices.append(idx)
    defensible_indices = sorted(set(defensible_indices))

    if answer_type == "single_correct":
        if len(defensible_indices) > 1:
            labels = [chr(65 + i) for i in defensible_indices]
            errors.append(
                f"multiple defensible options in single_correct: {', '.join(labels)}"
            )
    elif answer_type == "multiple_correct":
        if defensible_indices and sorted(defensible_indices) != gen_indices:
            def_labels = [chr(65 + i) for i in defensible_indices]
            gen_labels = [chr(65 + i) for i in gen_indices]
            errors.append(
                f"defensible option set {def_labels} does not match "
                f"generated key {gen_labels}"
            )

    if not blind_solver.get("information_sufficient", True):
        errors.append("information insufficient: stem does not provide enough data to determine the answer")

    if not blind_solver.get("arithmetic_consistent", True):
        errors.append("arithmetic/numerical inconsistency detected in stem or options")

    if not blind_solver.get("no_unsupported_claims", True):
        errors.append("unsupported absolute/misleading claim not grounded in material")

    # Grade-appropriate terminology / grounding: specialized terms in the stem
    # must be present in the provided chapter excerpt.
    if not blind_solver.get("terminology_grounded", True):
        errors.append("grade-inappropriate/untaught terminology detected in stem")

    return errors


def _letters_from_indices(indices: Sequence[int]) -> str:
    labels = "ABCDE"
    out = [labels[i] for i in indices if 0 <= i < len(labels)]
    return ", ".join(out) if out else ""


def _validate_subjective_best_objective_criterion(question_text: str) -> List[str]:
    text = (question_text or "")
    if not _SUBJECTIVE_BEST_RE.search(text):
        return []
    if _OBJECTIVE_CRITERION_RE.search(text) is None:
        return ["subjective 'best' question lacks an explicit objective decision criterion"]
    return []


def _validate_distractor_plausibility(question: Dict[str, Any]) -> List[str]:
    """
    Deterministic heuristic to reject obviously off-topic/absurd distractors.

    We keep this conservative: it only runs when the stem/topic appears to
    involve financial concepts. Otherwise, unit-test placeholders won't be
    accidentally rejected.
    """
    options: List[str] = question.get("options") or []
    correct_indices: List[int] = list(question.get("correct_indices") or [])
    q_text = question.get("question") or ""
    topic = question.get("topic") or ""
    sub_topic = question.get("sub_topic") or ""

    combined = " ".join([q_text, topic, sub_topic])
    if not _FINANCIAL_CONTEXT_RE.search(combined):
        return []

    seed_words = _extract_intent_words(combined)
    if not seed_words:
        return []

    errors: List[str] = []
    irrelevant_labels: List[str] = []
    labels = "ABCDE"

    for idx, opt in enumerate(options):
        if idx in correct_indices:
            continue
        opt_text = opt or ""
        if _OFFTOPIC_INDICATORS_RE.search(opt_text):
            irrelevant_labels.append(labels[idx] if idx < len(labels) else str(idx))
            continue

        opt_words = _extract_intent_words(opt_text)
        if not opt_words:
            continue
        overlap = len(seed_words & opt_words) / max(1, len(opt_words))
        if overlap <= 0.01:
            irrelevant_labels.append(labels[idx] if idx < len(labels) else str(idx))

    if irrelevant_labels:
        errors.append(f"unclear/irrelevant distractor(s): {', '.join(sorted(set(irrelevant_labels)))}")
    return errors


def _validate_redundant_correct_options(question: Dict[str, Any]) -> List[str]:
    """Reject multiple_correct questions where correct options are near duplicates in meaning."""
    answer_type = question.get("answer_type")
    # If answer_type isn't provided on the question dict, fall back to correct_indices size.
    options: List[str] = question.get("options") or []
    correct_indices: List[int] = list(question.get("correct_indices") or [])
    if answer_type != "multiple_correct" and len(correct_indices) < 2:
        return []

    # Require explicit multiple_correct by the slot (question dict often doesn't carry answer_type).
    if len(correct_indices) < 2:
        return []

    errors: List[str] = []
    pairs_checked = 0
    for i in range(len(correct_indices)):
        for j in range(i + 1, len(correct_indices)):
            idx_i = correct_indices[i]
            idx_j = correct_indices[j]
            if idx_i >= len(options) or idx_j >= len(options):
                continue
            wi = _extract_intent_words(options[idx_i] or "")
            wj = _extract_intent_words(options[idx_j] or "")
            if not wi or not wj:
                continue
            overlap = len(wi & wj) / max(1, min(len(wi), len(wj)))
            pairs_checked += 1
            if overlap >= 0.85:
                li = chr(65 + idx_i) if 0 <= idx_i < 5 else str(idx_i)
                lj = chr(65 + idx_j) if 0 <= idx_j < 5 else str(idx_j)
                errors.append(f"redundant correct options: {li} and {lj} appear semantically overlapping")
                return errors

    # Avoid false negatives: if we couldn't compare pairs, do not fail.
    if pairs_checked == 0:
        return []
    return errors


def apply_independent_validation(
    *,
    slot: QuestionSlot,
    criterion_scores: Dict[str, Any],
    quality_flags: Dict[str, Any],
    question: Dict[str, Any],
    existing_question_texts: Sequence[str],
    existing_questions: Sequence[Dict[str, Any]] = (),
    book_grounded: bool,
    blind_solver: Optional[Dict[str, Any]] = None,
    content_aware_lexical: bool = False,
) -> Dict[str, Any]:
    """
    Combine independent criterion scores (summed in Python) with quality flags,
    blind-solver checks, semantic duplicate detection, and topic metadata validation.

    Validator must not be told target_difficulty; comparison happens here.
    content_aware_lexical: Bank Batch only — ignore MCQ scaffold words in lexical gate.
    """
    reasons: List[str] = []
    scores, score_errors = clamp_criterion_scores(criterion_scores)
    reasons.extend(score_errors)
    total = cognitive_total(scores)
    validated = map_cognitive_score(total)
    target = normalize_difficulty(slot.target_difficulty)

    # --- Cognitive difficulty check (separate from quality) ---
    if validated != target:
        reasons.append(
            f"cognitive difficulty mismatch: target={target}, validated={validated} (score={total})"
        )

    # --- Answer-type structural checks ---
    option_count = len(question.get("options") or [])
    reasons.extend(
        evaluate_answer_type(
            slot.answer_type,
            question.get("correct_indices") or [],
            option_count,
        )
    )

    # --- Deterministic numerical equivalence ---
    reasons.extend(
        check_numerical_equivalence(
            question.get("options") or [],
            question.get("correct_indices") or [],
            slot.answer_type,
        )
    )

    # --- Blind solver: independent answer, option defensibility, info sufficiency,
    #     arithmetic consistency, unsupported claims ---
    reasons.extend(
        evaluate_blind_solver(
            blind_solver,
            question.get("correct_indices") or [],
            slot.answer_type,
        )
    )

    # --- LLM quality flags ---
    required_flags = {
        "content_valid": "content validity failed",
        "answer_valid": "answer validity failed",
        "grade_appropriate": "not appropriate for the selected grade",
        "unambiguous": "question is ambiguous",
        "language_clear": "language is unclear",
        "explanation_valid": "explanation is invalid",
        "distractors_ok": "distractor quality failed",
    }
    for key, message in required_flags.items():
        if not quality_flags.get(key, False):
            reasons.append(message)

    if book_grounded and not quality_flags.get("grounded_in_material", False):
        reasons.append("not grounded in the supplied chapter content (possible hallucination)")

    # --- Lexical duplicate ---
    if is_near_duplicate(
        question.get("question", ""),
        existing_question_texts,
        content_aware=content_aware_lexical,
    ):
        reasons.append("duplicate or near-duplicate of an approved question")

    # --- Semantic duplicate ---
    candidate_record = {
        "chapter": slot.chapter,
        "topic": question.get("topic", ""),
        "question": question.get("question", ""),
    }
    if is_semantic_duplicate(candidate_record, existing_questions):
        reasons.append("semantic duplicate: tests the same concept/intent as an accepted question")

    # --- Topic metadata quality ---
    reasons.extend(
        validate_topic_metadata(
            question.get("topic", ""),
            question.get("sub_topic", ""),
            slot.chapter_title,
            subject=slot.subject,
        )
    )

    # --- Subjective "best/smart" objective-criterion validation ---
    reasons.extend(_validate_subjective_best_objective_criterion(question.get("question", "")))

    # --- Distractor quality (deterministic heuristic) ---
    reasons.extend(_validate_distractor_plausibility(question))

    # --- Redundant Multiple Correct options (semantic overlap heuristic) ---
    if slot.answer_type == "multiple_correct":
        reasons.extend(_validate_redundant_correct_options(question))

    extra_reasons = quality_flags.get("reasons") or []
    if isinstance(extra_reasons, list):
        extra = [str(r) for r in extra_reasons if r]
    else:
        extra = []

    passed = len(reasons) == 0
    if not passed:
        reasons.extend(extra)
    status = "passed" if passed else "rejected"
    return {
        "passed": passed,
        "validation_status": status,
        "validation_reasons": reasons,
        "difficulty_scores": scores,
        "difficulty_score": total,
        "validated_cognitive_difficulty": validated,
        "target_difficulty": target,
        # Persist structured, concise blind-solver / quality flags so we can
        # audit why a question passed or failed.
        "blind_solver_answer": (
            _letters_from_indices(blind_solver.get("independently_derived_indices") or [])
            if blind_solver
            else "N/A (not persisted)"
        ),
        "answer_agreement": (
            set(blind_solver.get("independently_derived_indices") or [])
            == set(question.get("correct_indices") or [])
        )
        if blind_solver
        else "N/A (not persisted)",
        "information_sufficient": (
            bool(blind_solver.get("information_sufficient"))
            if blind_solver and "information_sufficient" in blind_solver
            else "N/A (not persisted)"
        ),
        "arithmetic_consistent": (
            bool(blind_solver.get("arithmetic_consistent"))
            if blind_solver and "arithmetic_consistent" in blind_solver
            else "N/A (not persisted)"
        ),
        "no_unsupported_claims": (
            bool(blind_solver.get("no_unsupported_claims"))
            if blind_solver and "no_unsupported_claims" in blind_solver
            else "N/A (not persisted)"
        ),
        "option_defensibility": (
            blind_solver.get("option_analysis") if blind_solver else "N/A (not persisted)"
        ),
        "distractors_ok": quality_flags.get("distractors_ok", "N/A (not persisted)"),
        "terminology_grounded": (
            bool(blind_solver.get("terminology_grounded"))
            if blind_solver and "terminology_grounded" in blind_solver
            else "N/A (not persisted)"
        ),
    }


def build_slots(
    preset: Optional[Dict[str, Any]] = None,
    *,
    grade: str = "",
    subject: str = "",
    chapter_titles: Optional[Sequence[str]] = None,
) -> List[QuestionSlot]:
    """
    Expand Chapter×Difficulty and Difficulty×Answer Type matrices into ordered slots.

    chapter_titles, if provided, must match the matrix row count exactly.
    Omit titles for topic-only generation (synthetic chapter labels).
    """
    preset = build_effective_preset(preset, chapter_titles)
    titles = list(preset.get("chapter_titles") or [])
    matrix = preset["chapter_difficulty"]
    if not titles:
        titles = [f"Chapter {k}" for k in sorted(matrix.keys(), key=int)]

    # Expand (chapter, difficulty) pairs in chapter order, easy→medium→difficult within chapter.
    pairs: List[Tuple[int, str, str]] = []
    for chap_key in sorted(matrix.keys(), key=int):
        chap_num = int(chap_key)
        title = titles[chap_num - 1] if 0 <= chap_num - 1 < len(titles) else f"Chapter {chap_num}"
        for difficulty in DIFFICULTIES:
            for _ in range(int(matrix[chap_key].get(difficulty, 0))):
                pairs.append((chap_num, title, difficulty))

    # Assign answer types per difficulty, spreading multiple-correct evenly.
    answer_types: List[str] = [""] * len(pairs)
    for difficulty, counts in preset["difficulty_answer_types"].items():
        indices = [i for i, p in enumerate(pairs) if p[2] == difficulty]
        n_multi = int(counts.get("multiple_correct", 0))
        n_single = int(counts.get("single_correct", 0))
        if len(indices) != n_multi + n_single:
            raise ValueError(
                f"Difficulty {difficulty}: {len(indices)} chapter slots != "
                f"{n_single} single + {n_multi} multiple"
            )
        multi_set = set(_spread_indices(len(indices), n_multi))
        for local_i, global_i in enumerate(indices):
            answer_types[global_i] = (
                "multiple_correct" if local_i in multi_set else "single_correct"
            )

    slots: List[QuestionSlot] = []
    for i, ((chap_num, title, difficulty), answer_type) in enumerate(
        zip(pairs, answer_types), start=1
    ):
        slots.append(
            QuestionSlot(
                question_number=i,
                chapter=chap_num,
                chapter_title=title,
                target_difficulty=difficulty,
                answer_type=answer_type,
                grade=grade or "",
                subject=subject or "",
            )
        )
    return slots


def chunk_chapter_text(text: str) -> List[str]:
    """Split a chapter so later portions can be selected independently of the start."""
    if not text or not text.strip():
        return []
    if len(text) <= CHAPTER_CHUNK_SIZE:
        return [text]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHAPTER_CHUNK_SIZE,
        chunk_overlap=CHAPTER_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = [c.strip() for c in splitter.split_text(text) if c.strip()]
    return chunks or [text[:CHAPTER_CHUNK_SIZE]]


def select_chapter_chunk(
    chunks: Sequence[str],
    slot_index_zero_based: int,
    attempt: int,
) -> str:
    """Rotate through chapter chunks so later content is eligible."""
    if not chunks:
        return ""
    idx = (slot_index_zero_based + max(attempt, 1) - 1) % len(chunks)
    return chunks[idx]


def normalize_question_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


# MCQ scaffold words that inflate lexical overlap across different intents
# (Bank Batch content-aware lexical mode only). Exact-normalized match still wins.
_MCQ_LEXICAL_SCAFFOLD = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "to",
        "in",
        "on",
        "for",
        "as",
        "at",
        "by",
        "or",
        "and",
        "is",
        "are",
        "was",
        "were",
        "be",
        "being",
        "been",
        "which",
        "what",
        "who",
        "whom",
        "whose",
        "when",
        "where",
        "why",
        "how",
        "following",
        "example",
        "examples",
        "select",
        "all",
        "that",
        "apply",
        "more",
        "than",
        "one",
        "answer",
        "answers",
        "may",
        "correct",
        "statements",
        "statement",
        "about",
        "true",
        "best",
        "main",
        "used",
        "using",
        "use",
        "does",
        "do",
        "did",
        "can",
        "could",
        "would",
        "should",
        "with",
        "from",
        "into",
        "over",
        "under",
        "between",
        "among",
        "each",
        "other",
        "their",
        "its",
        "this",
        "these",
        "those",
        "such",
    }
)


def _lexical_word_set(text: str, *, content_aware: bool) -> set:
    words = normalize_question_text(text).split()[:16]
    if not content_aware:
        return set(words)
    content = {w.strip(".,;:()[]\"'?!") for w in words}
    content = {w for w in content if w and w not in _MCQ_LEXICAL_SCAFFOLD}
    # Light geo/demonym normalization so "Indian"/"India" paraphrases still match
    aliases = {"indian": "india", "indias": "india"}
    return {aliases.get(w, w) for w in content}


def is_near_duplicate(
    candidate: str,
    existing: Iterable[str],
    min_overlap: float = 0.7,
    *,
    content_aware: bool = False,
) -> bool:
    """
    Lexical near-duplicate detection based on word overlap of the first 16 words.

    When content_aware=True (Bank Batch), MCQ scaffold words are ignored so shared
    templates like "Which of the following is an example of…" do not alone cause
    rejection across different learning objectives. Exact normalized matches still
    reject. Final Paper keeps content_aware=False (legacy behavior).

    LIMITATION: This is purely lexical — it catches re-worded or identical stems
    but does NOT detect semantically equivalent questions that use different
    vocabulary.
    """
    cand_norm = normalize_question_text(candidate)
    if not cand_norm:
        return False
    cand_set = _lexical_word_set(candidate, content_aware=content_aware)
    # Content-aware mode strips scaffolds, so allow a slightly lower ratio while
    # still requiring substantial content-word overlap (exact match always rejects).
    effective_min = 0.5 if content_aware else min_overlap
    for other in existing:
        other_norm = normalize_question_text(other)
        if not other_norm:
            continue
        if cand_norm == other_norm:
            return True
        other_set = _lexical_word_set(other, content_aware=content_aware)
        if content_aware and (len(cand_set) < 2 or len(other_set) < 2):
            # Too little content after scaffold removal — only exact match counts
            continue
        if not cand_set or not other_set:
            continue
        overlap = len(cand_set & other_set) / max(len(cand_set), 1)
        if overlap >= effective_min:
            return True
    return False


def _try_parse_number(text: str) -> Optional[float]:
    """
    Attempt to evaluate a simple numerical expression to a float.

    Handles: integers, decimals, percentages, simple fractions (a/b),
    simple arithmetic (+, -, *, /). Returns None if parsing is unsafe
    or the expression is non-numerical.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    # Strip leading option labels like "A. " or "(a) "
    cleaned = re.sub(r"^[A-Ea-e][.)]\s*", "", cleaned).strip()
    if not cleaned:
        return None

    # Percentage: "70%" -> 70
    pct_match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*%", cleaned)
    if pct_match:
        try:
            return float(pct_match.group(1))
        except ValueError:
            return None

    # Simple fraction: "7/18"
    frac_match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*/\s*([+-]?\d+(?:\.\d+)?)", cleaned)
    if frac_match:
        try:
            num = float(frac_match.group(1))
            den = float(frac_match.group(2))
            if den == 0:
                return None
            return num / den
        except (ValueError, ZeroDivisionError):
            return None

    # Integer or decimal
    num_match = re.fullmatch(r"[+-]?\d+(?:\.\d+)?", cleaned)
    if num_match:
        try:
            return float(cleaned)
        except ValueError:
            return None

    # Simple arithmetic: only digits, +, -, *, /, ., spaces, parens
    if re.fullmatch(r"[0-9+\-*/.()\s]+", cleaned):
        try:
            result = eval(cleaned, {"__builtins__": {}}, {})  # noqa: S307
            if isinstance(result, (int, float)) and not isinstance(result, bool):
                return float(result)
        except Exception:
            return None

    return None


def check_numerical_equivalence(
    options: Sequence[str],
    correct_indices: Sequence[int],
    answer_type: str,
    tolerance: float = 1e-9,
) -> List[str]:
    """
    For single_correct questions with parseable numerical options, check if
    any non-correct option is mathematically equivalent to the correct answer.

    Returns list of error strings (empty = ok).
    Falls back silently (returns []) if options are not simple numbers.
    """
    if answer_type != "single_correct":
        return []
    if len(correct_indices) != 1:
        return []

    correct_idx = correct_indices[0]
    if correct_idx < 0 or correct_idx >= len(options):
        return []

    correct_val = _try_parse_number(options[correct_idx])
    if correct_val is None:
        return []

    errors: List[str] = []
    for i, opt in enumerate(options):
        if i == correct_idx:
            continue
        val = _try_parse_number(opt)
        if val is not None and abs(val - correct_val) < tolerance:
            errors.append(
                f"option {OPTION_LABELS[i] if i < len(OPTION_LABELS) else str(i)} "
                f"('{opt.strip()}') is mathematically equivalent to the correct answer "
                f"('{options[correct_idx].strip()}')"
            )
    return errors


OPTION_LABELS = ("A", "B", "C", "D", "E")


def _count_matrix(questions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    chapter_difficulty: Dict[str, Dict[str, int]] = {}
    difficulty_totals = {d: 0 for d in DIFFICULTIES}
    answer_type_totals = {a: 0 for a in ANSWER_TYPES}
    difficulty_answer: Dict[str, Dict[str, int]] = {
        d: {a: 0 for a in ANSWER_TYPES} for d in DIFFICULTIES
    }
    for q in questions:
        chap = str(q.get("chapter") or q.get("blueprint_chapter") or "")
        diff = normalize_difficulty(q.get("validated_cognitive_difficulty") or q.get("target_difficulty"))
        atype = q.get("answer_type") or "single_correct"
        chapter_difficulty.setdefault(chap, {d: 0 for d in DIFFICULTIES})
        if chap:
            chapter_difficulty[chap][diff] = chapter_difficulty[chap].get(diff, 0) + 1
        difficulty_totals[diff] = difficulty_totals.get(diff, 0) + 1
        if atype in answer_type_totals:
            answer_type_totals[atype] += 1
        if diff in difficulty_answer and atype in difficulty_answer[diff]:
            difficulty_answer[diff][atype] += 1
    return {
        "chapter_difficulty": chapter_difficulty,
        "difficulty_totals": difficulty_totals,
        "answer_type_totals": answer_type_totals,
        "difficulty_answer": difficulty_answer,
    }


def audit_paper(
    questions: Sequence[Dict[str, Any]],
    preset: Optional[Dict[str, Any]] = None,
    *,
    options_per_question: int = 5,
    require_validated: bool = True,
) -> Dict[str, Any]:
    """
    Deterministic numeric audit. Does not call an LLM.

    Uses validated_cognitive_difficulty (not target) for difficulty totals so a
    mislabelled Medium cannot be counted as Difficult.
    """
    preset = preset_from_dict(preset)
    errors: List[str] = []
    expected_total = int(preset["total_questions"])
    if len(questions) != expected_total:
        errors.append(f"Total questions={len(questions)}, expected {expected_total}")

    expected_diff = {
        d: sum(int(ch.get(d, 0)) for ch in preset["chapter_difficulty"].values())
        for d in DIFFICULTIES
    }
    expected_atypes = {a: 0 for a in ANSWER_TYPES}
    for d, counts in preset["difficulty_answer_types"].items():
        for a in ANSWER_TYPES:
            expected_atypes[a] += int(counts.get(a, 0))

    seen_text: List[str] = []
    for i, q in enumerate(questions, start=1):
        options = q.get("options") or []
        if len(options) != options_per_question:
            errors.append(f"Q{i}: expected {options_per_question} options, got {len(options)}")
        if not (q.get("explanation") or "").strip():
            errors.append(f"Q{i}: missing explanation")
        if not (q.get("question") or "").strip():
            errors.append(f"Q{i}: missing question text")
        indices = q.get("correct_indices") or []
        atype = q.get("answer_type")
        if atype == "single_correct" and len(indices) != 1:
            errors.append(f"Q{i}: single_correct requires exactly one correct answer")
        if atype == "multiple_correct" and len(indices) < 2:
            errors.append(f"Q{i}: multiple_correct requires more than one correct answer")
        if require_validated:
            if q.get("validation_status") != "passed":
                errors.append(f"Q{i}: did not pass independent validation")
            target = normalize_difficulty(q.get("target_difficulty"))
            validated = normalize_difficulty(q.get("validated_cognitive_difficulty"))
            if target != validated:
                errors.append(
                    f"Q{i}: target {target} != validated {validated}"
                )
        text = q.get("question", "")
        if is_near_duplicate(text, seen_text):
            errors.append(f"Q{i}: duplicate/near-duplicate of an earlier question")
        seen_text.append(text)

    actual = _count_matrix(questions)

    for d in DIFFICULTIES:
        got = actual["difficulty_totals"].get(d, 0)
        exp = expected_diff.get(d, 0)
        if got != exp:
            errors.append(f"Difficulty {d}: {got}, expected {exp}")

    for a in ANSWER_TYPES:
        got = actual["answer_type_totals"].get(a, 0)
        exp = expected_atypes.get(a, 0)
        if got != exp:
            errors.append(f"Answer type {a}: {got}, expected {exp}")

    expected_cd = {
        str(k): {dd: int(vv.get(dd, 0)) for dd in DIFFICULTIES}
        for k, vv in preset["chapter_difficulty"].items()
    }
    # If chapters were merged, compare against merged matrix using actual chapter keys.
    if set(actual["chapter_difficulty"].keys()) != set(expected_cd.keys()):
        # Allow merge: compare totals per available chapter only when keys match 1..n
        pass
    for chap, expected_counts in expected_cd.items():
        got_counts = actual["chapter_difficulty"].get(chap, {d: 0 for d in DIFFICULTIES})
        total_got = sum(got_counts.get(d, 0) for d in DIFFICULTIES)
        total_exp = sum(expected_counts.values())
        if total_got != total_exp:
            errors.append(f"Chapter {chap} total={total_got}, expected {total_exp}")
        for d in DIFFICULTIES:
            if got_counts.get(d, 0) != expected_counts[d]:
                errors.append(
                    f"Chapter {chap} {d}={got_counts.get(d, 0)}, expected {expected_counts[d]}"
                )

    for d, counts in preset["difficulty_answer_types"].items():
        for a in ANSWER_TYPES:
            got = actual["difficulty_answer"].get(d, {}).get(a, 0)
            exp = int(counts.get(a, 0))
            if got != exp:
                errors.append(f"{d} {a}={got}, expected {exp}")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "actual": actual,
        "expected_total": expected_total,
    }


# ---------------------------------------------------------------------------
# Question Bank Batch (single chapter × single difficulty pool)
# ---------------------------------------------------------------------------


def is_bank_diversity_planner_enabled() -> bool:
    """Feature flag for Step 2 diversity planner. Default OFF (Step 1 path)."""
    import os

    raw = (os.environ.get("QUESTION_BANK_DIVERSITY_PLANNER") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def intent_fingerprint(question: str) -> str:
    """Stable compact fingerprint of question intent (sorted content stems)."""
    return " ".join(sorted(_extract_intent_words(question)))


def load_bank_duplicate_seed_snapshot() -> Optional[List[Dict[str, Any]]]:
    """
    Optional fixed seed snapshot for controlled Bank Batch benchmarks.

    Set QUESTION_BANK_SEED_SNAPSHOT_FILE to a JSON list of seed question dicts
    (id, question, topic, sub_topic, chapter, ...). Default: None (live DB seeds).
    """
    import os

    path = (os.environ.get("QUESTION_BANK_SEED_SNAPSHOT_FILE") or "").strip()
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("seeds"), list):
            return data["seeds"]
    except Exception:
        return None
    return None


# Bank Batch prompt-size caps (Final Paper still sends the full chapter chunk).
BANK_BATCH_VALIDATOR_GROUNDING_MIN = 800
BANK_BATCH_VALIDATOR_GROUNDING_MAX = 1500
BANK_BATCH_BLIND_SNIPPET_MAX = 700
BANK_BATCH_FORBIDDEN_STEM_LIMIT = 10


def select_source_grounding_window(
    text: str,
    probe: str,
    *,
    min_chars: int = BANK_BATCH_VALIDATOR_GROUNDING_MIN,
    max_chars: int = BANK_BATCH_VALIDATOR_GROUNDING_MAX,
) -> str:
    """Pick an 800–1500 character window of ``text`` nearest to ``probe`` terms."""
    raw = (text or "").strip()
    if not raw:
        return ""
    max_chars = max(1, min(int(max_chars), BANK_BATCH_VALIDATOR_GROUNDING_MAX))
    min_chars = max(1, min(int(min_chars), max_chars))
    if len(raw) <= max_chars:
        return raw
    words = [w for w in _extract_intent_words(probe) if len(w) >= 4]
    best_i = 0
    best_hits = -1
    step = max(80, max_chars // 8)
    last = max(0, len(raw) - max_chars)
    for i in range(0, last + 1, step):
        window = raw[i : i + max_chars].lower()
        hits = sum(1 for w in words if w in window)
        if hits > best_hits:
            best_hits = hits
            best_i = i
    if best_hits <= 0:
        low = raw.lower()
        for w in words:
            pos = low.find(w)
            if pos >= 0:
                start = max(0, pos - max_chars // 4)
                return raw[start : start + max_chars]
        return raw[:max_chars]
    chunk = raw[best_i : best_i + max_chars]
    if len(chunk) < min_chars:
        start = max(0, best_i - (min_chars - len(chunk)))
        chunk = raw[start : start + max_chars]
    return chunk


def select_blind_solver_source_snippet(
    text: str,
    stem: str,
    options: Optional[Sequence[str]] = None,
    *,
    max_chars: int = BANK_BATCH_BLIND_SNIPPET_MAX,
) -> str:
    """Small terminology snippet, or empty when the stem is self-contained."""
    raw = (text or "").strip()
    if not raw:
        return ""
    opt_text = " ".join(str(o) for o in (options or []) if str(o).strip())
    probe = f"{stem or ''} {opt_text}".strip()
    words = [w for w in _extract_intent_words(probe) if len(w) >= 5]
    low = raw.lower()
    hits = [w for w in words if w in low]
    if not hits:
        return ""
    cap = max(200, min(int(max_chars), BANK_BATCH_BLIND_SNIPPET_MAX))
    return select_source_grounding_window(
        raw,
        " ".join(hits),
        min_chars=min(400, cap),
        max_chars=cap,
    )


def select_bank_batch_forbidden_stems(
    assigned_intent: Optional[Dict[str, Any]],
    *,
    used_stems: Sequence[str] = (),
    rejected_stems: Sequence[str] = (),
    existing_questions: Sequence[Any] = (),
    limit: int = BANK_BATCH_FORBIDDEN_STEM_LIMIT,
) -> List[str]:
    """8–12 closest opening stems for Bank Batch generation (soft avoid only)."""
    n = max(8, min(12, int(limit or BANK_BATCH_FORBIDDEN_STEM_LIMIT)))
    ordered: List[str] = []
    seen = set()

    def _add(raw: Any) -> None:
        stem = " ".join(str(raw or "").split())
        if not stem:
            return
        key = stem.lower()
        if key in seen:
            return
        seen.add(key)
        ordered.append(stem)

    for s in used_stems or []:
        _add(s)
    for s in rejected_stems or []:
        _add(s)
    for q in existing_questions or []:
        if isinstance(q, dict):
            _add(q.get("question"))
        else:
            _add(q)
    if not ordered:
        return []
    if not isinstance(assigned_intent, dict):
        return ordered[-n:]
    probe = _extract_intent_words(
        " ".join(
            str(assigned_intent.get(k) or "")
            for k in ("concept", "objective", "topic", "sub_topic")
        )
    )
    if not probe:
        return ordered[-n:]
    scored = []
    for stem in ordered:
        ov = _semantic_intent_overlap(probe, _extract_intent_words(stem))
        scored.append((ov, stem))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [s for ov, s in scored if ov > 0][:n]
    if len(picked) < 8:
        for stem in reversed(ordered):
            if stem not in picked:
                picked.append(stem)
            if len(picked) >= min(8, n):
                break
    return picked[:n]


def find_lexical_duplicate_match(
    candidate: str,
    existing_questions: Sequence[Dict[str, Any]],
    *,
    min_overlap: float = 0.7,
    content_aware: bool = False,
) -> Optional[Dict[str, Any]]:
    """Return the best lexical near-duplicate match metadata, if any."""
    cand_norm = normalize_question_text(candidate)
    if not cand_norm:
        return None
    cand_set = _lexical_word_set(candidate, content_aware=content_aware)
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0
    best_exact = False
    effective_min = 0.5 if content_aware else min_overlap
    for ex in existing_questions:
        other = ex.get("question") or ""
        other_norm = normalize_question_text(other)
        if not other_norm:
            continue
        if cand_norm == other_norm:
            best = ex
            best_score = 1.0
            best_exact = True
            break
        other_set = _lexical_word_set(other, content_aware=content_aware)
        if content_aware and (len(cand_set) < 2 or len(other_set) < 2):
            continue
        if not cand_set or not other_set:
            continue
        score = len(cand_set & other_set) / max(len(cand_set), 1)
        if score >= effective_min and score > best_score:
            best = ex
            best_score = score
    if not best:
        return None
    return {
        "matched_question_id": str(best.get("id") or "") or None,
        "matched_stem": best.get("question") or "",
        "matched_topic": best.get("topic") or "",
        "matched_sub_topic": best.get("sub_topic") or "",
        "matched_intent_fingerprint": intent_fingerprint(best.get("question") or ""),
        "duplicate_type": "exact" if best_exact else "lexical",
        "overlap_score": round(best_score, 3),
    }


def find_semantic_duplicate_match(
    candidate: Dict[str, Any],
    existing_questions: Sequence[Dict[str, Any]],
    *,
    intent_overlap_threshold: float = 0.75,
) -> Optional[Dict[str, Any]]:
    """Return the best semantic-duplicate match metadata, if any."""
    cand_chapter = candidate.get("chapter")
    cand_topic = (candidate.get("topic") or "").strip().lower()
    cand_words = _extract_intent_words(candidate.get("question", ""))
    if not cand_words:
        return None
    best: Optional[Dict[str, Any]] = None
    best_overlap = 0.0
    for existing in existing_questions:
        if existing.get("chapter") != cand_chapter:
            continue
        ex_topic = (existing.get("topic") or "").strip().lower()
        topic_match = cand_topic == ex_topic or (
            cand_topic
            and ex_topic
            and (cand_topic in ex_topic or ex_topic in cand_topic)
        )
        if not topic_match:
            continue
        ex_words = _extract_intent_words(existing.get("question", ""))
        if not ex_words:
            continue
        overlap = _semantic_intent_overlap(cand_words, ex_words)
        if overlap >= intent_overlap_threshold and overlap > best_overlap:
            best = existing
            best_overlap = overlap
    if not best:
        return None
    return {
        "matched_question_id": str(best.get("id") or "") or None,
        "matched_stem": best.get("question") or "",
        "matched_topic": best.get("topic") or "",
        "matched_sub_topic": best.get("sub_topic") or "",
        "matched_intent_fingerprint": intent_fingerprint(best.get("question") or ""),
        "duplicate_type": "semantic",
        "overlap_score": round(best_overlap, 3),
    }


BANK_BATCH_DUPLICATE_RETRY_CORE = (
    "Do not paraphrase this question. Test a different learning objective, skill, "
    "relationship, application, or question intent from the same chapter while "
    "preserving the requested difficulty and answer type."
)


def format_bank_batch_duplicate_retry_guidance(
    match: Optional[Dict[str, Any]] = None,
) -> str:
    """Bank Batch-only retry guidance after lexical/semantic duplicate rejection."""
    parts = [BANK_BATCH_DUPLICATE_RETRY_CORE]
    if match:
        avoid_bits = []
        topic = (match.get("matched_topic") or "").strip()
        intent = (match.get("matched_intent_fingerprint") or "").strip()
        if topic:
            avoid_bits.append(f"topic={topic}")
        if intent:
            avoid_bits.append(f"intent={intent}")
        if avoid_bits:
            parts.append("Avoid: " + "; ".join(avoid_bits))
        parts.append(
            "Prefer a different eligible skill/concept from this chapter "
            "(still obey difficulty and answer type)."
        )
    else:
        parts.append(
            "Prefer a different eligible skill/concept from this chapter "
            "(still obey difficulty and answer type)."
        )
    return " ".join(parts)


def format_underused_concept_hints(
    usage_questions: Sequence[Dict[str, Any]],
    catalog: Optional[Dict[str, Any]] = None,
    *,
    max_prefer: int = 5,
) -> str:
    """
    Soft Bank Batch coverage hints (not the Step 2 diversity planner).

    Prefers underused topics/sub-topics/sections/LOs from existing bank metadata
    + chapter catalog. No rigid quotas.
    """
    topic_counts: Dict[str, int] = {}
    sub_counts: Dict[str, int] = {}
    for q in usage_questions:
        t = (q.get("topic") or "").strip()
        s = (q.get("sub_topic") or "").strip()
        if t:
            topic_counts[t] = topic_counts.get(t, 0) + 1
        if s:
            sub_counts[s] = sub_counts.get(s, 0) + 1

    catalog = catalog or {}
    sections = [str(x).strip() for x in (catalog.get("sections") or []) if str(x).strip()]
    los = [
        str(x).strip()
        for x in (catalog.get("learning_outcomes") or [])
        if str(x).strip()
    ]

    # Underused = present in catalog or seen once at most; heavily used = count >= 3
    heavy_topics = {t for t, c in topic_counts.items() if c >= 3}
    heavy_subs = {s for s, c in sub_counts.items() if c >= 3}

    prefer: List[str] = []
    for lo in los:
        if not any(lo.lower() in h.lower() or h.lower() in lo.lower() for h in heavy_topics):
            prefer.append(lo)
        if len(prefer) >= max_prefer:
            break
    for sec in sections:
        if len(prefer) >= max_prefer:
            break
        # Prefer sections whose label isn't already a heavy topic/sub
        if any(sec.lower() in h.lower() or h.lower() in sec.lower() for h in heavy_topics | heavy_subs):
            continue
        prefer.append(sec)

    # Also surface lightly used topics already in bank
    light_topics = sorted(
        (t for t, c in topic_counts.items() if 0 < c < 3 and t not in heavy_topics),
        key=lambda t: topic_counts.get(t, 0),
    )
    for t in light_topics:
        if len(prefer) >= max_prefer:
            break
        if t not in prefer:
            prefer.append(t)

    if not prefer and not heavy_topics:
        return ""

    avoid = sorted(heavy_topics)[:5]
    lines = [
        "\nSOFT COVERAGE HINTS (Bank Batch — preferences only; do not violate "
        "difficulty, answer type, or quality rules):",
    ]
    if prefer:
        lines.append("- Prefer underused concepts/sections when eligible: " + "; ".join(prefer[:max_prefer]))
    if avoid:
        lines.append("- Softly avoid repeating heavily used topics: " + ", ".join(avoid))
    lines.append(
        "- Still derive topic/sub_topic from the chapter excerpt; do not invent off-chapter content."
    )
    return "\n".join(lines) + "\n"


def build_rejected_attempt_record(
    *,
    slot: Any,
    attempt: int,
    generated: Optional[Dict[str, Any]],
    rejection_reasons: Sequence[str],
    rewrite_instruction: str,
    duplicate_match: Optional[Dict[str, Any]] = None,
    source_chunk_index: Optional[int] = None,
    phase: str = "fill",
) -> Dict[str, Any]:
    """Structured Bank Batch rejection metadata (no chain-of-thought)."""
    gen = generated or {}
    reasons = [str(r) for r in rejection_reasons if str(r).strip()]
    record: Dict[str, Any] = {
        "question_number": getattr(slot, "question_number", None),
        "attempt": attempt,
        "phase": phase,
        "question": gen.get("question") or "",
        "topic": gen.get("topic") or "",
        "sub_topic": gen.get("sub_topic") or "",
        "target_difficulty": getattr(slot, "target_difficulty", None),
        "answer_type": getattr(slot, "answer_type", None),
        "rejection_reasons": reasons,
        "rewrite_instruction": rewrite_instruction,
        "intent_fingerprint": intent_fingerprint(gen.get("question") or ""),
        "source_chunk_index": source_chunk_index,
        "chapter": getattr(slot, "chapter", None),
    }
    if duplicate_match:
        record["duplicate_type"] = duplicate_match.get("duplicate_type")
        record["matched_question_id"] = duplicate_match.get("matched_question_id")
        record["matched_stem"] = duplicate_match.get("matched_stem")
        record["matched_intent_fingerprint"] = duplicate_match.get(
            "matched_intent_fingerprint"
        )
        record["matched_topic"] = duplicate_match.get("matched_topic")
        record["matched_sub_topic"] = duplicate_match.get("matched_sub_topic")
    return record


def compute_bank_batch_saturation_diagnostics(
    *,
    seed_questions: Sequence[Dict[str, Any]],
    approved: Sequence[Dict[str, Any]],
    rejected_attempts: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Diagnostic coverage/saturation fields for Bank Batch results (not UI-critical)."""
    seeds = list(seed_questions or [])
    accepted = list(approved or [])
    rejected = list(rejected_attempts or [])

    def _topics(qs: Sequence[Dict[str, Any]]) -> List[str]:
        return [str(q.get("topic") or "").strip() for q in qs if str(q.get("topic") or "").strip()]

    def _subs(qs: Sequence[Dict[str, Any]]) -> List[str]:
        return [
            str(q.get("sub_topic") or "").strip()
            for q in qs
            if str(q.get("sub_topic") or "").strip()
        ]

    def _intents(qs: Sequence[Dict[str, Any]]) -> List[str]:
        out = []
        for q in qs:
            fp = q.get("intent_fingerprint") or intent_fingerprint(q.get("question") or "")
            if fp:
                out.append(fp)
        return out

    all_for_topics = seeds + accepted
    topic_counts: Dict[str, int] = {}
    for t in _topics(all_for_topics):
        topic_counts[t] = topic_counts.get(t, 0) + 1
    most_repeated = sorted(topic_counts.items(), key=lambda x: (-x[1], x[0]))[:8]

    dup_rejects = [
        r
        for r in rejected
        if (r.get("duplicate_type") or "")
        or any("duplicate" in str(x).lower() for x in (r.get("rejection_reasons") or []))
    ]
    lexical_dup = sum(
        1
        for r in dup_rejects
        if (r.get("duplicate_type") or "") in ("lexical", "exact")
        or any(
            "near-duplicate" in str(x).lower() or "duplicate or near-duplicate" in str(x).lower()
            for x in (r.get("rejection_reasons") or [])
        )
    )
    semantic_dup = sum(
        1
        for r in dup_rejects
        if (r.get("duplicate_type") or "") == "semantic"
        or any("semantic duplicate" in str(x).lower() for x in (r.get("rejection_reasons") or []))
    )

    # Retries that changed intent vs previous reject on same slot
    by_slot: Dict[Any, List[Dict[str, Any]]] = {}
    for r in rejected:
        by_slot.setdefault(r.get("question_number"), []).append(r)
    intent_changes = 0
    for _qn, items in by_slot.items():
        ordered = sorted(
            items,
            key=lambda x: (0 if x.get("phase") == "fill" else 100, int(x.get("attempt") or 0)),
        )
        prev_fp = None
        for item in ordered:
            fp = item.get("intent_fingerprint") or intent_fingerprint(item.get("question") or "")
            if prev_fp and fp and fp != prev_fp:
                intent_changes += 1
            if fp:
                prev_fp = fp

    return {
        "existing_seed_count": len(seeds),
        "accepted_new_count": len(accepted),
        "duplicate_rejection_count": len(dup_rejects),
        "lexical_duplicate_rejection_count": lexical_dup,
        "semantic_duplicate_rejection_count": semantic_dup,
        "unique_topic_count": len(set(_topics(all_for_topics))),
        "unique_sub_topic_count": len(set(_subs(all_for_topics))),
        "unique_intent_count": len(set(_intents(all_for_topics))),
        "most_repeated_topics": [
            {"topic": t, "count": c} for t, c in most_repeated
        ],
        "retries_that_changed_intent": intent_changes,
        "rejected_attempt_count": len(rejected),
    }


# ---------------------------------------------------------------------------
# Bank Batch Step 4 — target-driven, strategy-aware refill (Bank Batch only)
# ---------------------------------------------------------------------------

DEFAULT_TARGET_REFILL_CYCLES = 1


def bank_target_refill_cycles(default: int = DEFAULT_TARGET_REFILL_CYCLES) -> int:
    """Max extra missing-slot cycles after normal refill (default 1). Env override."""
    import os

    raw = (os.environ.get("QUESTION_BANK_TARGET_REFILL_CYCLES") or "").strip()
    if not raw:
        return max(0, int(default))
    try:
        return max(0, int(raw))
    except ValueError:
        return max(0, int(default))


def empty_bank_refill_diagnostics() -> Dict[str, Any]:
    return {
        "accepted_after_initial_fill": 0,
        "accepted_after_normal_refill": 0,
        "accepted_after_target_refill": 0,
        "accepted_after_target_cycle_1": 0,
        "accepted_after_target_cycle_2": 0,
        "missing_before_normal_refill": 0,
        "missing_before_target_refill": 0,
        "attempts_by_rejection_reason": {},
        "duplicate_retries_changed_intent": 0,
        "retries_changed_chunk": 0,
        "slots_exhausted": 0,
        "target_refill_cycles_run": 0,
        "strategies_used": {},
        "target_cycle_history": [],
    }


def empty_bank_cost_diagnostics() -> Dict[str, Any]:
    """Step 5 — per-stage cost/runtime counters (Bank Batch QA only)."""
    return {
        "generated_attempts": 0,
        "rejected_before_validator_llm": 0,
        "duplicate_early_exits": 0,
        "metadata_early_exits": 0,
        "structural_early_exits": 0,
        "deterministic_early_exits": 0,
        "intent_drift_early_exits": 0,
        "blind_solver_calls": 0,
        "cognitive_quality_calls": 0,
        "total_llm_calls": 0,
        "stage_ms_total": {
            "generate": 0.0,
            "early_gates": 0.0,
            "blind_solver": 0.0,
            "cognitive_quality": 0.0,
        },
        "stage_ms_count": {
            "generate": 0,
            "early_gates": 0,
            "blind_solver": 0,
            "cognitive_quality": 0,
        },
        "stage_tokens_approx": {
            "generate": 0,
            "blind_solver": 0,
            "cognitive_quality": 0,
        },
        "avg_latency_ms_per_stage": {},
    }


def record_bank_cost_stage(
    diagnostics: Dict[str, Any],
    stage: str,
    elapsed_ms: float,
    *,
    tokens_approx: Optional[int] = None,
) -> None:
    """Accumulate stage latency (and optional approximate tokens)."""
    ms_total = diagnostics.setdefault("stage_ms_total", {})
    ms_count = diagnostics.setdefault("stage_ms_count", {})
    ms_total[stage] = float(ms_total.get(stage) or 0.0) + float(elapsed_ms)
    ms_count[stage] = int(ms_count.get(stage) or 0) + 1
    if tokens_approx is not None:
        tok = diagnostics.setdefault("stage_tokens_approx", {})
        tok[stage] = int(tok.get(stage) or 0) + int(tokens_approx)
    avg: Dict[str, float] = {}
    for key, total in ms_total.items():
        n = int(ms_count.get(key) or 0)
        avg[key] = round(float(total) / n, 2) if n else 0.0
    diagnostics["avg_latency_ms_per_stage"] = avg


def finalize_bank_cost_diagnostics(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure derived averages / LLM totals are consistent before audit persist."""
    diag = dict(diagnostics or empty_bank_cost_diagnostics())
    ms_total = dict(diag.get("stage_ms_total") or {})
    ms_count = dict(diag.get("stage_ms_count") or {})
    avg: Dict[str, float] = {}
    for key, total in ms_total.items():
        n = int(ms_count.get(key) or 0)
        avg[key] = round(float(total) / n, 2) if n else 0.0
    diag["avg_latency_ms_per_stage"] = avg
    gen = int(diag.get("generated_attempts") or 0)
    blind = int(diag.get("blind_solver_calls") or 0)
    cog = int(diag.get("cognitive_quality_calls") or 0)
    # Generation + blind + cognitive/quality are the LLM stages we instrument.
    diag["total_llm_calls"] = gen + blind + cog
    return diag


def run_bank_batch_early_gates(
    *,
    slot: QuestionSlot,
    generated: Dict[str, Any],
    existing_question_texts: Sequence[str],
    existing_questions: Sequence[Dict[str, Any]] = (),
) -> Tuple[List[str], Optional[str]]:
    """
    Cheap Bank Batch rejection gates before blind solver / cognitive LLM.

    Order: structural answer-type → numerical → topic metadata → lexical +
    semantic duplicate → other deterministic heuristics.

    Returns (reasons, exit_category). exit_category is one of:
    ``structural``, ``metadata``, ``duplicate``, ``deterministic``, or None
    when all cheap gates pass. Does not replace full ``apply_independent_validation``.
    """
    question = generated or {}
    options = list(question.get("options") or [])
    indices = list(question.get("correct_indices") or [])

    structural = evaluate_answer_type(slot.answer_type, indices, len(options))
    if structural:
        return structural, "structural"

    numerical = check_numerical_equivalence(options, indices, slot.answer_type)
    if numerical:
        return numerical, "deterministic"

    metadata = validate_topic_metadata(
        question.get("topic", ""),
        question.get("sub_topic", ""),
        slot.chapter_title,
        subject=slot.subject,
    )
    if metadata:
        return metadata, "metadata"

    if is_near_duplicate(
        question.get("question", ""),
        existing_question_texts,
        content_aware=True,
    ):
        return (
            ["duplicate or near-duplicate of an existing question"],
            "duplicate",
        )

    candidate_record = {
        "chapter": slot.chapter,
        "topic": question.get("topic", ""),
        "question": question.get("question", ""),
    }
    if is_semantic_duplicate(candidate_record, existing_questions):
        return (
            [
                "semantic duplicate: tests the same concept/intent as an accepted question"
            ],
            "duplicate",
        )

    deterministic: List[str] = []
    deterministic.extend(
        _validate_subjective_best_objective_criterion(question.get("question", ""))
    )
    if deterministic:
        return deterministic, "deterministic"
    deterministic.extend(_validate_distractor_plausibility(question))
    if deterministic:
        return deterministic, "deterministic"
    if slot.answer_type == "multiple_correct":
        deterministic.extend(_validate_redundant_correct_options(question))
        if deterministic:
            return deterministic, "deterministic"

    return [], None


def bump_bank_early_exit(
    diagnostics: Dict[str, Any],
    category: Optional[str],
) -> None:
    """Increment Step 5 early-exit counters for a cheap-gate rejection."""
    diagnostics["rejected_before_validator_llm"] = (
        int(diagnostics.get("rejected_before_validator_llm") or 0) + 1
    )
    if category == "duplicate":
        diagnostics["duplicate_early_exits"] = (
            int(diagnostics.get("duplicate_early_exits") or 0) + 1
        )
    elif category == "metadata":
        diagnostics["metadata_early_exits"] = (
            int(diagnostics.get("metadata_early_exits") or 0) + 1
        )
    elif category == "structural":
        diagnostics["structural_early_exits"] = (
            int(diagnostics.get("structural_early_exits") or 0) + 1
        )
    elif category == "deterministic":
        diagnostics["deterministic_early_exits"] = (
            int(diagnostics.get("deterministic_early_exits") or 0) + 1
        )
    elif category == "intent_drift":
        diagnostics["intent_drift_early_exits"] = (
            int(diagnostics.get("intent_drift_early_exits") or 0) + 1
        )


def _rejected_validation_stub(
    slot: QuestionSlot,
    reasons: Sequence[str],
) -> Dict[str, Any]:
    """Minimal rejected validation payload for early exits (no LLM scores)."""
    return {
        "passed": False,
        "validation_status": "rejected",
        "validation_reasons": list(reasons),
        "difficulty_scores": {},
        "difficulty_score": 0,
        "validated_cognitive_difficulty": "easy",
        "target_difficulty": normalize_difficulty(slot.target_difficulty),
    }


def build_slot_avoidance_history(
    rejected_attempts: Sequence[Dict[str, Any]],
    question_number: Any,
) -> Dict[str, Any]:
    """Aggregate Step 3A/3B rejection metadata for one missing slot."""
    items = [
        r
        for r in (rejected_attempts or [])
        if r.get("question_number") == question_number
    ]
    stems: List[str] = []
    matched_stems: List[str] = []
    intents: List[str] = []
    topics: List[str] = []
    subs: List[str] = []
    chunks: List[int] = []
    reasons: List[str] = []
    dup_n = distractor_n = cognitive_n = 0
    for r in items:
        q = (r.get("question") or "").strip()
        if q:
            stems.append(q)
        ms = (r.get("matched_stem") or "").strip()
        if ms:
            matched_stems.append(ms)
        fp = (r.get("intent_fingerprint") or intent_fingerprint(q)).strip()
        if fp:
            intents.append(fp)
        t = (r.get("topic") or "").strip()
        if t:
            topics.append(t)
        s = (r.get("sub_topic") or "").strip()
        if s:
            subs.append(s)
        if r.get("source_chunk_index") is not None:
            try:
                chunks.append(int(r["source_chunk_index"]))
            except (TypeError, ValueError):
                pass
        for reason in r.get("rejection_reasons") or []:
            rs = str(reason).strip()
            if rs:
                reasons.append(rs)
            rl = rs.lower()
            if "duplicate" in rl:
                dup_n += 1
            if "distractor" in rl:
                distractor_n += 1
            if "cognitive difficulty mismatch" in rl:
                cognitive_n += 1
        mfp = (r.get("matched_intent_fingerprint") or "").strip()
        if mfp:
            intents.append(mfp)
        mt = (r.get("matched_topic") or "").strip()
        if mt:
            topics.append(mt)
    return {
        "rejected_stems": stems,
        "matched_stems": matched_stems,
        "intent_fingerprints": list(dict.fromkeys(intents)),
        "topics": list(dict.fromkeys(topics)),
        "sub_topics": list(dict.fromkeys(subs)),
        "chunk_indices": list(dict.fromkeys(chunks)),
        "failure_reasons": reasons,
        "duplicate_reject_count": dup_n,
        "distractor_reject_count": distractor_n,
        "cognitive_reject_count": cognitive_n,
    }


def classify_bank_refill_strategy(
    rejection_reasons: Sequence[str],
    avoidance: Optional[Dict[str, Any]] = None,
) -> str:
    """Pick a Bank Batch refill strategy from the latest rejection reasons."""
    avoidance = avoidance or {}
    text = " ".join(str(r).lower() for r in (rejection_reasons or []))
    dup_hits = int(avoidance.get("duplicate_reject_count") or 0)
    if "duplicate" in text or "near-duplicate" in text:
        if dup_hits >= 2:
            return "repeated_duplicate"
        return "duplicate"
    if "distractor" in text:
        return "distractor"
    if "cognitive difficulty mismatch" in text or "difficulty mismatch" in text:
        return "cognitive"
    return "normal"


def format_bank_batch_strategy_guidance(
    strategy: str,
    *,
    slot: Any,
    avoidance: Optional[Dict[str, Any]] = None,
    soft_coverage_hints: str = "",
) -> str:
    """
    Bank Batch–only progressive refill guidance (not the Step 2 diversity planner).

    Preserves requested difficulty and answer type; never suggests changing them.
    """
    avoidance = avoidance or {}
    difficulty = normalize_difficulty(getattr(slot, "target_difficulty", None) or "easy")
    answer_type = getattr(slot, "answer_type", "single_correct")
    parts: List[str] = [
        f"REFILL STRATEGY ({strategy}): Keep chapter, target difficulty={difficulty}, "
        f"and answer_type={answer_type} unchanged."
    ]

    avoid_intents = list(avoidance.get("intent_fingerprints") or [])[:8]
    avoid_topics = list(avoidance.get("topics") or [])[:6]
    avoid_chunks = list(avoidance.get("chunk_indices") or [])[:8]

    if strategy in ("duplicate", "repeated_duplicate"):
        parts.append(format_bank_batch_duplicate_retry_guidance())
        if avoid_intents:
            parts.append(
                "Forbidden prior intents for this slot (do not paraphrase): "
                + "; ".join(avoid_intents)
            )
        if avoid_topics:
            parts.append(
                "Already attempted topics for this slot (prefer a different eligible "
                "skill/concept): " + ", ".join(avoid_topics)
            )
        if strategy == "repeated_duplicate":
            parts.append(
                "Repeated duplicates: move to a different eligible chapter section/"
                "chunk and test a clearly different learning objective from this chapter."
            )
            if avoid_chunks:
                parts.append(
                    f"Avoid previously used chunk indices for this slot: {avoid_chunks}"
                )
    elif strategy == "distractor":
        parts.append(
            "DISTRACTOR-DRIVEN REFILL: Keep the same underlying content target if it "
            "is still eligible. Regenerate five options with misconception-based "
            "distractors (plausible student errors). Do not use joke/absurd fillers. "
            "Do not change the learning objective unless it was also rejected as a duplicate."
        )
    elif strategy == "cognitive":
        hint = DIFFICULTY_INTENT_HINTS.get(difficulty, DIFFICULTY_INTENT_HINTS["easy"])
        parts.append(
            "COGNITIVE-MISMATCH REFILL: Preserve the same content concept when possible, "
            f"but change the cognitive task to match target difficulty ({difficulty}). "
            f"{hint} Do not switch to an unrelated concept unless necessary."
        )
    else:
        parts.append(
            "Continue with a high-quality chapter-grounded item at the requested "
            "difficulty and answer type."
        )

    if soft_coverage_hints:
        parts.append(soft_coverage_hints.strip())
    return "\n".join(parts)


def select_chunk_avoiding_history(
    chunks: Sequence[str],
    slot_index_zero_based: int,
    attempt: int,
    avoided_indices: Optional[Sequence[int]] = None,
) -> Tuple[str, Optional[int]]:
    """
    Pick a chapter chunk for refill, preferring indices not yet tried for this slot.

    Falls back to normal select_chapter_chunk rotation when all chunks were tried.
    """
    if not chunks:
        return "", None
    avoided = {int(i) for i in (avoided_indices or []) if i is not None}
    n = len(chunks)
    # Prefer unused chunks first (stable order from slot + attempt)
    preferred: List[int] = []
    for offset in range(n):
        idx = (slot_index_zero_based + max(attempt, 1) - 1 + offset) % n
        if idx not in avoided:
            preferred.append(idx)
    if preferred:
        idx = preferred[0]
    else:
        idx = (slot_index_zero_based + max(attempt, 1) - 1) % n
    return chunks[idx], idx


def bump_reason_counts(
    diagnostics: Dict[str, Any],
    rejection_reasons: Sequence[str],
) -> None:
    bucket = diagnostics.setdefault("attempts_by_rejection_reason", {})
    tags = set()
    text = " ".join(str(r).lower() for r in (rejection_reasons or []))
    if "duplicate" in text:
        tags.add("duplicate")
    if "distractor" in text:
        tags.add("distractor")
    if "cognitive difficulty mismatch" in text:
        tags.add("cognitive_mismatch")
    if "topic metadata" in text or "generic topic" in text:
        tags.add("topic_metadata")
    if "self-check" in text:
        tags.add("self_check")
    if not tags:
        tags.add("other")
    for tag in tags:
        bucket[tag] = int(bucket.get(tag) or 0) + 1


_JOKE_FILLER_RE = re.compile(
    r"(?i)\b("
    r"aliens?|unicorns?|pizza|dinosaurs?|superhero|magic\s+wand|banana\s+peel|"
    r"lol|haha|asdf|qwerty|lorem\s+ipsum|n/?a\b|none\s+of\s+your\s+business|"
    r"because\s+i\s+said\s+so|random\s+guess"
    r")\b"
)


def generator_structural_self_check(
    generated: Dict[str, Any],
    *,
    answer_type: str,
    options_per_question: int = 5,
) -> List[str]:
    """
    Cheap Bank Batch generator-side structural checks before blind solver / quality.

    Does not replace independent validation; empty list means structurally OK to proceed.
    """
    errors: List[str] = []
    options = list(generated.get("options") or [])
    if len(options) != options_per_question:
        errors.append(
            f"self-check: expected {options_per_question} options, got {len(options)}"
        )

    normalized = [normalize_question_text(o) for o in options if (o or "").strip()]
    if len(normalized) != len(options):
        errors.append("self-check: one or more options are empty")
    if len(set(normalized)) != len(normalized):
        errors.append("self-check: options are not distinct")

    indices = list(generated.get("correct_indices") or [])
    if answer_type == "single_correct" and len(indices) != 1:
        errors.append("self-check: single_correct requires exactly one correct answer")
    if answer_type == "multiple_correct" and len(indices) < 2:
        errors.append("self-check: multiple_correct requires at least two correct answers")
    for idx in indices:
        if not isinstance(idx, int) or idx < 0 or idx >= len(options):
            errors.append("self-check: correct_indices out of range")
            break

    for i, opt in enumerate(options):
        if _JOKE_FILLER_RE.search(opt or ""):
            label = chr(65 + i) if 0 <= i < 5 else str(i)
            errors.append(f"self-check: option {label} looks like joke/irrelevant filler")

    return errors


@dataclass
class BankBatchBlueprint:
    """Request blueprint for bulk Question Bank generation (not final-paper layout)."""

    book_id: str
    grade: str
    subject: str
    chapter: int
    difficulty: str
    total_questions: int
    single_correct: int
    multiple_correct: int
    language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def bank_batch_from_dict(data: Dict[str, Any]) -> BankBatchBlueprint:
    """Parse and validate a bank-batch request dict."""
    if not data:
        raise ValueError("Bank batch blueprint is required")
    book_id = str(data.get("book_id") or "").strip()
    if not book_id:
        raise ValueError("book_id is required for bank batch generation")
    grade = str(data.get("grade") or "").strip()
    if not grade:
        raise ValueError("grade is required for bank batch generation")
    subject = str(data.get("subject") or "").strip()
    if not subject:
        raise ValueError("subject is required for bank batch generation")
    try:
        chapter = int(data.get("chapter"))
    except (TypeError, ValueError):
        raise ValueError("chapter must be a positive integer") from None
    if chapter < 1:
        raise ValueError("chapter must be >= 1")
    difficulty = normalize_difficulty(data.get("difficulty"))
    try:
        total = int(data.get("total_questions"))
        single = int(data.get("single_correct", 0))
        multiple = int(data.get("multiple_correct", 0))
    except (TypeError, ValueError):
        raise ValueError("total_questions, single_correct, and multiple_correct must be integers") from None
    if total < 1:
        raise ValueError("total_questions must be >= 1")
    if single < 0 or multiple < 0:
        raise ValueError("single_correct and multiple_correct must be >= 0")
    if single + multiple != total:
        raise ValueError(
            f"single_correct ({single}) + multiple_correct ({multiple}) "
            f"must equal total_questions ({total})"
        )
    language = str(data.get("language") or "en").strip() or "en"
    return BankBatchBlueprint(
        book_id=book_id,
        grade=grade,
        subject=subject,
        chapter=chapter,
        difficulty=difficulty,
        total_questions=total,
        single_correct=single,
        multiple_correct=multiple,
        language=language,
    )


def build_bank_batch_slots(
    blueprint: BankBatchBlueprint,
    *,
    chapter_title: str,
) -> List[QuestionSlot]:
    """Expand a single-chapter, single-difficulty bank batch into ordered slots."""
    total = blueprint.total_questions
    multi_set = set(_spread_indices(total, blueprint.multiple_correct))
    slots: List[QuestionSlot] = []
    for i in range(total):
        answer_type = "multiple_correct" if i in multi_set else "single_correct"
        slots.append(
            QuestionSlot(
                question_number=i + 1,
                chapter=blueprint.chapter,
                chapter_title=chapter_title,
                target_difficulty=blueprint.difficulty,
                answer_type=answer_type,
                grade=blueprint.grade,
                subject=blueprint.subject,
            )
        )
    return slots


def _summarize_bank_batch_failures(
    failed_slots: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate failure reasons for partial bank-batch completion reporting."""
    reason_counts: Dict[str, int] = {}
    for slot in failed_slots:
        for reason in slot.get("validation_reasons") or []:
            key = str(reason).strip()
            if key:
                reason_counts[key] = reason_counts.get(key, 0) + 1
    top_reasons = sorted(reason_counts.items(), key=lambda x: (-x[1], x[0]))[:8]
    return {
        "failed_slot_count": len(failed_slots),
        "top_failure_reasons": [{"reason": r, "count": c} for r, c in top_reasons],
        "failed_question_numbers": [
            int(s.get("question_number"))
            for s in failed_slots
            if s.get("question_number") is not None
        ],
    }


def audit_bank_batch(
    blueprint: BankBatchBlueprint,
    approved: Sequence[Dict[str, Any]],
    failed_slots: Sequence[Dict[str, Any]],
    *,
    options_per_question: int = 5,
) -> Dict[str, Any]:
    """
    Deterministic audit for Question Bank Batch jobs.

    Unlike audit_paper(), this checks only the submitted bank-batch request:
    grade, chapter, target difficulty, answer-type mix, validation pass, and uniqueness.
    Partial success (e.g. 43/50) yields completed_partial — not a crashed job.
    """
    errors: List[str] = []
    requested = int(blueprint.total_questions)
    accepted = len(approved)
    target_diff = normalize_difficulty(blueprint.difficulty)

    if accepted > requested:
        errors.append(f"Accepted count {accepted} exceeds requested {requested}")

    expected_single = int(blueprint.single_correct)
    expected_multi = int(blueprint.multiple_correct)
    actual_single = sum(1 for q in approved if q.get("answer_type") == "single_correct")
    actual_multi = sum(1 for q in approved if q.get("answer_type") == "multiple_correct")

    seen_text: List[str] = []
    for i, q in enumerate(approved, start=1):
        q_grade = str(q.get("grade") or "").strip()
        if q_grade and q_grade != str(blueprint.grade).strip():
            errors.append(f"Q{i}: grade mismatch (got {q_grade!r}, expected {blueprint.grade!r})")
        q_chapter = q.get("chapter")
        if q_chapter is not None and int(q_chapter) != int(blueprint.chapter):
            errors.append(
                f"Q{i}: chapter mismatch (got {q_chapter}, expected {blueprint.chapter})"
            )
        q_target = normalize_difficulty(q.get("target_difficulty"))
        if q_target != target_diff:
            errors.append(
                f"Q{i}: target difficulty mismatch (got {q_target}, expected {target_diff})"
            )
        if q.get("validation_status") != "passed":
            errors.append(f"Q{i}: did not pass quality validation")
        validated = normalize_difficulty(q.get("validated_cognitive_difficulty"))
        if validated != target_diff:
            errors.append(
                f"Q{i}: validated difficulty {validated} != target {target_diff}"
            )
        options = q.get("options") or []
        if len(options) != options_per_question:
            errors.append(f"Q{i}: expected {options_per_question} options, got {len(options)}")
        text = q.get("question", "")
        if is_near_duplicate(text, seen_text, content_aware=True):
            errors.append(f"Q{i}: duplicate/near-duplicate within batch")
        seen_text.append(text)

    if actual_single != expected_single:
        errors.append(f"single_correct: {actual_single} accepted, expected {expected_single}")
    if actual_multi != expected_multi:
        errors.append(f"multiple_correct: {actual_multi} accepted, expected {expected_multi}")

    failed_count = len(failed_slots)
    quality_ok = all(
        q.get("validation_status") == "passed"
        and normalize_difficulty(q.get("target_difficulty")) == target_diff
        and normalize_difficulty(q.get("validated_cognitive_difficulty")) == target_diff
        for q in approved
    )
    uniqueness_ok = not any(
        "duplicate" in e.lower() for e in errors if "duplicate" in e.lower()
    )

    if accepted == requested and not failed_slots and not errors:
        status = "completed"
    elif accepted < requested and quality_ok and uniqueness_ok:
        status = "completed_partial"
    elif accepted == 0 and failed_count >= requested:
        status = "completed_partial"
    else:
        status = "completed_partial" if accepted > 0 else "failed"

    failure_summary = _summarize_bank_batch_failures(failed_slots) if failed_slots else {}

    return {
        "ok": len(errors) == 0 and accepted == requested and not failed_slots,
        "status": status,
        "errors": errors,
        "requested": requested,
        "accepted": accepted,
        "failed": failed_count,
        "failure_summary": failure_summary,
        "expected": {
            "grade": blueprint.grade,
            "book_id": blueprint.book_id,
            "chapter": blueprint.chapter,
            "difficulty": target_diff,
            "single_correct": expected_single,
            "multiple_correct": expected_multi,
        },
        "actual": {
            "single_correct": actual_single,
            "multiple_correct": actual_multi,
        },
    }


# ---------------------------------------------------------------------------
# Bank Batch diversity planner (soft guidance; LLM-free)
# ---------------------------------------------------------------------------

DIFFICULTY_INTENT_HINTS: Dict[str, str] = {
    "easy": (
        "Prefer recall, recognition, direct comprehension, or a straightforward "
        "one-step application of a single concept from the preferred section."
    ),
    "medium": (
        "Prefer genuine application or interpretation with 1–2 reasoning steps "
        "using the preferred concept."
    ),
    "difficult": (
        "Prefer multi-step reasoning, analysis, inference, evaluation, or "
        "concept integration using the preferred concept."
    ),
}

_LO_HEADER_RE = re.compile(
    r"(?im)^\s*learning\s+outcomes?\s*:?\s*$"
)
_BULLET_RE = re.compile(r"(?m)^\s*(?:[\*\-•]|\d+[.)])\s+(.+)$")
_SECTION_HEADING_RE = re.compile(
    r"^(?:#{1,3}\s+|(?:\d+(?:\.\d+)*)\s+)([A-Za-z][^\n]{2,80})$"
    r"|^([A-Z][A-Za-z0-9 ,/'&\-]{2,60})$",
    re.MULTILINE,
)


@dataclass
class DiversityPlan:
    """Soft diversity guidance for one Bank Batch generation attempt."""

    prefer_topic: str = ""
    prefer_sub_topic: str = ""
    prefer_learning_outcome: str = ""
    prefer_section: str = ""
    avoid_topics: List[str] = None  # type: ignore[assignment]
    avoid_intents: List[str] = None  # type: ignore[assignment]
    preferred_chunk_index: int = 0
    difficulty_intent_hint: str = ""
    target_difficulty: str = ""
    answer_type: str = ""

    def __post_init__(self) -> None:
        if self.avoid_topics is None:
            self.avoid_topics = []
        if self.avoid_intents is None:
            self.avoid_intents = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_chapter_concept_catalog(chapter_text: str) -> Dict[str, List[str]]:
    """
    Derive soft concept targets from chapter text (learning outcomes + headings).

    Deterministic and LLM-free. Empty lists are fine when structure is missing.
    """
    text = chapter_text or ""
    learning_outcomes: List[str] = []
    sections: List[str] = []

    lines = text.splitlines()
    in_lo = False
    for line in lines:
        if _LO_HEADER_RE.match(line.strip()):
            in_lo = True
            continue
        if in_lo:
            if not line.strip():
                if learning_outcomes:
                    in_lo = False
                continue
            bullet = _BULLET_RE.match(line)
            if bullet:
                item = bullet.group(1).strip().lstrip("* ").strip()
                # Strip leading verbs like "Understand what ..."
                item = re.sub(
                    r"^(?:Students will be able to:\s*)?",
                    "",
                    item,
                    flags=re.I,
                ).strip()
                if item and item.lower() not in {x.lower() for x in learning_outcomes}:
                    learning_outcomes.append(item[:120])
                continue
            if line.strip() and not line.strip().startswith(("*", "-", "•")):
                in_lo = False

    for match in _SECTION_HEADING_RE.finditer(text):
        title = (match.group(1) or match.group(2) or "").strip()
        if not title:
            continue
        low = title.lower()
        if low.startswith("chapter ") or low.startswith("learning outcome"):
            continue
        if len(title.split()) > 12:
            continue
        if title not in sections and title.lower() not in {s.lower() for s in sections}:
            sections.append(title[:100])

    return {
        "learning_outcomes": learning_outcomes[:20],
        "sections": sections[:30],
    }


def _intent_fingerprint(question: str) -> str:
    words = sorted(_extract_intent_words(question))
    return " ".join(words[:8])


def summarize_diversity_usage(
    questions: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compact usage stats from bank seeds + current-batch accepted questions."""
    topic_counts: Dict[str, int] = {}
    sub_topic_counts: Dict[str, int] = {}
    intent_summaries: List[str] = []
    intent_fingerprints: List[str] = []
    used_chunk_indices: List[int] = []

    for q in questions:
        topic = (q.get("topic") or "").strip()
        sub = (q.get("sub_topic") or "").strip()
        if topic:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        if sub:
            sub_topic_counts[sub] = sub_topic_counts.get(sub, 0) + 1
        stem = (q.get("question") or "").strip()
        if stem:
            fp = _intent_fingerprint(stem)
            if fp and fp not in intent_fingerprints:
                intent_fingerprints.append(fp)
                # Short human-readable avoid phrase
                words = stem.split()
                short = " ".join(words[:12])
                if short:
                    intent_summaries.append(short)
        chunk_idx = q.get("source_chunk_index")
        if isinstance(chunk_idx, int):
            used_chunk_indices.append(chunk_idx)

    return {
        "topic_counts": topic_counts,
        "sub_topic_counts": sub_topic_counts,
        "intent_summaries": intent_summaries[:40],
        "intent_fingerprints": intent_fingerprints[:40],
        "used_chunk_indices": used_chunk_indices,
    }


def _pick_underused(
    candidates: Sequence[str],
    usage_counts: Dict[str, int],
    *,
    slot_index: int,
    avoid_words: Optional[set] = None,
) -> str:
    if not candidates:
        return ""
    avoid_words = avoid_words or set()
    scored: List[Tuple[int, int, str]] = []
    for i, cand in enumerate(candidates):
        cand_words = _extract_intent_words(cand)
        # Penalize overlap with avoided previous intent
        avoid_penalty = len(cand_words & avoid_words) if avoid_words else 0
        # Match usage by substring / word overlap with existing topics
        usage = 0
        for key, count in usage_counts.items():
            key_words = _extract_intent_words(key)
            if cand.lower() == key.lower() or cand.lower() in key.lower() or key.lower() in cand.lower():
                usage = max(usage, count)
            elif cand_words and key_words and len(cand_words & key_words) / min(len(cand_words), len(key_words)) >= 0.5:
                usage = max(usage, count)
        scored.append((usage + avoid_penalty * 2, i, cand))
    scored.sort(key=lambda x: (x[0], (x[1] + slot_index) % max(len(candidates), 1)))
    # Prefer lowest usage; rotate among ties via slot_index
    best_usage = scored[0][0]
    tied = [c for u, i, c in scored if u == best_usage]
    return tied[slot_index % len(tied)]


def plan_bank_batch_diversity(
    *,
    slot: QuestionSlot,
    attempt: int,
    catalog: Optional[Dict[str, Any]],
    usage: Optional[Dict[str, Any]],
    chunks: Sequence[str],
    previous_intent_words: Optional[set] = None,
    previous_chunk_index: Optional[int] = None,
) -> DiversityPlan:
    """
    Soft diversity plan for one Bank Batch slot attempt.

    Does not change slot.target_difficulty or slot.answer_type.
    """
    catalog = catalog or {}
    usage = usage or {}
    topic_counts = dict(usage.get("topic_counts") or {})
    sub_counts = dict(usage.get("sub_topic_counts") or {})
    intent_summaries = list(usage.get("intent_summaries") or [])
    used_chunks = list(usage.get("used_chunk_indices") or [])

    outcomes = list(catalog.get("learning_outcomes") or [])
    sections = list(catalog.get("sections") or [])
    slot_index = max(0, int(slot.question_number) - 1)
    avoid_words = set(previous_intent_words or set())

    prefer_lo = _pick_underused(outcomes, topic_counts, slot_index=slot_index, avoid_words=avoid_words)
    prefer_section = _pick_underused(
        sections, {**topic_counts, **sub_counts}, slot_index=slot_index + attempt, avoid_words=avoid_words
    )

    # Prefer topic/sub-topic labels from catalog when present; else leave soft.
    prefer_topic = prefer_section or (prefer_lo.split(" ", 3)[-1] if prefer_lo else "")
    if prefer_topic and len(prefer_topic) > 60:
        prefer_topic = " ".join(prefer_topic.split()[:6])
    prefer_sub = ""
    if prefer_lo and prefer_section and prefer_lo.lower() != prefer_section.lower():
        prefer_sub = prefer_lo[:80]
    elif prefer_lo:
        prefer_sub = prefer_lo[:80]

    # Heavily used topics → avoid list
    avoid_topics = [
        t for t, c in sorted(topic_counts.items(), key=lambda x: (-x[1], x[0]))
        if c >= 2 or (c >= 1 and len(topic_counts) <= 3)
    ][:6]
    # Always include top-used even if count==1 when many accepted
    if not avoid_topics and topic_counts:
        avoid_topics = [
            t for t, _ in sorted(topic_counts.items(), key=lambda x: (-x[1], x[0]))
        ][:4]

    avoid_intents = intent_summaries[:8]
    if previous_intent_words:
        # Put a compact reminder of the failed intent first
        prev_label = " ".join(sorted(previous_intent_words)[:8])
        if prev_label:
            avoid_intents = [f"(previous attempt) {prev_label}"] + [
                a for a in avoid_intents if a != prev_label
            ]

    # Chunk rotation: prefer least-used chunk; avoid previous on retry
    n_chunks = len(chunks)
    preferred_chunk = 0
    if n_chunks:
        chunk_use = {i: 0 for i in range(n_chunks)}
        for idx in used_chunks:
            if isinstance(idx, int) and 0 <= idx < n_chunks:
                chunk_use[idx] = chunk_use.get(idx, 0) + 1
        # Base from slot + attempt
        ordered = sorted(
            range(n_chunks),
            key=lambda i: (chunk_use.get(i, 0), (i + slot_index + attempt - 1) % n_chunks),
        )
        if previous_chunk_index is not None and n_chunks > 1:
            ordered = [i for i in ordered if i != previous_chunk_index] or ordered
        preferred_chunk = ordered[0]

    difficulty = normalize_difficulty(slot.target_difficulty)
    return DiversityPlan(
        prefer_topic=prefer_topic,
        prefer_sub_topic=prefer_sub,
        prefer_learning_outcome=prefer_lo,
        prefer_section=prefer_section,
        avoid_topics=avoid_topics,
        avoid_intents=avoid_intents,
        preferred_chunk_index=preferred_chunk,
        difficulty_intent_hint=DIFFICULTY_INTENT_HINTS.get(difficulty, DIFFICULTY_INTENT_HINTS["easy"]),
        target_difficulty=difficulty,
        answer_type=slot.answer_type,
    )


def select_chunk_for_diversity_plan(
    chunks: Sequence[str],
    plan: DiversityPlan,
) -> Tuple[str, int]:
    """Return (excerpt, chunk_index) using the plan's preferred chunk."""
    if not chunks:
        return "", 0
    idx = int(plan.preferred_chunk_index) % len(chunks)
    return chunks[idx], idx


def format_diversity_guidance(plan: DiversityPlan) -> str:
    """Compact prompt block for Bank Batch generation (soft guidance)."""
    prefer_bits = []
    if plan.prefer_section:
        prefer_bits.append(f"section/concept: {plan.prefer_section}")
    if plan.prefer_learning_outcome:
        prefer_bits.append(f"learning outcome: {plan.prefer_learning_outcome}")
    if plan.prefer_topic:
        prefer_bits.append(f"topic≈{plan.prefer_topic}")
    if plan.prefer_sub_topic:
        prefer_bits.append(f"sub_topic≈{plan.prefer_sub_topic}")
    prefer_line = "; ".join(prefer_bits) if prefer_bits else "an underused concept from this chapter excerpt"

    avoid_topics = ", ".join(plan.avoid_topics[:5]) if plan.avoid_topics else "none listed"
    avoid_intents = "; ".join(f'"{x}"' for x in plan.avoid_intents[:5]) if plan.avoid_intents else "none listed"

    return (
        "\nDIVERSITY GUIDANCE (Bank Batch — soft preferences; still obey all quality rules):\n"
        f"- Prefer: {prefer_line}\n"
        f"- Avoid repeating heavily used topics: {avoid_topics}\n"
        f"- Avoid repeating these question intents/stems: {avoid_intents}\n"
        f"- Difficulty-appropriate intent for {plan.target_difficulty.upper()}: "
        f"{plan.difficulty_intent_hint}\n"
        f"- Keep answer type exactly: {plan.answer_type}\n"
        f"- Keep target difficulty exactly: {plan.target_difficulty}\n"
        "- Derive topic/sub_topic from the preferred concept and the chapter excerpt.\n"
    )
