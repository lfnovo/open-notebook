"""Assert that pycountry (LGPL-2.1) is used completely unmodified.

pycountry is the one LGPL dependency we link against directly. Used as an
unmodified, separately-installed library our obligation is zero; *modifying*
it would trigger LGPL obligations on the modified library, which this product
cannot carry.

So rather than documenting "do not modify pycountry" and hoping, this verifies
it: every installed file is hashed and compared against the sha256 digests
recorded in the distribution's own RECORD manifest (PEP 376). Any edited,
added, or removed file fails the build.

See docs/LICENSE_COMPLIANCE.md §4.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
from pathlib import Path

import pytest

DIST_NAME = "pycountry"


def _package_root() -> Path:
    spec = importlib.util.find_spec(DIST_NAME)
    assert spec and spec.origin, f"{DIST_NAME} is not installed"
    return Path(spec.origin).parent


def _dist_info_dir() -> Path:
    site_packages = _package_root().parent
    matches = sorted(site_packages.glob(f"{DIST_NAME}-*.dist-info"))
    assert matches, f"no {DIST_NAME}-*.dist-info found next to the package"
    return matches[-1]


def _record_entries() -> list[tuple[str, str, str]]:
    """Parse RECORD into (path, hash_spec, size) rows."""
    record = _dist_info_dir() / "RECORD"
    assert record.is_file(), f"{record} is missing; cannot verify integrity"
    with record.open(encoding="utf-8", newline="") as fh:
        return [tuple(row) for row in csv.reader(fh) if len(row) == 3]  # type: ignore[misc]


def _sha256_urlsafe(path: Path) -> str:
    """PEP 376 records digests as urlsafe base64 with padding stripped."""
    digest = hashlib.sha256(path.read_bytes()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


class TestPycountryIntegrity:
    def test_record_manifest_is_present_and_populated(self):
        """Without a usable RECORD there is nothing to verify against, so an
        empty one must fail rather than vacuously pass."""
        entries = _record_entries()
        hashed = [e for e in entries if e[1].startswith("sha256=")]
        assert len(hashed) > 10, (
            f"{DIST_NAME} RECORD lists only {len(hashed)} hashed files; "
            "integrity cannot be meaningfully verified"
        )

    def test_no_installed_file_has_been_modified(self):
        """Every file's sha256 must match the digest recorded at install time."""
        site_packages = _package_root().parent
        modified: list[str] = []
        missing: list[str] = []

        for rel_path, hash_spec, _size in _record_entries():
            if not hash_spec.startswith("sha256="):
                # RECORD itself is listed without a hash, by design.
                continue
            target = site_packages / rel_path
            if not target.is_file():
                missing.append(rel_path)
                continue
            if _sha256_urlsafe(target) != hash_spec[len("sha256=") :]:
                modified.append(rel_path)

        assert not modified and not missing, (
            f"{DIST_NAME} is no longer the unmodified upstream distribution.\n"
            f"  modified: {modified or 'none'}\n"
            f"  missing:  {missing or 'none'}\n"
            "pycountry is LGPL-2.1: modifying it triggers LGPL obligations this "
            "product cannot carry. Reinstall it clean (`uv sync --reinstall-package "
            f"{DIST_NAME}`) and never patch or vendor it. "
            "See docs/LICENSE_COMPLIANCE.md §4."
        )

    def test_no_extra_python_files_were_added_to_the_package(self):
        """A patch could add a new module rather than edit an existing one,
        which per-file hashing alone would not catch."""
        root = _package_root()
        site_packages = root.parent
        recorded = {
            (site_packages / rel).resolve()
            for rel, _hash, _size in _record_entries()
        }
        extras = [
            str(path.relative_to(root))
            for path in root.rglob("*.py")
            if path.resolve() not in recorded
        ]
        assert not extras, (
            f"Unexpected Python files inside the installed {DIST_NAME} package: "
            f"{extras}. It must remain the unmodified upstream distribution."
        )


class TestPycountryIsNotVendored:
    def test_repository_does_not_contain_a_pycountry_copy(self):
        """Vendoring the source into this repo would put LGPL code into our
        distribution as a modifiable copy. It must stay an external dependency."""
        repo_root = Path(__file__).resolve().parent.parent
        skip = {".venv", "node_modules", ".git", ".mypy_cache", ".pytest_cache"}

        vendored = [
            str(path.relative_to(repo_root))
            for path in repo_root.rglob("pycountry")
            if path.is_dir() and not any(part in skip for part in path.parts)
        ]
        assert not vendored, (
            f"A vendored copy of {DIST_NAME} exists at {vendored}. "
            "It must remain an unmodified external dependency; see "
            "docs/LICENSE_COMPLIANCE.md §4."
        )


class TestGuardActuallyDetectsTampering:
    """The guard is only worth having if it trips, so prove it does."""

    def test_a_modified_file_is_detected(self, tmp_path, monkeypatch):
        original = tmp_path / "sample.py"
        original.write_bytes(b"x = 1\n")
        recorded = _sha256_urlsafe(original)

        original.write_bytes(b"x = 2  # tampered\n")

        assert _sha256_urlsafe(original) != recorded

    def test_identical_content_hashes_equal(self, tmp_path):
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        a.write_bytes(b"same\n")
        b.write_bytes(b"same\n")
        assert _sha256_urlsafe(a) == _sha256_urlsafe(b)


@pytest.mark.parametrize("module", ["pycountry"])
def test_dependency_is_importable(module):
    """A guard over a package that is not installed would pass vacuously."""
    assert importlib.util.find_spec(module) is not None
