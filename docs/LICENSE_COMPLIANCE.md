# License compliance

How this fork stays legally shippable as a commercial product, and what you
must not break. Companion to [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md)
(the attribution list) and [LICENSE](../LICENSE) (our terms).

> This is an engineering compliance record, not legal advice. The items marked
> **⚠️ legal review** need counsel sign-off before commercial launch.

---

## 1. Our license position

The upstream project is MIT, which permits selling a closed, commercial
derivative without publishing our source. Two obligations come with that, and
both are met in [LICENSE](../LICENSE):

- **Luis Novo's copyright is retained and must never be removed or replaced.**
  Our copyright line sits above his; his stays.
- **The MIT permission notice travels with the software**, which is why
  `LICENSE` ships in the container image (`COPY . /app`).

## 2. The rule that must not be broken

**Never add a GPL or AGPL dependency.**

- **AGPL is absolutely prohibited.** Its network-use clause reaches hosted
  SaaS — the one licence that would force us to publish our source for running
  the product as a service. `scripts/check_licenses.py` hard-blocks it and it
  can *never* be allowlisted, not even by name.
- **GPL** obligations attach on **distribution**. We do distribute (Docker
  images, and the per-client installer planned in WP7), so GPL is off-limits in
  any shipped artifact.
- **LGPL is acceptable** while the library is used unmodified and dynamically
  linked — which is why `pycountry` and `chardet` are fine and `asciidoc`
  was not.

### The trap to avoid

**Do not adopt PyMuPDF / `fitz`.** It is the most commonly recommended Python
PDF library and it is **AGPL-3.0** (dual-licensed commercially by Artifex).
Adopting it would either force us to open-source the product or buy a
commercial licence. The same caution applies to **poppler-utils** (GPL), often
pulled in indirectly via `pdf2image`.

If better PDF fidelity is needed, the answer is **Docling** (MIT), already
integrated as an opt-in engine — see
[ADR-007](7-DEVELOPMENT/decisions/ADR-007-optin-runtimes.md).

## 3. The drift guard (CI-enforced)

`scripts/check_licenses.py` runs on every pull request as the **License Scan**
job and fails the build on any copyleft dependency not on its reviewed
allowlist. It is a *drift* guard: it baselines what the fork inherited and
catches anything new.

```bash
uv run python scripts/check_licenses.py
```

Current allowlist — every entry is a reviewed decision with a written
justification in the script. **Do not add to it to make CI green.**

| Package | License | Why it is acceptable |
|---|---|---|
| `pycountry` | LGPL-2.1-only | Unmodified, separately installed — see §4 |
| `chardet` | LGPL-2.1+ | Unmodified, used over its public API (via `readability-lxml`) |
| `docutils` | BSD / GPL / Public Domain | Multi-licensed; **we elect the BSD option**, so no copyleft attaches |
| `asciidoc` | GPLv2+ | Present in the dev/CI venv only — **purged from every shipped image**; see §5 |
| `@img/sharp-*` | Apache-2.0 (+ LGPL-3.0 on some platforms) | libvips used as an unmodified shared library |

## 4. `pycountry` must stay unmodified

`pycountry` is LGPL-2.1. Used as an unmodified, separately-installed
dependency, our obligation is **zero**. Modifying or vendoring its source would
trigger LGPL obligations on the modified library.

**Rules:**
- Do not vendor `pycountry` into this repository.
- Do not patch it at runtime or at build time.
- Do not static-link it.

**Enforced by** `tests/test_pycountry_unmodified.py`, which verifies the
installed package is byte-identical to the distribution recorded in its own
`RECORD` manifest. It fails if any file is edited, added, or removed. That test
runs in CI with the rest of the suite.

## 5. `asciidoc` — GPL, purged from shipped artifacts

`content-core` declares `asciidoc` (GPLv2+) as a hard dependency but **never
imports it** — verified against both the installed wheel and the upstream
source. Extraction output is byte-identical without it across every supported
format.

- `uv sync` still installs it into the **development and CI** virtualenv. That
  is not distribution, so no GPL obligation attaches.
