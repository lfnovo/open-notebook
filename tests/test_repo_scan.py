"""Tests for the repo-review filesystem access layer (security boundary + grep)."""

import importlib

import pytest

import open_notebook.config as config
from open_notebook.exceptions import ConfigurationError, InvalidInputError


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A small fixture repo inside an allowed root."""
    root = tmp_path / "allowed"
    proj = root / "myproject"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "app.py").write_text(
        "import os\n"
        "PASSWORD = 'hunter2'  # hardcoded secret\n"
        "def run():\n"
        "    eval(user_input)\n"
    )
    (proj / "README.md").write_text("# My Project\nSafe content.\n")
    (proj / "node_modules").mkdir()
    (proj / "node_modules" / "junk.js").write_text("PASSWORD = 'should-be-ignored'\n")

    # Point the allowlist at the allowed root and reload modules that captured it.
    monkeypatch.setenv("REPO_REVIEW_ALLOWED_ROOTS", str(root))
    importlib.reload(config)
    import open_notebook.utils.repo_scan as rs

    importlib.reload(rs)
    yield proj, rs
    # Restore default module state for other tests.
    monkeypatch.delenv("REPO_REVIEW_ALLOWED_ROOTS", raising=False)
    importlib.reload(config)
    importlib.reload(rs)


def test_validate_accepts_path_within_root(repo):
    proj, rs = repo
    resolved = rs.validate_repo_path(str(proj))
    assert resolved == proj.resolve()


def test_validate_rejects_path_outside_root(repo, tmp_path):
    _, rs = repo
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    with pytest.raises(InvalidInputError):
        rs.validate_repo_path(str(outside))


def test_validate_rejects_traversal_escape(repo, tmp_path):
    proj, rs = repo
    # ../../ climbs out of the allowed root; resolve() exposes the escape.
    escape = str(proj / ".." / ".." / "..")
    with pytest.raises(InvalidInputError):
        rs.validate_repo_path(escape)


def test_validate_rejects_missing_path(repo):
    proj, rs = repo
    with pytest.raises(InvalidInputError):
        rs.validate_repo_path(str(proj / "does-not-exist"))


def test_validate_requires_configured_roots(monkeypatch):
    monkeypatch.setenv("REPO_REVIEW_ALLOWED_ROOTS", "")
    importlib.reload(config)
    import open_notebook.utils.repo_scan as rs

    importlib.reload(rs)
    with pytest.raises(ConfigurationError):
        rs.validate_repo_path("/tmp")
    monkeypatch.delenv("REPO_REVIEW_ALLOWED_ROOTS", raising=False)
    importlib.reload(config)
    importlib.reload(rs)


def test_grep_finds_matches_and_skips_ignored_dirs(repo):
    proj, rs = repo
    root = rs.validate_repo_path(str(proj))
    hits = rs.grep_repo(root, [r"PASSWORD\s*="])
    files = {h.file for h in hits}
    assert any("app.py" in f for f in files)
    # node_modules must be excluded by the ignore globs / walk pruning.
    assert not any("node_modules" in f for f in files)


def test_grep_multiple_patterns(repo):
    proj, rs = repo
    root = rs.validate_repo_path(str(proj))
    hits = rs.grep_repo(root, [r"eval\(", r"PASSWORD"])
    matched = "\n".join(h.snippet for h in hits)
    assert "eval(" in matched
    assert "PASSWORD" in matched


def test_grep_empty_patterns_returns_nothing(repo):
    proj, rs = repo
    root = rs.validate_repo_path(str(proj))
    assert rs.grep_repo(root, []) == []


def test_build_file_tree_filters_noise(repo):
    proj, rs = repo
    root = rs.validate_repo_path(str(proj))
    tree = rs.build_file_tree(root)
    assert "src/app.py" in tree or "src\\app.py" in tree
    assert not any("node_modules" in f for f in tree)
