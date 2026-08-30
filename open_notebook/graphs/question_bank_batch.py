"""
Question Bank Batch — slot-based LangGraph pipeline for bulk bank pool generation.

Flow:
  prepare_bank_batch → fill_slots → mark_fill → [refill_slots] → mark_refill
  → [target_refill × N?] → audit_bank_batch → persist_bank_batch

Reuses fill_slots / refill_slots from question_paper.py without changing final-paper audit semantics.
Step 4+ adds strategy-aware refill + bounded target-refill cycles (Bank Batch only; default N=1).
"""

from __future__ import annotations

from typing import Any, Dict, List  # noqa: F401 — Dict used by intent state

from langgraph.graph import END, START, StateGraph
from loguru import logger

from open_notebook.domain.question_bank import QuestionRecord
from open_notebook.graphs.question_paper import (
    PaperState,
    fill_slots,
    parse_book_chapters,
    refill_slots,
)
from open_notebook.graphs.question_bank_intent import (
    build_or_load_base_intent_catalog,
    empty_intent_diagnostics,
    expand_intent_catalog_for_request,
    filter_intents_against_used,
    is_bank_intent_planner_enabled,
    prepare_batch_intent_assignments,
    should_replenish_catalog,
)
from open_notebook.graphs.question_answer_pattern import apply_answer_position_audit
from open_notebook.graphs.question_paper_blueprint import (
    CHAPTER_CHUNK_SIZE,
    audit_bank_batch,
    bank_batch_budget_exhausted,
    bank_batch_from_dict,
    bank_target_refill_cycles,
    build_bank_batch_slots,
    chunk_chapter_text,
    compute_bank_batch_saturation_diagnostics,
    empty_bank_cost_diagnostics,
    empty_bank_refill_diagnostics,
    extract_chapter_concept_catalog,
    finalize_bank_cost_diagnostics,
    load_bank_duplicate_seed_snapshot,
)