- The `Dockerfile` **purges it from every shipped image**, and that step is
  self-verifying: it asserts the package is gone *and* that `content_core`
  still imports, so a future content-core that genuinely needs it fails the
  build rather than shipping broken.
- `tests/test_license_check.py::TestAsciidocStaysUnused` fails if content-core
  ever starts referencing it, which would invalidate the purge.

**Upstream fix in progress:** [lfnovo/content-core#58](https://github.com/lfnovo/content-core/pull/58).
Once merged and `content-core` is bumped, **delete the Dockerfile purge and the
allowlist entry together**, so asciidoc's return becomes a hard CI failure.

## 6. SurrealDB — BSL 1.1

**Decision: KEEP SurrealDB. No licence purchase is required for our model.**

SurrealDB is the one non-permissive component. It is source-available under the
Business Source License 1.1, not OSI open source.

- **Commercial embedding is permitted and free** — we may embed it, ship it to
  customers, and run it hosted at any scale.
- **The single prohibition** is offering SurrealDB *itself* as a managed
  database service. That is not our business.
- Each release **converts to Apache 2.0 four years** after its release date.

### How we distribute it — and the one exception

| Path | Artifact | Redistributes BSL code? | Obligation |
|---|---|---|---|
| **Default (chosen)** | `docker-compose.yml` pulls the official `surrealdb/surrealdb:v2` image as a separate container | **No** — it is a dependency, not redistribution | None |
| **Single-container** | `Dockerfile --target single` copies the SurrealDB binary into our image | **Yes** | BSL licence text must be inside that image — **satisfied**, see below |

**The single-container variant genuinely redistributes BSL-licensed code, and
carries the licence accordingly.** The `single` target copies
`licenses/SURREALDB-BSL-1.1.txt` to `/app/licenses/` in the image, so the
licence travels with the binary as BSL requires. The default multi-container
path carries no such obligation and remains the recommended deployment.

Two things to know if you touch this:

- **The licence text is vendored here, not copied from the official image.** The
  `surrealdb/surrealdb` image ships no licence file of its own — verified by
  exporting its filesystem (1400 files, none a licence) — so there is nothing to
  copy from it.
- **BSL parameters are per-release.** `licenses/SURREALDB-BSL-1.1.txt` is taken
  verbatim from the **`v2.6.5`** tag, matching the exact binary in
  `surrealdb/surrealdb:v2`. The `main` branch currently carries SurrealDB 3.0
  terms with a different Change Date (2030-01-01) that do **not** apply to our
  binary. **If the pinned SurrealDB version changes, re-fetch the licence from
  the matching tag:**

  ```bash
  curl -sSL -o licenses/SURREALDB-BSL-1.1.txt \
    https://raw.githubusercontent.com/surrealdb/surrealdb/<TAG>/LICENSE
  ```

Our version converts to **Apache 2.0 on 2029-09-17** (the Change Date stated in
the v2.6.5 licence).

The BSL position is recorded as an accepted business decision in
[LEGAL_DECISIONS.md](LEGAL_DECISIONS.md) §1.

## 7. Encryption key management

`OPEN_NOTEBOOK_ENCRYPTION_KEY` encrypts stored provider credentials at rest. It
has **no default** and is required for credential storage.

- **Generate one per deployment.** Never reuse a key across clients, and never
  reuse the development value.
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
- **Never commit it.** `.env` is gitignored. In production, supply it via the
  orchestrator's secret store, or via `OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE`
  pointing at a mounted secret file.
- The value in [DEV_SETUP.md](DEV_SETUP.md) is explicitly labelled
  development-only.

### Rotation

Rotating the key **invalidates every stored credential**, because existing
values cannot be decrypted with a new key. There is no automatic re-encryption.
To rotate:

1. Record which providers are configured (the UI never returns key *values*).
2. Set the new key and restart the API and worker.
3. Re-enter each provider credential through the Settings UI.

Rotate on suspected compromise, on operator offboarding, and when a deployment
is handed to a different client.

## 8. Brand assets — WP3, not here

The MIT licence gives us the code, **not** the name "Open Notebook", its logo,
or the open-notebook.ai brand. Those must be replaced before commercial launch.

**Rebranding is WP3 and is deliberately not done in WP1.** This is only the
inventory of where brand identity currently lives, so WP3 can act on it:

| What | Where |
|---|---|
| App title | `frontend/src/app/layout.tsx` (hardcoded) |
| Logo | `/logo.svg`, referenced in `frontend/src/components/layout/AppSidebar.tsx` |
| Root logo asset | `logo.png` |
| Product name in UI copy | `frontend/src/lib/locales/` (all locales) |
| Package name / description | `pyproject.toml`, `frontend/package.json` |
| Docs and README branding | `README.md`, `docs/` |

⚠️ Upstream brand assets must be removed from shipped artifacts at that point.

## 9. AI provider terms

Each provider's commercial terms govern our use of its API. See
[PROVIDER_TERMS.md](PROVIDER_TERMS.md) for the per-provider list and the ones
flagged for review.

## 10. Regenerating the notices

[THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md) is generated, never
hand-edited:

```bash
uv run python scripts/generate_notices.py          # regenerate
uv run python scripts/generate_notices.py --check  # CI: fail if stale
```

**It must be generated on Linux**, because dependency resolution is
platform-specific and the Linux container is what we distribute. A Windows host
resolves `pywin32`, `win32_setctime`, `@img/sharp-win32-x64` and
`@next/swc-win32-x64-msvc` — none of which we ship — while omitting the Linux
binaries we do. From a Windows machine, regenerate inside a container:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W):/src" node:22-slim bash -c '
  apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq curl ca-certificates >/dev/null 2>&1
  curl -LsSf https://astral.sh/uv/install.sh 2>/dev/null | sh >/dev/null 2>&1
  export PATH=/root/.local/bin:$PATH
  mkdir -p /build/open_notebook /build/scripts /build/frontend
  cp /src/pyproject.toml /src/uv.lock /build/
  cp /src/open_notebook/__init__.py /build/open_notebook/
  cp /src/scripts/generate_notices.py /build/scripts/
  cp /src/frontend/package.json /src/frontend/package-lock.json /build/frontend/
  cd /build/frontend && npm ci --silent >/dev/null 2>&1
  cd /build && uv sync --quiet >/dev/null 2>&1
  uv run python scripts/generate_notices.py
  cp /build/THIRD-PARTY-NOTICES.md /src/THIRD-PARTY-NOTICES.md'
