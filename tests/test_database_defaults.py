"""The job queue uses Open Notebook's namespace and database defaults (#1466)."""

import pytest
from surreal_commands.core.service import CommandService

from open_notebook.database.repository import (
    apply_database_defaults,
    get_database_name,
    get_database_namespace,
)


@pytest.fixture
def clean_env(monkeypatch):
    # setenv first, so monkeypatch also undoes what the helper writes.
    for name in ("SURREAL_NAMESPACE", "SURREAL_DATABASE"):
        monkeypatch.setenv(name, "placeholder")
        monkeypatch.delenv(name)
    return monkeypatch


def _queue_target():
    service = CommandService(db_url="ws://localhost:8000/rpc")
    return service.db_namespace, service.db_database


def test_unset_variables_resolve_to_the_same_database_for_both(clean_env):
    # Without the helper, surreal-commands falls back to test/test.
    assert _queue_target() == ("test", "test")

    apply_database_defaults()

    assert _queue_target() == (get_database_namespace(), get_database_name())
    assert _queue_target() == ("open_notebook", "open_notebook")


@pytest.mark.parametrize("empty", [False, True])
def test_explicit_values_are_kept_and_empty_ones_get_the_default(clean_env, empty):
    clean_env.setenv("SURREAL_NAMESPACE", "team")
    if empty:
        # Open Notebook reads an empty value as unset; the queue must too.
        clean_env.setenv("SURREAL_DATABASE", "")
    else:
        clean_env.setenv("SURREAL_DATABASE", "notes")

    apply_database_defaults()

    expected_db = "open_notebook" if empty else "notes"
    assert _queue_target() == ("team", expected_db)
    assert (get_database_namespace(), get_database_name()) == ("team", expected_db)