async def prepare_bank_batch(state: PaperState) -> dict:
    """Build single-chapter bank-batch slots and load existing bank duplicates."""
    import time

    raw = state.get("bank_batch_blueprint") or {}
    blueprint = bank_batch_from_dict(raw)

    chapters = parse_book_chapters(state.get("book_chapters"), state.get("book_content"))
    if not chapters:
        raise ValueError(
            "No chapter content could be loaded for bank batch generation."
        )

    chapter_num = int(blueprint.chapter)
    if len(chapters) == 1:
        selected = chapters[0]
    elif chapter_num < 1 or chapter_num > len(chapters):
        raise ValueError(
            f"Chapter {chapter_num} is not available in the selected book "
            f"({len(chapters)} chapter(s) loaded)."
        )
    else:
        selected = chapters[chapter_num - 1]
    chapter_title = selected.get("title") or f"Chapter {chapter_num}"
    chapter_text = selected.get("text") or ""
    chunks = chunk_chapter_text(chapter_text)
    chapter_chunks = {str(chapter_num): chunks}
    diversity_catalog = extract_chapter_concept_catalog(chapter_text)

    logger.info(
        f"Bank batch chapter {chapter_num} '{chapter_title}': "
        f"{len(chapter_text)} chars → {len(chunks)} chunk(s) "
        f"(chunk_size={CHAPTER_CHUNK_SIZE}); "
        f"catalog LOs={len(diversity_catalog.get('learning_outcomes') or [])} "
        f"sections={len(diversity_catalog.get('sections') or [])}"
    )

    slots = build_bank_batch_slots(blueprint, chapter_title=chapter_title)
    snapshot = load_bank_duplicate_seed_snapshot()
    if snapshot is not None:
        existing = snapshot
        logger.info(
            f"Using fixed Bank Batch seed snapshot ({len(existing)} question(s)) "
            f"via QUESTION_BANK_SEED_SNAPSHOT_FILE"
        )
    else:
        existing = await QuestionRecord.fetch_scoped_for_duplicate_check(
            grade=blueprint.grade,
            chapter=blueprint.chapter,
            target_difficulty=blueprint.difficulty,
        )
    seed_texts = [r.get("question", "") for r in existing if r.get("question")]
    seed_qs = [
        {
            "id": str(r.get("id") or "") or None,
            "chapter": r.get("chapter"),
            "topic": r.get("topic", ""),
            "sub_topic": r.get("sub_topic", ""),
            "question": r.get("question", ""),
            "source_chunk_index": r.get("source_chunk_index"),
        }
        for r in existing
    ]

    max_target = int(
        state.get("max_target_refill_cycles")
        if state.get("max_target_refill_cycles") is not None
        else bank_target_refill_cycles()
    )

    intent_diagnostics = empty_intent_diagnostics()
    cost_diagnostics = empty_bank_cost_diagnostics()
    bank_intent_catalog: List[dict] = []
    bank_intent_assignments: Dict[str, dict] = {}
    bank_intent_remaining: List[dict] = []
    book_id = ""
    if is_bank_intent_planner_enabled():
        book_id = str(
            state.get("book_id")
            or blueprint.book_id
            or (raw.get("book_id") if isinstance(raw, dict) else "")
            or ""
        )
        base_catalog = await build_or_load_base_intent_catalog(
            book_id=book_id,
            chapter=int(blueprint.chapter),
            difficulty=blueprint.difficulty,
            chapter_text=chapter_text,
            chunks=chunks,
            grade=str(blueprint.grade or ""),
            subject=str(blueprint.subject or ""),
            chapter_title=chapter_title,
            requested_count=int(blueprint.total_questions),
            concept_catalog=diversity_catalog,
            model_id=state.get("generator_model"),
            diagnostics=intent_diagnostics,
            cost_diagnostics=cost_diagnostics,
        )
        available_probe, _filtered = filter_intents_against_used(
            base_catalog, bank_questions=seed_qs
        )
        usable = len(available_probe)
        requested_n = int(blueprint.total_questions)
        if should_replenish_catalog(
            unused_intents=usable,
            missing_slots=requested_n,
            catalog_size=len(base_catalog),
            requested_count=requested_n,
            planner_calls=int(intent_diagnostics.get("planner_calls") or 0),
            replenish_rounds=int(intent_diagnostics.get("replenishment_rounds") or 0),
            require_capacity_for_missing=True,
        ):
            base_catalog = await expand_intent_catalog_for_request(
                catalog=list(base_catalog),
                chunks=chunks,
                requested_count=requested_n,
                missing_slots=requested_n,
                unused_intents=usable,
                grade=str(blueprint.grade or ""),
                subject=str(blueprint.subject or ""),
                chapter=int(blueprint.chapter),
                chapter_title=chapter_title,
                difficulty=blueprint.difficulty,
                bank_questions=seed_qs,
                diagnostics=intent_diagnostics,
                model_id=state.get("generator_model"),
                cache_key=str(intent_diagnostics.get("cache_key") or ""),
                book_id=book_id,
                content_hash=str(intent_diagnostics.get("content_hash") or ""),
                cost_diagnostics=cost_diagnostics,
            )
        bank_intent_catalog = list(base_catalog)
        bank_intent_assignments, bank_intent_remaining, intent_diagnostics = (
            prepare_batch_intent_assignments(
                base_catalog=base_catalog,
                slots=slots,
                bank_questions=seed_qs,
                diagnostics=intent_diagnostics,
            )
        )
        logger.info(
            f"Intent planner v2+9: grounded={intent_diagnostics.get('grounded_intents')} "
            f"expand={intent_diagnostics.get('cache_expansion_count')} "
            f"planner_calls={intent_diagnostics.get('planner_calls')} "
            f"bank_derived={intent_diagnostics.get('bank_intents_derived')} "
            f"filtered_bank={intent_diagnostics.get('intents_filtered_already_in_bank')} "
            f"assigned={intent_diagnostics.get('intents_assigned')}/{len(slots)} "
            f"cache_hit={intent_diagnostics.get('cache_hit')}"
        )

    logger.info(
        f"Prepared bank batch: {len(slots)} slots for "
        f"grade={blueprint.grade!r} ch={blueprint.chapter} "
        f"difficulty={blueprint.difficulty}; "
        f"{len(seed_qs)} existing bank question(s) for duplicate seeding; "
        f"max_target_refill_cycles={max_target}"
    )

    return {
        "slots": [s.to_dict() for s in slots],
        "chapter_chunks": chapter_chunks,
        "book_grounded": True,
        "grade": blueprint.grade,
        "subject": blueprint.subject,
        "language": blueprint.language,
        "bank_batch_mode": True,
        "bank_duplicate_seed_texts": seed_texts,
        "bank_duplicate_seed_questions": seed_qs,
        "bank_diversity_catalog": diversity_catalog,
        "bank_intent_catalog": bank_intent_catalog,
        "bank_intent_assignments": bank_intent_assignments,
        "bank_intent_remaining": bank_intent_remaining,
        "intent_diagnostics": intent_diagnostics,
        "intent_planner_context": {
            "book_id": book_id if is_bank_intent_planner_enabled() else "",
            "grade": str(blueprint.grade or ""),
            "subject": str(blueprint.subject or ""),
            "chapter": int(blueprint.chapter),
            "chapter_title": chapter_title,
            "difficulty": blueprint.difficulty,
            "requested_count": int(blueprint.total_questions),
            "cache_key": str((intent_diagnostics or {}).get("cache_key") or ""),
            "content_hash": str((intent_diagnostics or {}).get("content_hash") or ""),
        },
        "approved": list(state.get("approved") or []),
        "failed_slots": list(state.get("failed_slots") or []),
        "used_stems": list(state.get("used_stems") or []),
        "rejected_with_feedback": list(state.get("rejected_with_feedback") or []),
        "persisted_question_ids": list(state.get("persisted_question_ids") or []),
        "refill_diagnostics": empty_bank_refill_diagnostics(),
        "cost_diagnostics": cost_diagnostics,
        "target_refill_cycles_done": 0,
        "max_target_refill_cycles": max_target,
        "refill_phase": "normal",
        "batch_started_at": float(state.get("batch_started_at") or time.time()),
        "minimum_accepted_questions": state.get("minimum_accepted_questions"),
        "max_batch_generation_attempts": state.get("max_batch_generation_attempts"),
        "max_batch_runtime_seconds": state.get("max_batch_runtime_seconds"),
        "batch_budget_exhausted_reason": state.get("batch_budget_exhausted_reason"),
    }


