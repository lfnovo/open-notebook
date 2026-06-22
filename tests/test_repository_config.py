from open_notebook.database.repository import (
    get_database_name,
    get_database_namespace,
    get_database_password,
)


def test_database_namespace_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("SURREAL_NAMESPACE", raising=False)

    assert get_database_namespace() == "open_notebook"


def test_database_namespace_defaults_when_empty(monkeypatch):
    monkeypatch.setenv("SURREAL_NAMESPACE", "")

    assert get_database_namespace() == "open_notebook"


def test_database_name_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("SURREAL_DATABASE", raising=False)

    assert get_database_name() == "open_notebook"


def test_database_name_defaults_when_empty(monkeypatch):
    monkeypatch.setenv("SURREAL_DATABASE", "")

    assert get_database_name() == "open_notebook"


def test_database_password_defaults_when_empty(monkeypatch):
    monkeypatch.setenv("SURREAL_PASSWORD", "")
    monkeypatch.setenv("SURREAL_PASS", "")

    assert get_database_password() == "root"
