#!/usr/bin/env python3
"""Generate THIRD-PARTY-NOTICES.md from the actual installed dependency tree.

Attribution has to be regenerable, not hand-maintained: a hand-written notices
file silently goes stale on the next dependency bump, and a stale attribution
file is a compliance problem rather than a cosmetic one. So this reads the real
installed metadata from both ecosystems and rewrites the file wholesale.

  - Python   via `pip-licenses` (name, version, license, author, project URL)
  - Frontend via `license-checker --production` (same, from package metadata)

Entries that cannot be derived from package metadata -- currently SurrealDB,
which we depend on as a container image rather than as a package -- are held in
MANUAL_ENTRIES below and merged into the output.

Run:      uv run python scripts/generate_notices.py
Check:    uv run python scripts/generate_notices.py --check   (CI: fails if stale)

Requires `npm ci` to have been run in frontend/ so node_modules exists.

MUST BE RUN ON LINUX. Dependency resolution is platform-specific, and what we
distribute is the Linux container image. Running this on Windows produces a
notices file listing pywin32/win32_setctime/sharp-win32 -- packages we never
ship -- while omitting their Linux counterparts, which is an inaccurate legal
notice. From a Windows host, regenerate inside a container; the exact command
is in docs/LICENSE_COMPLIANCE.md.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
OUTPUT = REPO_ROOT / "THIRD-PARTY-NOTICES.md"

UNKNOWN = {"UNKNOWN", "", None, "UNKNOWN LICENSE"}

# Packages whose declared metadata is missing or unusable. Each value records
# WHERE the real license was read from, so every override is auditable rather
# than asserted. Verify before adding: read the package's own LICENSE file.
LICENSE_OVERRIDES: dict[str, tuple[str, str]] = {
    "caio": (
        "Apache-2.0",
        "no license in package metadata; Apache 2.0 per its own COPYING file",
    ),
    "content-core": (
        "MIT",
        "no license classifier in package metadata; MIT per its own LICENSE "
        "file (Copyright (c) 2025 Luis Novo)",
    ),
}

# Present in the dev/CI virtualenv but deliberately NOT shipped, so listing
# them here as distributed dependencies would be factually wrong.
EXCLUDED: dict[str, str] = {
    "asciidoc": (
        "GPLv2+. Declared as a hard dependency by content-core but never "
        "imported by it, and purged from every shipped artifact by the "
        "Dockerfile. `uv sync` still installs it into the development and CI "
        "virtualenv, but no GPL code is distributed. Removal proposed upstream "
        "in lfnovo/content-core#58."
    ),
}


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    license: str
    author: str
    url: str

    def as_row(self) -> str:
        def cell(value: str) -> str:
            # Pipes would break the table; some author fields contain them.
            return (value or "-").replace("|", "\\|").strip() or "-"

        url = cell(self.url)
        link = f"[link]({url})" if url.startswith("http") else "-"
        return (
            f"| {cell(self.name)} | {cell(self.version)} | {cell(self.license)} "
            f"| {cell(self.author)} | {link} |"
        )


# Dependencies that are not installed packages, so no metadata exists to read.
MANUAL_ENTRIES = """\
### SurrealDB (database engine)

- **Version:** v2 (see `docker-compose.yml`)
- **License:** Business Source License 1.1 (BSL 1.1) — *source-available, not
  OSI-approved open source*
- **Copyright:** SurrealDB Ltd
- **Project:** <https://github.com/surrealdb/surrealdb>
- **License text:** <https://github.com/surrealdb/surrealdb/blob/main/LICENSE>

SurrealDB is the one non-permissive component in the stack, and it is a
deliberate, reviewed choice. Its terms:

- **Commercial embedding is permitted and free.** We may embed it in the
  product, ship that product to customers, and run it as a hosted service at
  any scale. **No license purchase is required for our model.**
- **The one prohibition:** offering SurrealDB *itself* as a managed
  database-as-a-service. We do not do this.
- **Automatic conversion:** each release becomes Apache 2.0 four years after
  its release date.

**How we distribute it — dependency, not redistribution.** We pull the official
`surrealdb/surrealdb:v2` image from Docker Hub as a separate container
(`docker-compose.yml`). We do **not** bundle the SurrealDB binary into our own
image in the default deployment, so we redistribute no BSL-licensed code.

