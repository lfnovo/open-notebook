"""Unit tests for smart-chat retrieval assembly (pure functions)."""

from open_notebook.graphs import chat_retrieval as cr


def test_merge_and_cap_dedupes_keeping_highest_similarity():
    q1 = [
        {"id": "source:a", "similarity": 0.5, "matches": ["a1"]},
        {"id": "source:b", "similarity": 0.9, "matches": ["b1"]},
    ]
    q2 = [
        {"id": "source:a", "similarity": 0.8, "matches": ["a2"]},  # higher dup
        {"id": "source:c", "similarity": 0.7, "matches": ["c1"]},
    ]
    merged = cr.merge_and_cap([q1, q2], cap=10)
    ids = [h["id"] for h in merged]
    # Deduped to 3, ordered by similarity desc: b(0.9), a(0.8), c(0.7)
    assert ids == ["source:b", "source:a", "source:c"]
    a = next(h for h in merged if h["id"] == "source:a")
    assert a["similarity"] == 0.8  # kept the higher-scoring copy


def test_merge_and_cap_respects_cap_and_drops_none_ids():
    hits = [
        {"id": "source:a", "similarity": 0.9},
        {"id": None, "similarity": 0.99},
        {"id": "source:b", "similarity": 0.8},
        {"id": "source:c", "similarity": 0.7},
    ]
    merged = cr.merge_and_cap([hits], cap=2)
    assert [h["id"] for h in merged] == ["source:a", "source:b"]


def test_format_retrieved_includes_ids_for_citation():
    hits = [{"id": "source:x", "title": "Book One", "matches": ["chunk one", "chunk two"]}]
    out = cr.format_retrieved(hits)
    assert "[source:x]" in out
    assert "Book One" in out
    assert "chunk one" in out and "chunk two" in out


def test_format_retrieved_empty():
    assert cr.format_retrieved([]) == ""


def test_format_history_handles_dicts_and_labels_roles():
    msgs = [
        {"type": "human", "content": "what is positioning"},
        {"type": "ai", "content": "positioning is..."},
        {"type": "human", "content": "what about pricing"},
    ]
    out = cr.format_history(msgs, turns=6)
    assert "User: what is positioning" in out
    assert "Assistant: positioning is..." in out
    assert out.index("positioning") < out.index("pricing")


def test_format_history_empty():
    assert cr.format_history([]) == ""
