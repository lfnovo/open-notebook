from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id


def test_plain_id_is_parsed():
    assert ensure_record_id("source:abc") == RecordID("source", "abc")


def test_double_prefixed_id_is_collapsed():
    assert ensure_record_id("source:source:abc") == RecordID("source", "abc")


def test_repeated_prefix_is_collapsed():
    assert ensure_record_id("source:source:source:abc") == RecordID("source", "abc")


def test_record_id_passes_through():
    rid = RecordID("note", "xyz")
    assert ensure_record_id(rid) is rid