async def mark_after_fill(state: PaperState) -> dict:
    """Record accepted/missing after initial fill (diagnostics only)."""
    diag = dict(state.get("refill_diagnostics") or empty_bank_refill_diagnostics())
    accepted = len(state.get("approved") or [])
    missing = len(state.get("failed_slots") or [])
    diag["accepted_after_initial_fill"] = accepted
    diag["missing_before_normal_refill"] = missing
    logger.info(f"Bank batch after fill: accepted={accepted} missing={missing}")
    return {"refill_diagnostics": diag, "refill_phase": "normal"}


async def mark_after_normal_refill(state: PaperState) -> dict:
    """Record accepted/missing after the normal refill pass."""
    diag = dict(state.get("refill_diagnostics") or empty_bank_refill_diagnostics())
    # Merge any diagnostics updates from refill_slots
    incoming = state.get("refill_diagnostics") or {}
    diag.update(incoming)
    accepted = len(state.get("approved") or [])
    missing = len(state.get("failed_slots") or [])
    diag["accepted_after_normal_refill"] = accepted
    diag["missing_before_target_refill"] = missing
    # If normal refill was skipped, mirror fill counts
    if not diag.get("accepted_after_initial_fill") and accepted:
        diag["accepted_after_initial_fill"] = accepted
    logger.info(
        f"Bank batch after normal refill: accepted={accepted} missing={missing}"
    )
    return {"refill_diagnostics": diag}


