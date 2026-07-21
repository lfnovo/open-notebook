#!/usr/bin/env python3
"""Fail the build when a new GPL/AGPL dependency enters the tree.

This is the licensing drift guard for the commercial fork (WP0 task 6). It is
deliberately a *drift* guard, not a clean-tree assertion: the fork already
inherits a handful of copyleft transitive dependencies from upstream, each
recorded in ALLOWED below with the reason it is tolerated. Anything copyleft
that is NOT on that list fails the build.

Two rules:
  1. AGPL is never allowed, not even via the allowlist. A network-copyleft
     dependency in a hosted SaaS is the one outcome this program cannot ship.
  2. Any other GPL-family license must be explicitly allowlisted, with a
     justification, before it can enter the tree.

Scans both ecosystems:
  - Python   via `pip-licenses --format=json`
  - Frontend via `license-checker --production --json` (run in frontend/)

Run locally:  uv run python scripts/check_licenses.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

# Matches the GPL family. Word-boundary anchored so "GPL" inside an unrelated
# token can't trigger, and so LGPL/AGPL are caught by their own patterns.
COPYLEFT_RE = re.compile(r"\b(?:A?GPL|LGPL|GNU (?:Lesser |Affero )?General Public)", re.I)
AGPL_RE = re.compile(r"\b(?:AGPL|GNU Affero)", re.I)

# A permissive alternative in a multi-license string means we can take that
# option instead of the copyleft one, so the package is not a copyleft problem.
PERMISSIVE_ALTERNATIVE_RE = re.compile(
    r"\b(?:MIT|BSD|Apache|ISC|Python Software Foundation|Public Domain|Zlib|MPL)",
    re.I,
)


@dataclass(frozen=True)
class Allowance:
    """A copyleft package we knowingly tolerate, and why."""

    name: str
    reason: str


# Inherited from upstream at the `upstream-base` fork point. Every entry here
# is a deliberate, reviewed decision — do not add to this list to make CI green
# without a licensing review. See docs/DEV_SETUP.md.
ALLOWED: dict[str, Allowance] = {
    # --- Python ---
    "pycountry": Allowance(
        "pycountry",
        "LGPL-2.1-only. Safe while used as an unmodified, separately-installed "
        "dependency (no static linking, no vendored source). WP1 asserts it "
        "stays unmodified. Do not vendor or patch it.",
    ),
    "chardet": Allowance(
        "chardet",
        "LGPL-2.1+, pulled in transitively by readability-lxml. Unmodified "
        "library used over its public API; LGPL obligations are satisfied by "
        "not modifying and not static-linking it.",
    ),
    "docutils": Allowance(
        "docutils",
        "Multi-licensed BSD / GPL / Public Domain (via rich-rst). We take it "
        "under the BSD option, so no copyleft obligation attaches.",
    ),
    "asciidoc": Allowance(
        "asciidoc",
        "GPLv2+, pulled in transitively by content-core. FLAGGED FOR WP1 LEGAL "
        "REVIEW: this is the one strong-copyleft runtime dependency inherited "
        "from upstream. It is invoked as a separate document-conversion tool "
        "rather than imported as a library, which is the usual basis for "
        "treating it as an aggregate rather than a derived work -- but that "
        "position needs sign-off, or content-core needs to be configured to "
        "drop it, before commercial distribution.",
    ),
    # --- Frontend ---
    # sharp ships a per-platform binary package (@img/sharp-<platform>-<arch>),
    # so the exact name differs between a Windows dev box and Linux CI. The
    # prefix match below covers every variant.
    "@img/sharp": Allowance(
        "@img/sharp",
        "Apache-2.0 AND LGPL-3.0-or-later -- the LGPL part is libvips, used as "
        "an unmodified shared library by Next.js image optimization. Standard "
        "commercial use; do not modify or static-link libvips.",
    ),
}


class LicenseScanError(RuntimeError):
    """A scanner could not be run at all (missing tool, bad output)."""


def _is_allowed(package_name: str) -> Allowance | None:
    """Exact match first, then prefix match for platform-variant packages."""
    if package_name in ALLOWED:
        return ALLOWED[package_name]
    for key, allowance in ALLOWED.items():
        if package_name.startswith(key):
            return allowance
    return None


def _classify(package: str, license_text: str) -> str | None:
    """Return a violation reason, or None if this package is acceptable."""
    if not COPYLEFT_RE.search(license_text):
        return None

    if AGPL_RE.search(license_text):
        # Never allowlistable, regardless of ALLOWED.
        return "AGPL is never permitted in this product (network copyleft)."

    if PERMISSIVE_ALTERNATIVE_RE.search(license_text):
        # Multi-licensed with a permissive option we can elect.
        return None

    if _is_allowed(package):
        return None

    return "copyleft license not on the reviewed allowlist"


def scan_python() -> list[tuple[str, str, str]]:
    """Return [(package, license, reason)] for Python violations."""
    try:
        raw = subprocess.run(
            [sys.executable, "-m", "piplicenses", "--format=json"],
            capture_output=True,
            check=True,
            cwd=REPO_ROOT,
            # Decode explicitly: package metadata contains bytes the Windows
            # console codepage can't decode, which makes bare text=True raise.
            encoding="utf-8",
            errors="replace",
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise LicenseScanError(
            "pip-licenses could not be run. Install it with "
            "`uv sync` (it is in the dev dependency group)."
        ) from exc

    try:
        packages = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LicenseScanError(f"pip-licenses produced invalid JSON: {exc}") from exc

    violations = []
    for pkg in packages:
        name = pkg.get("Name", "")
        license_text = pkg.get("License", "")
        reason = _classify(name, license_text)
        if reason:
            violations.append((name, license_text, reason))
    return violations


def scan_frontend() -> list[tuple[str, str, str]]:
    """Return [(package, license, reason)] for frontend violations."""
    if not (FRONTEND_DIR / "node_modules").is_dir():
        raise LicenseScanError(
            f"{FRONTEND_DIR / 'node_modules'} is missing. Run `npm ci` in "
            "frontend/ before scanning."
        )

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise LicenseScanError("npx not found on PATH; cannot scan frontend licenses.")

    try:
        raw = subprocess.run(
            [npx, "--yes", "license-checker", "--production", "--json"],
            capture_output=True,
            check=True,
            cwd=FRONTEND_DIR,
            encoding="utf-8",
            errors="replace",
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise LicenseScanError(
            f"license-checker failed: {exc.stderr.strip() or exc}"
        ) from exc

    try:
        packages = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LicenseScanError(f"license-checker produced invalid JSON: {exc}") from exc

    # license-checker keys are "name@version"; our own package is not a
    # dependency, so skip it (it is intentionally UNLICENSED/private).
    own_name = json.loads((FRONTEND_DIR / "package.json").read_text())["name"]

    violations = []
    for key, meta in packages.items():
        name = key.rsplit("@", 1)[0]
        if name == own_name:
            continue
        license_text = meta.get("licenses", "")
        if isinstance(license_text, list):
            license_text = " AND ".join(license_text)
        reason = _classify(name, license_text)
        if reason:
            violations.append((name, license_text, reason))
    return violations


def main() -> int:
    failed = False
    all_violations: list[tuple[str, str, str, str]] = []

    for ecosystem, scanner in (("Python", scan_python), ("Frontend", scan_frontend)):
        try:
            violations = scanner()
        except LicenseScanError as exc:
            # A scanner that cannot run is a failure, not a pass. Silently
            # skipping would turn this guard into a no-op.
            print(f"ERROR: {ecosystem} license scan could not run: {exc}")
            failed = True
            continue

        print(f"{ecosystem}: scanned, {len(violations)} violation(s).")
        all_violations.extend((ecosystem, *v) for v in violations)

    if all_violations:
        failed = True
        print("\nLicense violations found:\n")
        for ecosystem, name, license_text, reason in all_violations:
            print(f"  [{ecosystem}] {name}")
            print(f"      license: {license_text}")
            print(f"      reason:  {reason}")
        print(
            "\nA new copyleft dependency entered the tree. Either remove it, or "
            "-- after a licensing review -- add it to ALLOWED in "
            "scripts/check_licenses.py with a written justification.\n"
            "AGPL can never be allowlisted."
        )

    if failed:
        return 1

    print("\nLicense check passed: no unreviewed copyleft dependencies.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