**⚠️ The single-container variant is the exception.** `Dockerfile` target
`single` copies the SurrealDB binary in (`COPY --from=surreal-binary /surreal`).
That image **does** redistribute BSL-licensed code, so **the BSL license text
must be included inside any artifact built from that target** before it is
shipped to a customer. See `docs/LICENSE_COMPLIANCE.md`.
"""

HEADER = """\
# Third-Party Notices

This product, **{product}**, is a commercial derivative of
[Open Notebook](https://github.com/lfnovo/open-notebook) by Luis Novo, used
under the MIT License. See [LICENSE](LICENSE) — the upstream copyright is
retained there, as the MIT License requires.

This file enumerates every third-party dependency, its version, license,
and copyright holder, satisfying the attribution requirements of the
permissive licenses across the stack in one place.

> **Generated file — do not edit by hand.**
> Regenerate with `uv run python scripts/generate_notices.py`.
> Last generated: {generated} against the locked dependency tree.
> Entries that have no package metadata (SurrealDB) are maintained in
> `MANUAL_ENTRIES` in that script.
>
> **Must be generated on Linux.** The dependency tree is platform-specific —
> a Windows machine resolves `pywin32`, `win32_setctime`,
> `@img/sharp-win32-x64` and `@next/swc-win32-x64-msvc`, none of which ship in
> our Linux container, while omitting the Linux binaries that do. Since what we
> distribute is the Linux image, generating this file anywhere else produces an
> inaccurate notice. CI verifies it with `--check` on Linux; see
> `docs/LICENSE_COMPLIANCE.md` for how to regenerate from a Windows host.

The "Copyright" column reports each package's declared author or maintainer,
which is the copyright holder that package metadata exposes. Where a project
declares no author, it shows `-`; the authoritative notice is then the
LICENSE file in the package itself.

---

## Licenses in use

{summary}

No GPL or AGPL-licensed code is distributed in this product. That is enforced
on every pull request by `scripts/check_licenses.py`, which fails the build on
any copyleft dependency not on its reviewed allowlist; AGPL can never be
allowlisted. See [docs/LICENSE_COMPLIANCE.md](docs/LICENSE_COMPLIANCE.md).

### Installed for development but not distributed

These are present in the development and CI virtualenv but are removed from
every shipped artifact, so they are not listed as dependencies above.

{excluded}

### Licenses corrected from package metadata

These packages declare no usable license in their metadata. The license below
was read from the package's own license file rather than inferred.

{overrides}

---

## Infrastructure

{manual}

---

## Python dependencies ({py_count})

| Package | Version | License | Copyright | Project |
|---|---|---|---|---|
{py_rows}

---

## Frontend dependencies ({js_count})

Production dependencies only — build-time-only tooling is not distributed.

| Package | Version | License | Copyright | Project |
|---|---|---|---|---|
{js_rows}
"""

PRODUCT = "Open Notebook Commercial (DataFabricX Pvt Ltd)"


class NoticeError(RuntimeError):
    """A generator input could not be produced."""


def normalize_license(name: str, raw: str) -> str:
    """Return a short license identifier for a package.

    Some packages (tiktoken) put their entire license *text* in the metadata
    License field -- over 1000 characters, which destroys the notices table.
    For those, the first non-empty line is the identifier ("MIT License").
    """
    if name in LICENSE_OVERRIDES:
        return LICENSE_OVERRIDES[name][0]

    text = (raw or "").strip()
    if text in UNKNOWN:
        return "UNKNOWN"

    if len(text) > 60 or "\n" in text:
        first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        # Guard against a first line that is itself prose rather than a name.
        return first if 0 < len(first) <= 60 else "See package LICENSE file"

    return text


def _run(cmd: list[str], cwd: Path) -> str:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            cwd=cwd,
            # Package metadata is UTF-8 and routinely contains characters the
            # Windows console codepage cannot decode.
            encoding="utf-8",
            errors="replace",
        ).stdout
    except FileNotFoundError as exc:
        raise NoticeError(f"{cmd[0]} not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise NoticeError(
            f"{' '.join(cmd[:3])} failed: {(exc.stderr or '').strip()[:300]}"
        ) from exc


def collect_python() -> list[Package]:
    raw = _run(
        [
            sys.executable,
            "-m",
            "piplicenses",
            "--format=json",
            "--with-authors",
            "--with-urls",
        ],
        REPO_ROOT,
    )
    packages = []
    for pkg in json.loads(raw):
        name = pkg.get("Name", "")
        # The project itself is not a third-party dependency, and EXCLUDED
        # packages are installed locally but never shipped.
        if name in {"open-notebook", "UNKNOWN"} or name in EXCLUDED:
            continue
        author = pkg.get("Author", "")
        packages.append(
            Package(
                name=name,
                version=pkg.get("Version", ""),
                license=normalize_license(name, pkg.get("License", "")),
                author="" if author in UNKNOWN else author,
                url=pkg.get("URL", ""),
            )
        )
    return sorted(packages, key=lambda p: p.name.lower())


def collect_frontend() -> list[Package]:
    if not (FRONTEND_DIR / "node_modules").is_dir():
        raise NoticeError(
            f"{FRONTEND_DIR / 'node_modules'} is missing. Run `npm ci` in "
            "frontend/ first — notices are generated from installed metadata."
        )
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise NoticeError("npx not found on PATH; cannot enumerate frontend deps.")

    raw = _run(
        [npx, "--yes", "license-checker", "--production", "--json"], FRONTEND_DIR
    )
    own_name = json.loads((FRONTEND_DIR / "package.json").read_text())["name"]

    packages = []
    for key, meta in json.loads(raw).items():
        # Keys are "name@version"; scoped names start with @ and keep it.
        name, _, version = key.rpartition("@")
        if name == own_name:
            continue
        if name in EXCLUDED:
            continue
        licenses = meta.get("licenses", "")
        if isinstance(licenses, list):
            licenses = " AND ".join(licenses)
        packages.append(
            Package(
                name=name,
                version=version,
                license=normalize_license(name, licenses),
                author=meta.get("publisher", ""),
                url=meta.get("repository", ""),
            )
        )
    return sorted(packages, key=lambda p: p.name.lower())


def summarize(*groups: list[Package]) -> str:
    counts: dict[str, int] = {}
    for group in groups:
        for pkg in group:
            counts[pkg.license] = counts.get(pkg.license, 0) + 1
    lines = ["| License | Packages |", "|---|---|"]
    for lic, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {lic.replace('|', '/')} | {count} |")
    return "\n".join(lines)


def render() -> str:
    python_pkgs = collect_python()
    frontend_pkgs = collect_frontend()
    excluded = "\n".join(
        f"- **{name}** — {reason}" for name, reason in sorted(EXCLUDED.items())
    )
    overrides = "\n".join(
        f"- **{name}** — recorded as `{lic}`: {why}"
        for name, (lic, why) in sorted(LICENSE_OVERRIDES.items())
    )
    return HEADER.format(
        product=PRODUCT,
        generated=date.today().isoformat(),
        summary=summarize(python_pkgs, frontend_pkgs),
        manual=MANUAL_ENTRIES,
        excluded=excluded,
        overrides=overrides,
        py_count=len(python_pkgs),
        js_count=len(frontend_pkgs),
        py_rows="\n".join(p.as_row() for p in python_pkgs),
        js_rows="\n".join(p.as_row() for p in frontend_pkgs),
    )


def _strip_generated_date(text: str) -> str:
    """Ignore the timestamp line when comparing, so --check does not fail
    merely because a day passed since the file was generated."""
    return "\n".join(
        line for line in text.splitlines() if not line.startswith("> Last generated:")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed file matches the current tree; do not write.",
    )
    args = parser.parse_args()

    try:
        content = render()
    except NoticeError as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.check:
        if not OUTPUT.exists():
            print(f"ERROR: {OUTPUT.name} is missing. Run this script to create it.")
            return 1
        current = OUTPUT.read_text(encoding="utf-8")
        if _strip_generated_date(current) != _strip_generated_date(content):
            print(
                f"ERROR: {OUTPUT.name} is out of date with the dependency tree.\n"
                "Regenerate it with:  uv run python scripts/generate_notices.py"
            )
            return 1
        print(f"{OUTPUT.name} is up to date.")
        return 0

    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Wrote {OUTPUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