```

## 11. Status of the licensing items

Decisions and their reasoning are recorded in
[LEGAL_DECISIONS.md](LEGAL_DECISIONS.md).

| # | Item | Status |
|---|---|---|
| 1 | SurrealDB BSL 1.1 position | ✅ Accepted — keep SurrealDB |
| 2 | BSL text in the single-container image | ✅ **Fixed in code** — ships at `/app/licenses/` |
| 3 | PRC-jurisdiction providers (DeepSeek, DashScope, MiniMax) | ✅ Assigned to client — ⚠️ product action: make opt-in |
| 4 | ElevenLabs commercial audio rights | ✅ Accepted — conditional on clients using own keys |
| 5 | Local model weight licences (Ollama, oMLX) | ✅ Assigned to client — ToS wording needed |
| 6 | Customer-configured "compatible" endpoints | ✅ Assigned to client — ToS wording needed |
| 7 | Rebranding before launch (WP3) | Inventoried, not yet done |

**These are business decisions by DataFabricX, not a legal opinion.** The
engineering diligence behind each is documented and verifiable; the conclusions
drawn from it are the company's own.

> **The condition everything in rows 3–6 rests on:** clients operate their own
> instances and supply their own AI provider credentials (see
> [TENANCY.md](TENANCY.md) — Model A). **If DataFabricX ever hosts instances or
> supplies its own provider keys, those four items revert to DataFabricX and
> must be re-decided.**