async def bank_target_refill(state: PaperState) -> dict:
    """
    One bounded missing-slot refill cycle (Bank Batch).

    Never regenerates accepted questions; reuses refill_slots with phase=target.
    The graph may invoke this node repeatedly up to max_target_refill_cycles.
    """
    import time

    approved = list(state.get("approved") or [])
    failed = list(state.get("failed_slots") or [])
    cycles_done = int(state.get("target_refill_cycles_done") or 0)
    max_cycles = int(
        state.get("max_target_refill_cycles")
        if state.get("max_target_refill_cycles") is not None
        else bank_target_refill_cycles()
    )
    raw = state.get("bank_batch_blueprint") or {}
    blueprint = bank_batch_from_dict(raw)
    requested = int(blueprint.total_questions)
    accepted = len(approved)

    if accepted >= requested or not failed or cycles_done >= max_cycles:
        logger.info(
            f"Bank target refill skipped: accepted={accepted}/{requested} "
            f"failed={len(failed)} cycles={cycles_done}/{max_cycles}"
        )
        diag = dict(state.get("refill_diagnostics") or empty_bank_refill_diagnostics())
        diag["accepted_after_target_refill"] = accepted
        diag["target_refill_cycles_run"] = cycles_done
        return {
            "refill_diagnostics": diag,
            "target_refill_cycles_done": cycles_done,
        }

    if bank_batch_budget_exhausted(state):
        logger.info(
            f"Bank target refill skipped: batch budget exhausted "
            f"(reason={state.get('batch_budget_exhausted_reason')}) "
            f"accepted={accepted}/{requested} failed={len(failed)}"
        )
        diag = dict(state.get("refill_diagnostics") or empty_bank_refill_diagnostics())
        diag["accepted_after_target_refill"] = accepted
        diag["target_refill_cycles_run"] = cycles_done
        return {
            "refill_diagnostics": diag,
            "target_refill_cycles_done": cycles_done,
            "batch_budget_exhausted_reason": state.get("batch_budget_exhausted_reason"),
        }

    cycle_num = cycles_done + 1
    missing_before = len(failed)
    accepted_before = accepted
    logger.info(
        f"Bank target refill cycle {cycle_num}/{max_cycles}: "
        f"missing={missing_before} (accepted={accepted_before}/{requested})"
    )
    t0 = time.perf_counter()
    result = await refill_slots(
        {
            **state,
            "refill_phase": "target",
            "approved": approved,
            "failed_slots": failed,
        }
    )
    elapsed_s = round(time.perf_counter() - t0, 2)
    new_approved = result.get("approved") or approved
    new_failed = result.get("failed_slots") or []
    newly_accepted = max(0, len(new_approved) - accepted_before)
    missing_after = len(new_failed)
    diag = dict(result.get("refill_diagnostics") or state.get("refill_diagnostics") or {})
    history = list(diag.get("target_cycle_history") or [])
    history.append(
        {
            "cycle": cycle_num,
            "missing_before": missing_before,
            "newly_accepted": newly_accepted,
            "missing_after": missing_after,
            "accepted_before": accepted_before,
            "accepted_after": len(new_approved),
            "runtime_s": elapsed_s,
        }
    )
    diag["target_cycle_history"] = history
    diag["accepted_after_target_refill"] = len(new_approved)
    diag["target_refill_cycles_run"] = cycle_num
    diag["missing_before_target_refill"] = (
        diag.get("missing_before_target_refill") or missing_before
    )
    if cycle_num == 1:
        diag["accepted_after_target_cycle_1"] = len(new_approved)
    elif cycle_num == 2:
        diag["accepted_after_target_cycle_2"] = len(new_approved)
        if not diag.get("accepted_after_target_cycle_1"):
            diag["accepted_after_target_cycle_1"] = accepted_before
    logger.info(
        f"Bank target refill cycle {cycle_num} done: "
        f"+{newly_accepted} accepted, missing={missing_after}, runtime={elapsed_s}s"
    )
    return {
        **result,
        "approved": new_approved,
        "failed_slots": new_failed,
        "refill_diagnostics": diag,
        "target_refill_cycles_done": cycle_num,
        "refill_phase": "target",
    }


