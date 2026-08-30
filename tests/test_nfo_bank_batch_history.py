"""Read-only Question Bank batch history serialization. Does not generate."""

from api.question_paper_service import serialize_bank_batch_summary


def test_serialize_bank_batch_summary_maps_history_fields():
    row = {
        "id": "question_bank_batch:qkozkavx2rfkorgleo0h",
        "book_id": "question_book:4b46dax7tgo86c3sgaz0",
        "grade": "10",
        "subject": "PFH 2026 Grade 10",
        "chapter": 2,
        "difficulty": "medium",
        "requested": 15,
        "accepted": 12,
        "failed": 3,
        "status": "completed_partial",
        "created": "2026-08-30T01:00:00Z",
        "error_message": None,
        "stop_reason": "catalog_exhausted",
        "saved_question_ids": ["question_bank:a", "question_bank:b"],
    }
    summary = serialize_bank_batch_summary(row)
    assert summary["batch_id"] == "question_bank_batch:qkozkavx2rfkorgleo0h"
    assert summary["grade"] == "10"
    assert summary["book_id"] == "question_book:4b46dax7tgo86c3sgaz0"
    assert summary["chapter"] == 2
    assert summary["difficulty"] == "medium"
    assert summary["requested"] == 15
    assert summary["accepted"] == 12
    assert summary["status"] == "completed_partial"
    assert summary["stop_reason"] == "catalog_exhausted"
    assert summary["created"] == "2026-08-30T01:00:00Z"
    assert summary["saved_question_ids"] == ["question_bank:a", "question_bank:b"]


def test_serialize_bank_batch_summary_falls_back_to_total_questions():
    summary = serialize_bank_batch_summary(
        {
            "id": "question_bank_batch:x",
            "total_questions": 15,
            "saved_question_ids": ["q1", "q2", "q3"],
            "status": "completed",
        }
    )
    assert summary["requested"] == 15
    assert summary["accepted"] == 3
    assert summary["failed"] == 0
    assert summary["book_id"] is None


def test_serialize_reads_stop_reason_from_audit_without_reclassifying_status():
    summary = serialize_bank_batch_summary(
        {
            "id": "question_bank_batch:x",
            "status": "completed_partial",
            "requested": 15,
            "accepted": 12,
            "audit": {"stop_reason": "normal_partial_completion"},
        }
    )
    assert summary["status"] == "completed_partial"
    assert summary["stop_reason"] == "normal_partial_completion"


def test_serialize_bank_batch_summary_does_not_invent_generation_fields():
    summary = serialize_bank_batch_summary({"id": "question_bank_batch:x", "status": "running"})
    assert "blueprint" not in summary
    assert summary["requested"] == 0
    assert summary["accepted"] == 0
    assert summary["saved_question_ids"] == []