async def audit_bank_batch_node(state: PaperState) -> dict:
    """Run bank-batch audit (partial success allowed)."""
    import time

    raw = state.get("bank_batch_blueprint") or {}
    blueprint = bank_batch_from_dict(raw)
    approved, pos_diag = apply_answer_position_audit(list(state.get("approved") or []))
    failed = state.get("failed_slots") or []
    rejected = state.get("rejected_with_feedback") or []
    started = state.get("batch_started_at")
    runtime_s = (
        max(0.0, time.time() - float(started)) if started is not None else 0.0
    )
    cost = finalize_bank_cost_diagnostics(
        state.get("cost_diagnostics") or empty_bank_cost_diagnostics(),
        accepted_count=len(approved),
        processing_time_seconds=runtime_s,
    )
    intent_diag = dict(state.get("intent_diagnostics") or empty_intent_diagnostics())
    catalog_exhausted = int(intent_diag.get("catalog_exhaustion_count") or 0) > 0
    audit = audit_bank_batch(
        blueprint,
        approved,
        failed,
        options_per_question=5,
        minimum_accepted_questions=state.get("minimum_accepted_questions"),
        budget_exhausted_reason=state.get("batch_budget_exhausted_reason"),
        generated_attempts=int(cost.get("generated_attempts") or 0),
        runtime_seconds=runtime_s,
        catalog_exhausted=catalog_exhausted,
    )
    sat = compute_bank_batch_saturation_diagnostics(
        seed_questions=state.get("bank_duplicate_seed_questions") or [],
        approved=approved,
        rejected_attempts=rejected,
    )
    diag = dict(state.get("refill_diagnostics") or empty_bank_refill_diagnostics())
    # Finalize diagnostic mirrors if target cycle never ran
    if not diag.get("accepted_after_normal_refill"):
        diag["accepted_after_normal_refill"] = diag.get(
            "accepted_after_initial_fill", len(approved)
        )
    if not diag.get("accepted_after_target_refill"):
        diag["accepted_after_target_refill"] = len(approved)
    accepted_n = max(1, len(approved)) if approved else 0
    gen_attempts = int(cost.get("generated_attempts") or 0)
    if approved:
        intent_diag["generated_attempts_per_accepted"] = round(
            gen_attempts / float(accepted_n), 2
        )
    sat["refill"] = diag
    sat["cost"] = cost
    sat["intent"] = intent_diag
    audit["saturation"] = sat
    audit["refill_diagnostics"] = diag
    audit["cost_diagnostics"] = cost
    audit["intent_diagnostics"] = intent_diag
    audit["answer_position"] = pos_diag
    logger.info(
        f"Bank batch audit status={audit.get('status')} "
        f"accepted={audit.get('accepted')}/{audit.get('requested')} "
        f"stop_reason={audit.get('stop_reason')} "
        f"min_target={audit.get('minimum_accepted_questions')} "
        f"min_reached={audit.get('minimum_target_reached')} "
        f"errors={len(audit.get('errors') or [])}; "
        f"saturation seeds={sat.get('existing_seed_count')} "
        f"dup_rejects={sat.get('duplicate_rejection_count')}; "
        f"refill fill={diag.get('accepted_after_initial_fill')} "
        f"normal={diag.get('accepted_after_normal_refill')} "
        f"target={diag.get('accepted_after_target_refill')}; "
        f"cost gen={cost.get('generated_attempts')} "
        f"early_dup={cost.get('duplicate_early_exits')} "
        f"blind={cost.get('blind_solver_calls')} "
        f"cog={cost.get('cognitive_quality_calls')} "
        f"llm={cost.get('total_llm_calls')}; "
        f"intent assigned={intent_diag.get('intents_assigned')} "
        f"retired={intent_diag.get('intents_retired_after_duplicate')} "
        f"accepted_from_intent={intent_diag.get('questions_accepted_from_assigned_intent')}"
    )
    return {
        "audit": audit,
        "approved": approved,
        "rejected_with_feedback": rejected,
        "refill_diagnostics": diag,
        "cost_diagnostics": cost,
        "intent_diagnostics": intent_diag,
    }


def _bank_record_from_approved(
    q: dict,
    *,
    batch_id: str,
    book_id: str,
    chapter_chunks: Dict[str, List[str]],
) -> dict:
    """Map an approved slot record to question_bank persistence shape."""
    chapter = q.get("chapter")
    q_num = int(q.get("question_number") or 0)
    attempts = int(q.get("generation_attempts") or 1)
    chunks = chapter_chunks.get(str(chapter), [])
    source_chunk_index = q.get("source_chunk_index")
    if source_chunk_index is None and chunks:
        source_chunk_index = (q_num - 1 + max(attempts, 1) - 1) % len(chunks)

    return {
        "question": q.get("question", ""),
        "type": q.get("type", "mcq"),
        "answer_type": q.get("answer_type"),
        "options": q.get("options"),
        "correct_indices": q.get("correct_indices"),
        "answer": q.get("answer", ""),
        "explanation": q.get("explanation", ""),
        "topic": q.get("topic", ""),
        "sub_topic": q.get("sub_topic"),
        "grade": q.get("grade"),
        "subject": q.get("subject"),
        "chapter": q.get("chapter"),
        "chapter_title": q.get("chapter_title"),
        "section_ref": q.get("section_ref") or q.get("chapter_title"),
        "target_difficulty": q.get("target_difficulty"),
        "validated_cognitive_difficulty": q.get("validated_cognitive_difficulty"),
        "difficulty": q.get("target_difficulty"),
        "difficulty_score": q.get("difficulty_score"),
        "difficulty_scores": q.get("difficulty_scores"),
        "validation_status": q.get("validation_status"),
        "validation_reasons": q.get("validation_reasons"),
        "generation_attempts": q.get("generation_attempts"),
        "batch_id": batch_id,
        "book_id": book_id,
        "source_chunk_index": source_chunk_index,
        "learning_outcome": q.get("learning_outcome"),
        "blind_solver_answer": q.get("blind_solver_answer"),
        "answer_agreement": q.get("answer_agreement"),
        "information_sufficient": q.get("information_sufficient"),
        "arithmetic_consistent": q.get("arithmetic_consistent"),
        "no_unsupported_claims": q.get("no_unsupported_claims"),
        "option_defensibility": q.get("option_defensibility"),
        "distractors_ok": q.get("distractors_ok"),
        "terminology_grounded": q.get("terminology_grounded"),
    }


async def persist_bank_batch(state: PaperState) -> dict:
    """Persist every passed question to the bank (partial batches included)."""
    approved = state.get("approved") or []
    batch_id = str(state.get("batch_id") or "")
    book_id = str(state.get("book_id") or "")
    chapter_chunks = state.get("chapter_chunks") or {}

    from open_notebook.database.repository import repo_query
    from open_notebook.graphs.question_paper_blueprint import normalize_question_text

    existing_rows = await repo_query(
        "SELECT id, question FROM question_bank WHERE batch_id = $batch_id",
        {"batch_id": batch_id},
    )
    saved_ids: List[str] = [str(r["id"]) for r in (existing_rows or []) if r.get("id")]
    saved_texts = {
        normalize_question_text(str(r.get("question") or ""))
        for r in (existing_rows or [])
    }

    for q in approved:
        if q.get("validation_status") != "passed":
            continue
        text_key = normalize_question_text(str(q.get("question") or ""))
        if not text_key or text_key in saved_texts:
            continue
        record = _bank_record_from_approved(
            q,
            batch_id=batch_id,
            book_id=book_id,
            chapter_chunks=chapter_chunks,
        )
        try:
            saved = await QuestionRecord.save_one(record)
            if saved and saved.id:
                saved_ids.append(str(saved.id))
                saved_texts.add(text_key)
                logger.info(
                    f"Bank batch saved Q{q.get('question_number')} → {saved.id}"
                )
        except Exception as e:
            logger.warning(f"Failed to save bank batch question: {e}")

    new_count = len(saved_ids) - len(existing_rows or [])
    logger.info(
        f"Bank batch persist: {new_count} new question(s); {len(saved_ids)} total for batch"
    )
    return {"persisted_question_ids": saved_ids}


def _needs_refill_bank(state: PaperState) -> str:
    if not state.get("failed_slots"):
        return "mark_after_normal_refill"
    # Additional batch-level ceiling: skip further refill attempts when exhausted.
    if state.get("bank_batch_mode") and bank_batch_budget_exhausted(state):
        return "mark_after_normal_refill"
    return "refill_slots"


def _needs_target_refill(state: PaperState) -> str:
    """Enter target refill only when still missing and budget remains."""
    if not state.get("bank_batch_mode"):
        return "audit_bank_batch"
    approved = state.get("approved") or []
    failed = state.get("failed_slots") or []
    if not failed:
        return "audit_bank_batch"
    raw = state.get("bank_batch_blueprint") or {}
    try:
        blueprint = bank_batch_from_dict(raw)
        requested = int(blueprint.total_questions)
    except Exception:
        requested = len(state.get("slots") or []) or 0
    if len(approved) >= requested:
        return "audit_bank_batch"
    if bank_batch_budget_exhausted(state):
        return "audit_bank_batch"
    cycles_done = int(state.get("target_refill_cycles_done") or 0)
    max_cycles = int(
        state.get("max_target_refill_cycles")
        if state.get("max_target_refill_cycles") is not None
        else bank_target_refill_cycles()
    )
    if cycles_done >= max_cycles or max_cycles <= 0:
        return "audit_bank_batch"
    return "bank_target_refill"


def build_question_bank_batch_graph():
    graph = StateGraph(PaperState)

    graph.add_node("prepare_bank_batch", prepare_bank_batch)
    graph.add_node("fill_slots", fill_slots)
    graph.add_node("mark_after_fill", mark_after_fill)
    graph.add_node("refill_slots", refill_slots)
    graph.add_node("mark_after_normal_refill", mark_after_normal_refill)
    graph.add_node("bank_target_refill", bank_target_refill)
    graph.add_node("audit_bank_batch", audit_bank_batch_node)
    graph.add_node("persist_bank_batch", persist_bank_batch)

    graph.add_edge(START, "prepare_bank_batch")
    graph.add_edge("prepare_bank_batch", "fill_slots")
    graph.add_edge("fill_slots", "mark_after_fill")
    graph.add_conditional_edges(
        "mark_after_fill",
        _needs_refill_bank,
        {
            "refill_slots": "refill_slots",
            "mark_after_normal_refill": "mark_after_normal_refill",
        },
    )
    graph.add_edge("refill_slots", "mark_after_normal_refill")
    graph.add_conditional_edges(
        "mark_after_normal_refill",
        _needs_target_refill,
        {
            "bank_target_refill": "bank_target_refill",
            "audit_bank_batch": "audit_bank_batch",
        },
    )
    # Allow up to max_target_refill_cycles by looping until budget exhausted
    # or no missing slots remain (default still 1 via env/default).
    graph.add_conditional_edges(
        "bank_target_refill",
        _needs_target_refill,
        {
            "bank_target_refill": "bank_target_refill",
            "audit_bank_batch": "audit_bank_batch",
        },
    )
    graph.add_edge("audit_bank_batch", "persist_bank_batch")
    graph.add_edge("persist_bank_batch", END)

    return graph.compile()


question_bank_batch_graph = build_question_bank_batch_graph()
