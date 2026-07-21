# Third-Party Notices

This product, **Open Notebook Commercial (DataFabricX Pvt Ltd)**, is a commercial derivative of
[Open Notebook](https://github.com/lfnovo/open-notebook) by Luis Novo, used
under the MIT License. See [LICENSE](LICENSE) — the upstream copyright is
retained there, as the MIT License requires.

This file enumerates every third-party dependency, its version, license,
and copyright holder, satisfying the attribution requirements of the
permissive licenses across the stack in one place.

> **Generated file — do not edit by hand.**
> Regenerate with `uv run python scripts/generate_notices.py`.
> Last generated: 2026-07-21 against the locked dependency tree.
> Entries that have no package metadata (SurrealDB) are maintained in
> `MANUAL_ENTRIES` in that script.

The "Copyright" column reports each package's declared author or maintainer,
which is the copyright holder that package metadata exposes. Where a project
declares no author, it shows `-`; the authoritative notice is then the
LICENSE file in the package itself.

---

## Licenses in use

| License | Packages |
|---|---|
| MIT | 349 |
| MIT License | 48 |
| Apache-2.0 | 21 |
| Apache Software License | 18 |
| BSD License | 18 |
| BSD-3-Clause | 16 |
| ISC | 8 |
| BSD-2-Clause | 5 |
| Python Software Foundation License | 3 |
| Apache License 2.0 | 2 |
| Apache Software License; BSD License | 2 |
| ISC License (ISCL) | 2 |
| LGPL-3.0-or-later | 2 |
| Mozilla Public License 2.0 (MPL 2.0) | 2 |
| 0BSD | 1 |
| Apache Software License; MIT License | 1 |
| Apache-2.0 AND CNRI-Python | 1 |
| Apache-2.0 AND MIT | 1 |
| Apache-2.0 OR BSD-3-Clause | 1 |
| Apache-2.0 OR MIT | 1 |
| BSD License; GNU General Public License (GPL); Public Domain | 1 |
| BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 1 |
| BSD-3-Clause, Apache-2.0, dependency licenses | 1 |
| CC-BY-4.0 | 1 |
| CC0-1.0 | 1 |
| GNU Lesser General Public License v2 or later (LGPLv2+) | 1 |
| LGPL-2.1-only | 1 |
| MIT License, Apache License, Version 2.0 | 1 |
| MIT License; Mozilla Public License 2.0 (MPL 2.0) | 1 |
| MIT-CMU | 1 |
| MPL-2.0 AND (Apache-2.0 OR MIT) | 1 |
| PSF-2.0 | 1 |
| The Unlicense (Unlicense) | 1 |
| Unlicense | 1 |

No GPL or AGPL-licensed code is distributed in this product. That is enforced
on every pull request by `scripts/check_licenses.py`, which fails the build on
any copyleft dependency not on its reviewed allowlist; AGPL can never be
allowlisted. See [docs/LICENSE_COMPLIANCE.md](docs/LICENSE_COMPLIANCE.md).

### Installed for development but not distributed

These are present in the development and CI virtualenv but are removed from
every shipped artifact, so they are not listed as dependencies above.

- **asciidoc** — GPLv2+. Declared as a hard dependency by content-core but never imported by it, and purged from every shipped artifact by the Dockerfile. `uv sync` still installs it into the development and CI virtualenv, but no GPL code is distributed. Removal proposed upstream in lfnovo/content-core#58.

### Licenses corrected from package metadata

These packages declare no usable license in their metadata. The license below
was read from the package's own license file rather than inferred.

- **caio** — recorded as `Apache-2.0`: no license in package metadata; Apache 2.0 per its own COPYING file
- **content-core** — recorded as `MIT`: no license classifier in package metadata; MIT per its own LICENSE file (Copyright (c) 2025 Luis Novo)

---

## Infrastructure

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


---

## Python dependencies (200)

| Package | Version | License | Copyright | Project |
|---|---|---|---|---|
| ai-prompter | 0.4.0 | MIT | LUIS NOVO <lfnovo@gmail.com> | - |
| aiofile | 3.9.0 | Apache Software License | Dmitry Orlov | [link](http://github.com/mosquito/aiofile) |
| aiohappyeyeballs | 2.6.1 | Python Software Foundation License | J. Nick Koston | [link](https://github.com/aio-libs/aiohappyeyeballs) |
| aiohttp | 3.14.1 | Apache-2.0 AND MIT | - | [link](https://github.com/aio-libs/aiohttp) |
| aiosignal | 1.4.0 | Apache Software License | - | [link](https://github.com/aio-libs/aiosignal) |
| aiosqlite | 0.22.1 | MIT License | Amethyst Reese <amethyst@n7.gg> | [link](https://aiosqlite.omnilib.dev) |
| annotated-doc | 0.0.4 | MIT | =?utf-8?q?Sebasti=C3=A1n_Ram=C3=ADrez?= <tiangolo@gmail.com> | [link](https://github.com/fastapi/annotated-doc) |
| annotated-types | 0.7.0 | MIT License | Adrian Garcia Badaracco <1755071+adriangb@users.noreply.github.com>, Samuel Colvin <s@muelcolvin.com>, Zac Hatfield-Dodds <zac@zhd.dev> | [link](https://github.com/annotated-types/annotated-types) |
| anthropic | 0.109.2 | MIT License | Anthropic <support@anthropic.com> | [link](https://github.com/anthropics/anthropic-sdk-python) |
| anyio | 4.12.1 | MIT | Alex Grönholm <alex.gronholm@nextday.fi> | [link](https://anyio.readthedocs.io/en/stable/versionhistory.html) |
| attrs | 25.4.0 | MIT | Hynek Schlawack <hs@ox.cx> | [link](https://www.attrs.org/en/stable/changelog.html) |
| Authlib | 1.6.12 | BSD License | Hsiaoming Yang <me@lepture.com> | [link](https://github.com/authlib/authlib) |
| babel | 2.18.0 | BSD License | Armin Ronacher | [link](https://babel.pocoo.org/) |
| beartype | 0.22.9 | MIT License | Cecil Curry <leycec@gmail.com> | - |
| beautifulsoup4 | 4.14.3 | MIT License | Leonard Richardson <leonardr@segfault.org> | [link](https://www.crummy.com/software/BeautifulSoup/bs4/) |
| bs4 | 0.0.2 | MIT License | Leonard Richardson <leonardr@segfault.org> | - |
| cachetools | 6.2.4 | MIT | Thomas Kemmer <tkemmer@computer.org> | [link](https://github.com/tkem/cachetools/) |
| caio | 0.9.25 | Apache-2.0 | Dmitry Orlov <me@mosquito.su> | - |
| certifi | 2026.1.4 | Mozilla Public License 2.0 (MPL 2.0) | Kenneth Reitz | [link](https://github.com/certifi/python-certifi) |
| cffi | 2.0.0 | MIT | Armin Rigo, Maciej Fijalkowski | [link](https://cffi.readthedocs.io/en/latest/whatsnew.html) |
| cfgv | 3.5.0 | MIT | Anthony Sottile | [link](https://github.com/asottile/cfgv) |
| chardet | 5.2.0 | GNU Lesser General Public License v2 or later (LGPLv2+) | Mark Pilgrim | [link](https://github.com/chardet/chardet) |
| charset-normalizer | 3.4.4 | MIT | "Ahmed R. TAHRI" <tahri.ahmed@proton.me> | [link](https://github.com/jawah/charset_normalizer/blob/master/CHANGELOG.md) |
| click | 8.3.1 | BSD-3-Clause | - | [link](https://github.com/pallets/click/) |
| content-core | 2.0.4 | MIT | LUIS NOVO <lfnovo@gmail.com> | - |
| coverage | 7.14.3 | Apache-2.0 | Ned Batchelder and 257 others | [link](https://github.com/coveragepy/coveragepy) |
| cryptography | 48.0.1 | Apache-2.0 OR BSD-3-Clause | The Python Cryptographic Authority and individual contributors <cryptography-dev@python.org> | [link](https://github.com/pyca/cryptography) |
| cssselect | 1.3.0 | BSD License | Ian Bicking | [link](https://github.com/scrapy/cssselect) |
| cyclopts | 4.5.0 | Apache-2.0 | Brian Pugh | [link](https://github.com/BrianPugh/cyclopts) |
| decorator | 5.2.1 | BSD License | Michele Simionato <michele.simionato@gmail.com> | - |
| defusedxml | 0.7.1 | Python Software Foundation License | Christian Heimes | [link](https://github.com/tiran/defusedxml) |
| distlib | 0.4.0 | Python Software Foundation License | Vinay Sajip | [link](https://github.com/pypa/distlib) |
| distro | 1.9.0 | Apache Software License | Nir Cohen | [link](https://github.com/python-distro/distro) |
| dnspython | 2.8.0 | ISC License (ISCL) | Bob Halley <halley@dnspython.org> | [link](https://www.dnspython.org) |
| docstring_parser | 0.17.0 | MIT License | Marcin Kurczewski <dash@wind.garden> | [link](https://github.com/rr-/docstring_parser) |
| docutils | 0.22.4 | BSD License; GNU General Public License (GPL); Public Domain | David Goodger <goodger@python.org> | [link](https://docutils.sourceforge.io) |
| email-validator | 2.3.0 | The Unlicense (Unlicense) | Joshua Tauberer | [link](https://github.com/JoshData/python-email-validator) |
| esperanto | 2.25.1 | MIT | LUIS NOVO <lfnovo@gmail.com> | [link](https://github.com/lfnovo/esperanto) |
| et_xmlfile | 2.0.0 | MIT License | See AUTHORS.txt | [link](https://foss.heptapod.net/openpyxl/et_xmlfile) |
| exceptiongroup | 1.3.1 | MIT License | Alex Grönholm <alex.gronholm@nextday.fi> | [link](https://github.com/agronholm/exceptiongroup/blob/main/CHANGES.rst) |
| fast-ebook | 0.2.0 | MIT | - | [link](https://github.com/arc53/fast-ebook) |
| fastapi | 0.136.3 | MIT | =?utf-8?q?Sebasti=C3=A1n_Ram=C3=ADrez?= <tiangolo@gmail.com> | [link](https://github.com/fastapi/fastapi) |
| fastmcp | 3.2.0 | Apache-2.0 | Jeremiah Lowin | [link](https://gofastmcp.com) |
| filelock | 3.20.3 | Unlicense | - | [link](https://github.com/tox-dev/py-filelock) |
| filetype | 1.2.0 | MIT License | Tomas Aparicio | [link](https://github.com/h2non/filetype.py) |
| firecrawl-py | 4.13.1 | MIT License | Mendable.ai | [link](https://github.com/firecrawl/firecrawl) |
| frozenlist | 1.8.0 | Apache-2.0 | - | [link](https://github.com/aio-libs/frozenlist) |
| fsspec | 2026.1.0 | BSD-3-Clause | - | [link](https://github.com/fsspec/filesystem_spec) |
| google-auth | 2.47.0 | Apache Software License | Google Cloud Platform | [link](https://github.com/googleapis/google-auth-library-python) |
| google-genai | 1.60.0 | Apache-2.0 | Google LLC <googleapis-packages@google.com> | [link](https://github.com/googleapis/python-genai) |
| groq | 0.37.1 | Apache Software License | Groq <support@groq.com> | [link](https://github.com/groq/groq-python) |
| h11 | 0.16.0 | MIT License | Nathaniel J. Smith | [link](https://github.com/python-hyper/h11) |
| hf-xet | 1.2.0 | Apache-2.0 | - | [link](https://github.com/huggingface/xet-core) |
| httpcore | 1.0.9 | BSD-3-Clause | Tom Christie <tom@tomchristie.com> | [link](https://www.encode.io/httpcore/) |
| httpx | 0.28.1 | BSD License | Tom Christie <tom@tomchristie.com> | [link](https://github.com/encode/httpx) |
| httpx-sse | 0.4.3 | MIT | Florimond Manca <florimond.manca@protonmail.com> | [link](https://github.com/florimondmanca/httpx-sse) |
| huggingface_hub | 1.3.2 | Apache Software License | Hugging Face, Inc. | [link](https://github.com/huggingface/huggingface_hub) |
| humanize | 4.15.0 | MIT | Jason Moiron <jmoiron@jmoiron.net> | [link](https://github.com/python-humanize/humanize) |
| identify | 2.6.16 | MIT | Chris Kuehl | [link](https://github.com/pre-commit/identify) |
| idna | 3.15 | BSD-3-Clause | Kim Davies <kim+pypi@gumleaf.org> | [link](https://github.com/kjd/idna) |
| ImageIO | 2.37.2 | BSD-2-Clause | ImageIO contributors | [link](https://github.com/imageio/imageio) |
| imageio-ffmpeg | 0.6.0 | BSD License | imageio contributors | [link](https://github.com/imageio/imageio-ffmpeg) |
| importlib_metadata | 8.7.1 | Apache-2.0 | "Jason R. Coombs" <jaraco@jaraco.com> | [link](https://github.com/python/importlib_metadata) |
| iniconfig | 2.3.0 | MIT | Ronny Pfannschmidt <opensource@ronnypfannschmidt.de>, Holger Krekel <holger.krekel@gmail.com> | [link](https://github.com/pytest-dev/iniconfig) |
| jaraco.classes | 3.4.0 | MIT License | Jason R. Coombs | [link](https://github.com/jaraco/jaraco.classes) |
| jaraco.context | 6.1.0 | MIT | "Jason R. Coombs" <jaraco@jaraco.com> | [link](https://github.com/jaraco/jaraco.context) |
| jaraco.functools | 4.4.0 | MIT | "Jason R. Coombs" <jaraco@jaraco.com> | [link](https://github.com/jaraco/jaraco.functools) |
| jeepney | 0.9.0 | MIT | Thomas Kluyver <thomas@kluyver.me.uk> | [link](https://gitlab.com/takluyver/jeepney) |
| Jinja2 | 3.1.6 | BSD License | - | [link](https://github.com/pallets/jinja/) |
| jiter | 0.12.0 | MIT License | Samuel Colvin <s@muelcolvin.com> | [link](https://github.com/pydantic/jiter/) |
| jsonpatch | 1.33 | BSD License | Stefan Kögl | [link](https://github.com/stefankoegl/python-json-patch) |
| jsonpointer | 3.0.0 | BSD License | Stefan Kögl | [link](https://github.com/stefankoegl/python-json-pointer) |
| jsonref | 1.1.0 | MIT | Chase Sterling <chase.sterling@gmail.com> | [link](https://github.com/gazpachoking/jsonref) |
| jsonschema | 4.26.0 | MIT | Julian Berman <Julian+jsonschema@GrayVines.com> | [link](https://github.com/python-jsonschema/jsonschema) |
| jsonschema-path | 0.3.4 | Apache Software License | Artur Maciag | [link](https://github.com/p1c2u/jsonschema-path) |
| jsonschema-specifications | 2025.9.1 | MIT | Julian Berman <Julian+jsonschema-specifications@GrayVines.com> | [link](https://github.com/python-jsonschema/jsonschema-specifications) |
| keyring | 25.7.0 | MIT | Kang Zhang <jobo.zh@gmail.com> | [link](https://github.com/jaraco/keyring) |
| langchain | 1.3.9 | MIT License | - | [link](https://docs.langchain.com/) |
| langchain-anthropic | 1.4.6 | MIT License | - | [link](https://docs.langchain.com/oss/python/integrations/providers/anthropic) |
| langchain-core | 1.4.7 | MIT License | - | [link](https://docs.langchain.com/) |
| langchain-google-genai | 4.2.0 | MIT | - | [link](https://docs.langchain.com/oss/python/integrations/providers/google) |
| langchain-groq | 1.1.1 | MIT | - | [link](https://docs.langchain.com/oss/python/integrations/providers/groq) |
| langchain-mistralai | 1.1.1 | MIT | - | [link](https://docs.langchain.com/oss/python/integrations/providers/mistralai) |
| langchain-ollama | 1.0.1 | MIT | - | [link](https://docs.langchain.com/oss/python/integrations/providers/ollama) |
| langchain-openai | 1.1.14 | MIT License | - | [link](https://docs.langchain.com/oss/python/integrations/providers/openai) |
| langchain-protocol | 0.0.15 | MIT License | - | [link](https://github.com/langchain-ai/agent-protocol/tree/main/streaming) |
| langchain-text-splitters | 1.1.2 | MIT License | - | [link](https://docs.langchain.com/) |
| langdetect | 1.0.9 | Apache Software License | Michal Mimino Danilak | [link](https://github.com/Mimino666/langdetect) |
| langgraph | 1.2.5 | MIT | - | [link](https://docs.langchain.com/oss/python/langgraph/overview) |
| langgraph-checkpoint | 4.1.1 | MIT | - | [link](https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint) |
| langgraph-checkpoint-sqlite | 3.0.3 | MIT | - | [link](https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint-sqlite) |
| langgraph-prebuilt | 1.1.0 | MIT | - | [link](https://github.com/langchain-ai/langgraph/tree/main/libs/prebuilt) |
| langgraph-sdk | 0.4.2 | MIT | - | [link](https://github.com/langchain-ai/langgraph/tree/main/libs/sdk-py) |
| langsmith | 0.9.0 | MIT | LangChain <support@langchain.dev> | [link](https://smith.langchain.com/) |
| librt | 0.7.8 | MIT License | Jukka Lehtosalo <jukka.lehtosalo@iki.fi>, Ivan Levkivskyi <levkivskyi@gmail.com> | [link](https://github.com/mypyc/librt) |
| loguru | 0.7.3 | MIT License | Delgan <delgan.py@gmail.com> | [link](https://github.com/Delgan/loguru) |
| lxml | 6.1.0 | BSD-3-Clause | lxml dev team | [link](https://lxml.de/) |
| lxml_html_clean | 0.4.4 | BSD-3-Clause | Lumír Balhar | [link](https://github.com/fedora-python/lxml_html_clean/) |
| markdown-it-py | 4.0.0 | MIT License | Chris Sewell <chrisj_sewell@hotmail.com> | [link](https://github.com/executablebooks/markdown-it-py) |
| markdownify | 1.2.2 | MIT License | Matthew Tretter <m@tthewwithanm.com> | [link](http://github.com/matthewwithanm/python-markdownify) |
| MarkupSafe | 3.0.3 | BSD-3-Clause | - | [link](https://github.com/pallets/markupsafe/) |
| mcp | 1.28.1 | MIT License | Anthropic, PBC. | [link](https://modelcontextprotocol.io) |
| mdurl | 0.1.2 | MIT License | Taneli Hukkinen <hukkin@users.noreply.github.com> | [link](https://github.com/executablebooks/mdurl) |
| more-itertools | 10.8.0 | MIT | Erik Rose <erikrose@grinchcentral.com> | [link](https://github.com/more-itertools/more-itertools) |
| moviepy | 2.2.1 | MIT License | Zulko 2024 | - |
| multidict | 6.7.0 | Apache License 2.0 | Andrew Svetlov | [link](https://github.com/aio-libs/multidict) |
| mypy | 1.19.1 | MIT License | Jukka Lehtosalo <jukka.lehtosalo@iki.fi> | [link](https://www.mypy-lang.org/) |
| mypy_extensions | 1.1.0 | MIT | The mypy developers <jukka.lehtosalo@iki.fi> | [link](https://github.com/python/mypy_extensions) |
| nest-asyncio | 1.6.0 | BSD License | Ewald R. de Wit | [link](https://github.com/erdewit/nest_asyncio) |
| nodeenv | 1.10.0 | BSD License | Eugene Kalinin | [link](https://github.com/ekalinin/nodeenv) |
| nodejs-wheel-binaries | 24.13.0 | MIT License | Jinzhe Zeng <jinzhe.zeng@ustc.edu.cn> | [link](https://github.com/njzjz/nodejs-wheel) |
| numpy | 2.4.1 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Travis E. Oliphant et al. | [link](https://numpy.org) |
| ollama | 0.6.1 | MIT | hello@ollama.com | [link](https://ollama.com) |
| openai | 2.32.0 | Apache Software License | OpenAI <support@openai.com> | [link](https://github.com/openai/openai-python) |
| openapi-pydantic | 0.5.1 | MIT License | Mike Oakley | [link](https://github.com/mike-oakley/openapi-pydantic) |
| openpyxl | 3.1.5 | MIT License | See AUTHORS | [link](https://openpyxl.readthedocs.io) |
| opentelemetry-api | 1.39.1 | Apache-2.0 | OpenTelemetry Authors <cncf-opentelemetry-contributors@lists.cncf.io> | [link](https://github.com/open-telemetry/opentelemetry-python/tree/main/opentelemetry-api) |
| orjson | 3.11.6 | MPL-2.0 AND (Apache-2.0 OR MIT) | - | [link](https://github.com/ijl/orjson) |
| ormsgpack | 1.12.2 | Apache-2.0 OR MIT | Aviram Hassan <aviramyhassan@gmail.com>, Emanuele Giaquinta <emanuele.giaquinta@gmail.com> | [link](https://github.com/ormsgpack/ormsgpack) |
| packaging | 25.0 | Apache Software License; BSD License | Donald Stufft <donald@stufft.io> | [link](https://github.com/pypa/packaging) |
| pandas | 3.0.0 | BSD License | The Pandas Development Team <pandas-dev@python.org> | [link](https://pandas.pydata.org) |
| pathable | 0.4.4 | Apache Software License | Artur Maciag | [link](https://github.com/p1c2u/pathable) |
| pathspec | 1.0.3 | Mozilla Public License 2.0 (MPL 2.0) | "Caleb P. Burns" <cpburnz@gmail.com> | [link](https://python-path-specification.readthedocs.io/en/latest/index.html) |
| pdfminer.six | 20260107 | MIT | Yusuke Shinyama, Pieter Marsman | [link](https://github.com/pdfminer/pdfminer.six) |
| pdfplumber | 0.11.10 | MIT License | Jeremy Singer-Vine | [link](https://github.com/jsvine/pdfplumber) |
| pillow | 12.3.0 | MIT-CMU | Jeffrey 'Alex' Clark <aclark@aclark.net> | [link](https://python-pillow.github.io) |
| platformdirs | 4.5.1 | MIT | - | [link](https://github.com/tox-dev/platformdirs) |
| pluggy | 1.6.0 | MIT License | Holger Krekel <holger@merlinux.eu> | - |
| podcast-creator | 0.12.0 | MIT | - | - |
| pre_commit | 4.5.1 | MIT | Anthony Sottile | [link](https://github.com/pre-commit/pre-commit) |
| proglog | 0.1.12 | MIT | Zulko | [link](https://github.com/Edinburgh-Genome-Foundry/proglog) |
| propcache | 0.4.1 | Apache Software License | Andrew Svetlov | [link](https://github.com/aio-libs/propcache) |
| py-key-value-aio | 0.4.4 | Apache Software License | - | - |
| pyasn1 | 0.6.3 | BSD-2-Clause | Ilya Etingof <etingof@gmail.com> | [link](https://github.com/pyasn1/pyasn1) |
| pyasn1_modules | 0.4.2 | BSD License | Ilya Etingof | [link](https://github.com/pyasn1/pyasn1-modules) |
| pycountry | 26.2.16 | LGPL-2.1-only | Christian Theune | [link](https://github.com/pycountry/pycountry) |
| pycparser | 3.0 | BSD-3-Clause | Eli Bendersky <eliben@gmail.com> | [link](https://github.com/eliben/pycparser) |
| pydantic | 2.12.5 | MIT | Samuel Colvin <s@muelcolvin.com>, Eric Jolibois <em.jolibois@gmail.com>, Hasan Ramezani <hasan.r67@gmail.com>, Adrian Garcia Badaracco <1755071+adriangb@users.noreply.github.com>, Terrence Dorsey <terry@pydantic.dev>, David Montague <david@pydantic.dev>, Serge Matveenko <lig@countzero.co>, Marcelo Trylesinski <marcelotryle@gmail.com>, Sydney Runkle <sydneymarierunkle@gmail.com>, David Hewitt <mail@davidhewitt.io>, Alex Hall <alex.mojaki@gmail.com>, Victorien Plot <contact@vctrn.dev>, Douwe Maan <hi@douwe.me> | [link](https://github.com/pydantic/pydantic) |
| pydantic-settings | 2.14.2 | MIT | Samuel Colvin <s@muelcolvin.com>, Eric Jolibois <em.jolibois@gmail.com>, Hasan Ramezani <hasan.r67@gmail.com> | [link](https://github.com/pydantic/pydantic-settings) |
| pydantic_core | 2.41.5 | MIT | Samuel Colvin <s@muelcolvin.com>, Adrian Garcia Badaracco <1755071+adriangb@users.noreply.github.com>, David Montague <david@pydantic.dev>, David Hewitt <mail@davidhewitt.dev>, Sydney Runkle <sydneymarierunkle@gmail.com>, Victorien Plot <contact@vctrn.dev> | [link](https://github.com/pydantic/pydantic-core) |
| pydub | 0.25.1 | MIT License | James Robert | [link](http://pydub.com) |
| Pygments | 2.20.0 | BSD-2-Clause | Georg Brandl <georg@python.org> | [link](https://pygments.org) |
| PyJWT | 2.13.0 | MIT | Jose Padilla <hello@jpadilla.com> | [link](https://github.com/jpadilla/pyjwt) |
| pypdfium2 | 5.11.0 | BSD-3-Clause, Apache-2.0, dependency licenses | pypdfium2-team | [link](https://github.com/pypdfium2-team/pypdfium2) |
| pyperclip | 1.11.0 | BSD License | Al Sweigart <al@inventwithpython.com> | [link](https://github.com/asweigart/pyperclip) |
| pytest | 9.0.3 | MIT | Holger Krekel, Bruno Oliveira, Ronny Pfannschmidt, Floris Bruynooghe, Brianna Laugher, Freya Bruhin, Others (See AUTHORS) | [link](https://docs.pytest.org/en/latest/) |
| pytest-asyncio | 1.3.0 | Apache-2.0 | Tin Tvrtković <tinchester@gmail.com> | [link](https://github.com/pytest-dev/pytest-asyncio) |
| pytest-cov | 7.1.0 | MIT | Marc Schlaich <marc.schlaich@gmail.com> | [link](https://pytest-cov.readthedocs.io/en/latest/changelog.html) |
| python-dateutil | 2.9.0.post0 | Apache Software License; BSD License | Gustavo Niemeyer | [link](https://github.com/dateutil/dateutil) |
| python-docx | 1.2.0 | MIT License | Steve Canny <stcanny@gmail.com> | [link](https://github.com/python-openxml/python-docx) |
| python-dotenv | 1.2.2 | BSD-3-Clause | Saurabh Kumar <me+github@saurabh-kumar.com> | [link](https://github.com/theskumar/python-dotenv) |
| python-multipart | 0.0.31 | Apache-2.0 | Andrew Dunham <andrew@du.nham.ca> | [link](https://github.com/Kludex/python-multipart) |
| python-pptx | 1.0.2 | MIT License | Steve Canny <stcanny@gmail.com> | [link](https://github.com/scanny/python-pptx) |
| pytubefix | 10.3.6 | MIT License | Juan Bindez <juanbindez780@gmail.com> | [link](https://github.com/juanbindez/pytubefix) |
| PyYAML | 6.0.3 | MIT License | Kirill Simonov | [link](https://pyyaml.org/) |
| readability-lxml | 0.8.4.1 | Apache License 2.0 | Yuri Baburov | [link](http://github.com/buriy/python-readability) |
| referencing | 0.36.2 | MIT | Julian Berman <Julian+referencing@GrayVines.com> | [link](https://github.com/python-jsonschema/referencing) |
| regex | 2026.1.15 | Apache-2.0 AND CNRI-Python | Matthew Barnett <regex@mrabarnett.plus.com> | [link](https://github.com/mrabarnett/mrab-regex) |
| requests | 2.33.0 | Apache Software License | Kenneth Reitz <me@kennethreitz.org> | [link](https://github.com/psf/requests) |
| requests-toolbelt | 1.0.0 | Apache Software License | Ian Cordasco, Cory Benfield | [link](https://toolbelt.readthedocs.io/) |
| rich | 14.2.0 | MIT License | Will McGugan | [link](https://github.com/Textualize/rich) |
| rich-rst | 1.3.2 | MIT | Wasi Master <arianmollik323@gmail.com> | [link](https://wasi-master.github.io/rich-rst) |
| rpds-py | 0.30.0 | MIT | Julian Berman <Julian+rpds@GrayVines.com> | [link](https://github.com/crate-py/rpds) |
| rsa | 4.9.1 | Apache Software License | Sybren A. Stüvel | [link](https://stuvel.eu/rsa) |
| ruff | 0.14.13 | MIT License | "Astral Software Inc." <hey@astral.sh> | [link](https://docs.astral.sh/ruff) |
| SecretStorage | 3.5.0 | BSD-3-Clause | Dmitry Shachnev <mitya57@gmail.com> | [link](https://github.com/mitya57/secretstorage) |
| shellingham | 1.5.4 | ISC License (ISCL) | Tzu-ping Chung | [link](https://github.com/sarugaku/shellingham) |
| six | 1.17.0 | MIT License | Benjamin Peterson | [link](https://github.com/benjaminp/six) |
| sniffio | 1.3.1 | Apache Software License; MIT License | "Nathaniel J. Smith" <njs@pobox.com> | [link](https://github.com/python-trio/sniffio) |
| socksio | 1.0.0 | MIT License | Seth Michael Larson | [link](https://github.com/sethmlarson/socksio) |
| soupsieve | 2.8.4 | MIT | Isaac Muse <Isaac.Muse@gmail.com> | [link](https://github.com/facelessuser/soupsieve) |
| sqlite-vec | 0.1.6 | MIT License, Apache License, Version 2.0 | TODO | [link](https://TODO.com) |
| sse-starlette | 3.2.0 | BSD-3-Clause | sysid <sysid@gmx.de> | [link](https://github.com/sysid/sse-starlette) |
| starlette | 1.3.1 | BSD-3-Clause | Tom Christie <tom@tomchristie.com> | [link](https://github.com/Kludex/starlette) |
| surreal-commands | 1.3.1 | MIT License | Surreal Commands Contributors | [link](https://github.com/lfnovo/surreal-commands) |
| surrealdb | 1.0.8 | Apache-2.0 | SurrealDB | [link](https://github.com/surrealdb/surrealdb.py) |
| tenacity | 9.1.2 | Apache Software License | Julien Danjou | [link](https://github.com/jd/tenacity) |
| tiktoken | 0.12.0 | MIT License | Shantanu Jain | [link](https://github.com/openai/tiktoken) |
| tokenizers | 0.22.2 | Apache Software License | Nicolas Patry <patry.nicolas@protonmail.com>, Anthony Moi <anthony@huggingface.co> | [link](https://github.com/huggingface/tokenizers) |
| tomli | 2.4.0 | MIT | Taneli Hukkinen <hukkin@users.noreply.github.com> | [link](https://github.com/hukkin/tomli) |
| tqdm | 4.67.1 | MIT License; Mozilla Public License 2.0 (MPL 2.0) | - | [link](https://tqdm.github.io) |
| typer | 0.21.1 | MIT | =?utf-8?q?Sebasti=C3=A1n_Ram=C3=ADrez?= <tiangolo@gmail.com> | [link](https://github.com/fastapi/typer) |
| typer-slim | 0.21.1 | MIT | =?utf-8?q?Sebasti=C3=A1n_Ram=C3=ADrez?= <tiangolo@gmail.com> | [link](https://github.com/fastapi/typer) |
| types-requests | 2.32.4.20260107 | Apache-2.0 | - | [link](https://github.com/python/typeshed) |
| typing-inspection | 0.4.2 | MIT | Victorien Plot <contact@vctrn.dev> | [link](https://github.com/pydantic/typing-inspection) |
| typing_extensions | 4.15.0 | PSF-2.0 | "Guido van Rossum, Jukka Lehtosalo, Łukasz Langa, Michael Lee" <levkivskyi@gmail.com> | [link](https://github.com/python/typing_extensions) |
| uncalled-for | 0.2.0 | MIT License | Chris Guidry <guid@omg.lol> | [link](https://github.com/chrisguidry/uncalled-for) |
| urllib3 | 2.7.0 | MIT | Andrey Petrov <andrey.petrov@shazow.net> | [link](https://github.com/urllib3/urllib3/blob/main/CHANGES.rst) |
| uuid_utils | 0.14.0 | BSD License | Amin Alaee <mohammadamin.alaee@gmail.com> | [link](https://github.com/aminalaee/uuid-utils) |
| uvicorn | 0.40.0 | BSD-3-Clause | Tom Christie <tom@tomchristie.com> | [link](https://uvicorn.dev/) |
| validators | 0.35.0 | MIT License | Konsta Vesterinen <konsta@fastmonkeys.com> | [link](https://python-validators.github.io/validators) |
| virtualenv | 20.36.1 | MIT | - | [link](https://github.com/pypa/virtualenv) |
| watchfiles | 1.1.1 | MIT License | Samuel Colvin <s@muelcolvin.com> | [link](https://github.com/samuelcolvin/watchfiles) |
| websockets | 15.0.1 | BSD License | Aymeric Augustin <aymeric.augustin@m4x.org> | [link](https://github.com/python-websockets/websockets) |
| xlsxwriter | 3.2.9 | BSD License | John McNamara | [link](https://github.com/jmcnamara/XlsxWriter) |
| xxhash | 3.6.0 | BSD License | Yue Du | [link](https://github.com/ifduyue/python-xxhash) |
| yarl | 1.22.0 | Apache Software License | Andrew Svetlov | [link](https://github.com/aio-libs/yarl) |
| youtube-transcript-api | 1.2.3 | MIT License | Jonas Depoix | [link](https://github.com/jdepoix/youtube-transcript-api) |
| zipp | 3.23.0 | MIT | "Jason R. Coombs" <jaraco@jaraco.com> | [link](https://github.com/jaraco/zipp) |
| zstandard | 0.25.0 | BSD-3-Clause | Gregory Szorc <gregory.szorc@gmail.com> | [link](https://github.com/indygreg/python-zstandard) |

---

## Frontend dependencies (316)

Production dependencies only — build-time-only tooling is not distributed.

| Package | Version | License | Copyright | Project |
|---|---|---|---|---|
| @babel/runtime | 7.28.4 | MIT | The Babel Team | [link](https://github.com/babel/babel) |
| @floating-ui/core | 1.7.2 | MIT | atomiks | [link](https://github.com/floating-ui/floating-ui) |
| @floating-ui/dom | 1.7.2 | MIT | atomiks | [link](https://github.com/floating-ui/floating-ui) |
| @floating-ui/react-dom | 2.1.4 | MIT | atomiks | [link](https://github.com/floating-ui/floating-ui) |
| @floating-ui/utils | 0.2.10 | MIT | atomiks | [link](https://github.com/floating-ui/floating-ui) |
| @hookform/resolvers | 5.1.1 | MIT | bluebill1049 | [link](https://github.com/react-hook-form/resolvers) |
| @img/colour | 1.0.0 | MIT | - | [link](https://github.com/lovell/colour) |
| @img/sharp-libvips-linux-x64 | 1.2.4 | LGPL-3.0-or-later | Lovell Fuller | [link](https://github.com/lovell/sharp-libvips) |
| @img/sharp-libvips-linuxmusl-x64 | 1.2.4 | LGPL-3.0-or-later | Lovell Fuller | [link](https://github.com/lovell/sharp-libvips) |
| @img/sharp-linux-x64 | 0.34.5 | Apache-2.0 | Lovell Fuller | [link](https://github.com/lovell/sharp) |
| @img/sharp-linuxmusl-x64 | 0.34.5 | Apache-2.0 | Lovell Fuller | [link](https://github.com/lovell/sharp) |
| @next/env | 16.2.6 | MIT | Next.js Team | [link](https://github.com/vercel/next.js) |
| @next/swc-linux-x64-gnu | 16.2.6 | MIT | - | [link](https://github.com/vercel/next.js) |
| @next/swc-linux-x64-musl | 16.2.6 | MIT | - | [link](https://github.com/vercel/next.js) |
| @radix-ui/number | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/primitive | 1.1.2 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/primitive | 1.1.3 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-accordion | 1.2.12 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-alert-dialog | 1.1.14 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-arrow | 1.1.7 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-checkbox | 1.3.2 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-collapsible | 1.1.12 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-collection | 1.1.7 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-compose-refs | 1.1.2 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-context | 1.1.2 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-dialog | 1.1.14 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-dialog | 1.1.15 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-direction | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-dismissable-layer | 1.1.10 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-dismissable-layer | 1.1.11 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-dropdown-menu | 2.1.15 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-focus-guards | 1.1.2 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-focus-guards | 1.1.3 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-focus-scope | 1.1.7 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-id | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-label | 2.1.7 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-menu | 2.1.15 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-popover | 1.1.15 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-popper | 1.2.7 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-popper | 1.2.8 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-portal | 1.1.9 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-presence | 1.1.4 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-presence | 1.1.5 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-primitive | 2.1.3 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-progress | 1.1.7 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-radio-group | 1.3.8 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-roving-focus | 1.1.10 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-roving-focus | 1.1.11 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-scroll-area | 1.2.9 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-select | 2.2.5 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-separator | 1.1.7 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-slot | 1.2.3 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-tabs | 1.1.12 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-tooltip | 1.2.7 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-use-callback-ref | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-use-controllable-state | 1.2.2 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-use-effect-event | 0.0.2 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-use-escape-keydown | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-use-layout-effect | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-use-previous | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-use-rect | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-use-size | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/react-visually-hidden | 1.2.3 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @radix-ui/rect | 1.1.1 | MIT | - | [link](https://github.com/radix-ui/primitives) |
| @standard-schema/utils | 0.3.0 | MIT | Fabian Hiller | [link](https://github.com/standard-schema/standard-schema) |
| @swc/helpers | 0.5.15 | Apache-2.0 | 강동윤 | [link](https://github.com/swc-project/swc) |
| @tailwindcss/typography | 0.5.16 | MIT | - | [link](https://github.com/tailwindlabs/tailwindcss-typography) |
| @tanstack/query-core | 5.83.0 | MIT | tannerlinsley | [link](https://github.com/TanStack/query) |
| @tanstack/react-query | 5.83.0 | MIT | tannerlinsley | [link](https://github.com/TanStack/query) |
| @types/debug | 4.1.12 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/estree | 1.0.8 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/estree-jsx | 1.0.5 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/hast | 2.3.10 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/hast | 3.0.4 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/katex | 0.16.8 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/mdast | 4.0.4 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/ms | 2.1.0 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/prismjs | 1.26.5 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/react | 19.1.8 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/react-dom | 19.1.6 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/react-syntax-highlighter | 15.5.13 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/unist | 2.0.11 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @types/unist | 3.0.3 | MIT | - | [link](https://github.com/DefinitelyTyped/DefinitelyTyped) |
| @uiw/copy-to-clipboard | 1.0.17 | MIT | Kenny Wang | [link](https://github.com/uiwjs/copy-to-clipboard) |
| @uiw/react-markdown-preview | 5.1.5 | MIT | kenny wang | [link](https://github.com/uiwjs/react-markdown-preview) |
| @uiw/react-md-editor | 4.0.8 | MIT | kenny wang | [link](https://github.com/uiwjs/react-md-editor) |
| @ungap/structured-clone | 1.3.0 | ISC | Andrea Giammarchi | [link](https://github.com/ungap/structured-clone) |
| agent-base | 6.0.2 | MIT | Nathan Rajlich | [link](https://github.com/TooTallNate/node-agent-base) |
| aria-hidden | 1.2.6 | MIT | Anton Korzunov | [link](https://github.com/theKashey/aria-hidden) |
| asynckit | 0.4.0 | MIT | Alex Indigo | [link](https://github.com/alexindigo/asynckit) |
| axios | 1.18.1 | MIT | Matt Zabriskie | [link](https://github.com/axios/axios) |
| bail | 2.0.2 | MIT | Titus Wormer | [link](https://github.com/wooorm/bail) |
| baseline-browser-mapping | 2.10.37 | Apache-2.0 | - | [link](https://github.com/web-platform-dx/baseline-browser-mapping) |
| bcp-47-match | 2.0.3 | MIT | Titus Wormer | [link](https://github.com/wooorm/bcp-47-match) |
| boolbase | 1.0.0 | ISC | Felix Boehm | [link](https://github.com/fb55/boolbase) |
| call-bind-apply-helpers | 1.0.2 | MIT | Jordan Harband | [link](https://github.com/ljharb/call-bind-apply-helpers) |
| caniuse-lite | 1.0.30001799 | CC-BY-4.0 | Ben Briggs | [link](https://github.com/browserslist/caniuse-lite) |
| ccount | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/wooorm/ccount) |
| character-entities | 2.0.2 | MIT | Titus Wormer | [link](https://github.com/wooorm/character-entities) |
| character-entities-html4 | 2.1.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/character-entities-html4) |
| character-entities-legacy | 3.0.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/character-entities-legacy) |
| character-reference-invalid | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/wooorm/character-reference-invalid) |
| class-variance-authority | 0.7.1 | Apache-2.0 | Joe Bell | [link](https://github.com/joe-bell/cva) |
| client-only | 0.0.1 | MIT | - | - |
| clsx | 2.1.1 | MIT | Luke Edwards | [link](https://github.com/lukeed/clsx) |
| cmdk | 1.1.1 | MIT | Paco | [link](https://github.com/pacocoursey/cmdk) |
| combined-stream | 1.0.8 | MIT | Felix Geisendörfer | [link](https://github.com/felixge/node-combined-stream) |
| comma-separated-tokens | 2.0.3 | MIT | Titus Wormer | [link](https://github.com/wooorm/comma-separated-tokens) |
| commander | 8.3.0 | MIT | TJ Holowaychuk | [link](https://github.com/tj/commander.js) |
| css-selector-parser | 3.1.3 | MIT | Marat Dulin | [link](https://github.com/mdevils/css-selector-parser) |
| cssesc | 3.0.0 | MIT | Mathias Bynens | [link](https://github.com/mathiasbynens/cssesc) |
| csstype | 3.1.3 | MIT | Fredrik Nicol | [link](https://github.com/frenic/csstype) |
| date-fns | 4.1.0 | MIT | - | [link](https://github.com/date-fns/date-fns) |
| debug | 4.4.1 | MIT | Josh Junon | [link](https://github.com/debug-js/debug) |
| decode-named-character-reference | 1.2.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/decode-named-character-reference) |
| delayed-stream | 1.0.0 | MIT | Felix Geisendörfer | [link](https://github.com/felixge/node-delayed-stream) |
| dequal | 2.0.3 | MIT | Luke Edwards | [link](https://github.com/lukeed/dequal) |
| detect-libc | 2.1.2 | Apache-2.0 | Lovell Fuller | [link](https://github.com/lovell/detect-libc) |
| detect-node-es | 1.1.0 | MIT | Ilya Kantor | [link](https://github.com/thekashey/detect-node) |
| devlop | 1.1.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/devlop) |
| direction | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/wooorm/direction) |
| dunder-proto | 1.0.1 | MIT | Jordan Harband | [link](https://github.com/es-shims/dunder-proto) |
| entities | 6.0.1 | BSD-2-Clause | Felix Boehm | [link](https://github.com/fb55/entities) |
| es-define-property | 1.0.1 | MIT | Jordan Harband | [link](https://github.com/ljharb/es-define-property) |
| es-errors | 1.3.0 | MIT | Jordan Harband | [link](https://github.com/ljharb/es-errors) |
| es-object-atoms | 1.1.1 | MIT | Jordan Harband | [link](https://github.com/ljharb/es-object-atoms) |
| es-set-tostringtag | 2.1.0 | MIT | Jordan Harband | [link](https://github.com/es-shims/es-set-tostringtag) |
| escape-string-regexp | 5.0.0 | MIT | Sindre Sorhus | [link](https://github.com/sindresorhus/escape-string-regexp) |
| estree-util-is-identifier-name | 3.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/estree-util-is-identifier-name) |
| extend | 3.0.2 | MIT | Stefan Thomas | [link](https://github.com/justmoon/node-extend) |
| fault | 1.0.4 | MIT | Titus Wormer | [link](https://github.com/wooorm/fault) |
| follow-redirects | 1.16.0 | MIT | Ruben Verborgh | [link](https://github.com/follow-redirects/follow-redirects) |
| form-data | 4.0.6 | MIT | Felix Geisendörfer | [link](https://github.com/form-data/form-data) |
| format | 0.2.2 | MIT | Sami Samhuri | [link](https://github.com/samsonjs/format) |
| function-bind | 1.1.2 | MIT | Raynos | [link](https://github.com/Raynos/function-bind) |
| get-intrinsic | 1.3.0 | MIT | Jordan Harband | [link](https://github.com/ljharb/get-intrinsic) |
| get-nonce | 1.0.1 | MIT | Anton Korzunov | [link](https://github.com/theKashey/get-nonce) |
| get-proto | 1.0.1 | MIT | Jordan Harband | [link](https://github.com/ljharb/get-proto) |
| github-slugger | 2.0.0 | ISC | Dan Flettre | [link](https://github.com/Flet/github-slugger) |
| gopd | 1.2.0 | MIT | Jordan Harband | [link](https://github.com/ljharb/gopd) |
| has-symbols | 1.1.0 | MIT | Jordan Harband | [link](https://github.com/inspect-js/has-symbols) |
| has-tostringtag | 1.0.2 | MIT | Jordan Harband | [link](https://github.com/inspect-js/has-tostringtag) |
| hasown | 2.0.4 | MIT | Jordan Harband | [link](https://github.com/inspect-js/hasOwn) |
| hast-util-from-dom | 5.0.1 | ISC | Keith McKnight | [link](https://github.com/syntax-tree/hast-util-from-dom) |
| hast-util-from-html | 2.0.3 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-from-html) |
| hast-util-from-html-isomorphic | 2.0.0 | MIT | Remco Haszing | [link](https://github.com/syntax-tree/hast-util-from-html-isomorphic) |
| hast-util-from-parse5 | 8.0.3 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-from-parse5) |
| hast-util-has-property | 3.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-has-property) |
| hast-util-heading-rank | 3.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-heading-rank) |
| hast-util-is-element | 3.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-is-element) |
| hast-util-parse-selector | 3.1.1 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-parse-selector) |
| hast-util-parse-selector | 4.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-parse-selector) |
| hast-util-raw | 9.1.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-raw) |
| hast-util-sanitize | 5.0.2 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-sanitize) |
| hast-util-select | 6.0.4 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-select) |
| hast-util-to-html | 9.0.5 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-to-html) |
| hast-util-to-jsx-runtime | 2.3.6 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-to-jsx-runtime) |
| hast-util-to-parse5 | 8.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-to-parse5) |
| hast-util-to-string | 3.0.1 | MIT | Titus Wormer | [link](https://github.com/rehypejs/rehype-minify/tree/main/packages/hast-util-to-string) |
| hast-util-to-text | 4.0.2 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-to-text) |
| hast-util-whitespace | 3.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hast-util-whitespace) |
| hastscript | 7.2.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hastscript) |
| hastscript | 9.0.1 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/hastscript) |
| highlight.js | 10.7.3 | BSD-3-Clause | Ivan Sagalaev | [link](https://github.com/highlightjs/highlight.js) |
| highlightjs-vue | 1.0.0 | CC0-1.0 | Sara Lissette | [link](https://github.com/highlightjs/highlightjs-vue) |
| html-parse-stringify | 3.0.1 | MIT | Henrik Joreteg | [link](https://github.com/henrikjoreteg/html-parse-stringify) |
| html-url-attributes | 3.0.1 | MIT | Titus Wormer | [link](https://github.com/rehypejs/rehype-minify/tree/main/packages/html-url-attributes) |
| html-void-elements | 3.0.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/html-void-elements) |
| https-proxy-agent | 5.0.1 | MIT | Nathan Rajlich | [link](https://github.com/TooTallNate/node-https-proxy-agent) |
| i18next | 25.7.4 | MIT | Jan Mühlemann | [link](https://github.com/i18next/i18next) |
| i18next-browser-languagedetector | 8.2.0 | MIT | Jan Mühlemann | [link](https://github.com/i18next/i18next-browser-languageDetector) |
| inline-style-parser | 0.2.4 | MIT | - | [link](https://github.com/remarkablemark/inline-style-parser) |
| is-alphabetical | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/wooorm/is-alphabetical) |
| is-alphanumerical | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/wooorm/is-alphanumerical) |
| is-decimal | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/wooorm/is-decimal) |
| is-hexadecimal | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/wooorm/is-hexadecimal) |
| is-plain-obj | 4.1.0 | MIT | Sindre Sorhus | [link](https://github.com/sindresorhus/is-plain-obj) |
| katex | 0.16.47 | MIT | - | [link](https://github.com/KaTeX/KaTeX) |
| lodash.castarray | 4.4.0 | MIT | John-David Dalton | [link](https://github.com/lodash/lodash) |
| lodash.isplainobject | 4.0.6 | MIT | John-David Dalton | [link](https://github.com/lodash/lodash) |
| lodash.merge | 4.6.2 | MIT | John-David Dalton | [link](https://github.com/lodash/lodash) |
| longest-streak | 3.1.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/longest-streak) |
| lowlight | 1.20.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/lowlight) |
| lucide-react | 0.525.0 | ISC | Eric Fennis | [link](https://github.com/lucide-icons/lucide) |
| markdown-table | 3.0.4 | MIT | Titus Wormer | [link](https://github.com/wooorm/markdown-table) |
| math-intrinsics | 1.1.0 | MIT | Jordan Harband | [link](https://github.com/es-shims/math-intrinsics) |
| mdast-util-find-and-replace | 3.0.2 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-find-and-replace) |
| mdast-util-from-markdown | 2.0.2 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-from-markdown) |
| mdast-util-gfm | 3.1.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-gfm) |
| mdast-util-gfm-autolink-literal | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-gfm-autolink-literal) |
| mdast-util-gfm-footnote | 2.1.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-gfm-footnote) |
| mdast-util-gfm-strikethrough | 2.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-gfm-strikethrough) |
| mdast-util-gfm-table | 2.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-gfm-table) |
| mdast-util-gfm-task-list-item | 2.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-gfm-task-list-item) |
| mdast-util-math | 3.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-math) |
| mdast-util-mdx-expression | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-mdx-expression) |
| mdast-util-mdx-jsx | 3.2.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-mdx-jsx) |
| mdast-util-mdxjs-esm | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-mdxjs-esm) |
| mdast-util-phrasing | 4.1.0 | MIT | Victor Felder | [link](https://github.com/syntax-tree/mdast-util-phrasing) |
| mdast-util-to-hast | 13.2.1 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-to-hast) |
| mdast-util-to-markdown | 2.1.2 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-to-markdown) |
| mdast-util-to-string | 4.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/mdast-util-to-string) |
| micromark | 4.0.2 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark) |
| micromark-core-commonmark | 2.0.3 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-core-commonmark) |
| micromark-extension-gfm | 3.0.0 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark-extension-gfm) |
| micromark-extension-gfm-autolink-literal | 2.1.0 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark-extension-gfm-autolink-literal) |
| micromark-extension-gfm-footnote | 2.1.0 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark-extension-gfm-footnote) |
| micromark-extension-gfm-strikethrough | 2.1.0 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark-extension-gfm-strikethrough) |
| micromark-extension-gfm-table | 2.1.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark-extension-gfm-table) |
| micromark-extension-gfm-tagfilter | 2.0.0 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark-extension-gfm-tagfilter) |
| micromark-extension-gfm-task-list-item | 2.1.0 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark-extension-gfm-task-list-item) |
| micromark-extension-math | 3.1.0 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark-extension-math) |
| micromark-factory-destination | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-factory-destination) |
| micromark-factory-label | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-factory-label) |
| micromark-factory-space | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-factory-space) |
| micromark-factory-title | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-factory-title) |
| micromark-factory-whitespace | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-factory-whitespace) |
| micromark-util-character | 2.1.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-character) |
| micromark-util-chunked | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-chunked) |
| micromark-util-classify-character | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-classify-character) |
| micromark-util-combine-extensions | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-combine-extensions) |
| micromark-util-decode-numeric-character-reference | 2.0.2 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-decode-numeric-character-reference) |
| micromark-util-decode-string | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-decode-string) |
| micromark-util-encode | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-encode) |
| micromark-util-html-tag-name | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-html-tag-name) |
| micromark-util-normalize-identifier | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-normalize-identifier) |
| micromark-util-resolve-all | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-resolve-all) |
| micromark-util-sanitize-uri | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-sanitize-uri) |
| micromark-util-subtokenize | 2.1.0 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-subtokenize) |
| micromark-util-symbol | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-symbol) |
| micromark-util-types | 2.0.2 | MIT | Titus Wormer | [link](https://github.com/micromark/micromark/tree/main/packages/micromark-util-types) |
| mime-db | 1.52.0 | MIT | - | [link](https://github.com/jshttp/mime-db) |
| mime-types | 2.1.35 | MIT | - | [link](https://github.com/jshttp/mime-types) |
| ms | 2.1.3 | MIT | - | [link](https://github.com/vercel/ms) |
| nanoid | 3.3.11 | MIT | Andrey Sitnik | [link](https://github.com/ai/nanoid) |
| next | 16.2.6 | MIT | - | [link](https://github.com/vercel/next.js) |
| nth-check | 2.1.1 | BSD-2-Clause | Felix Boehm | [link](https://github.com/fb55/nth-check) |
| parse-entities | 4.0.2 | MIT | Titus Wormer | [link](https://github.com/wooorm/parse-entities) |
| parse-numeric-range | 1.3.0 | ISC | Euan Kemp | [link](https://github.com/euank/node-parse-numeric-range) |
| parse5 | 7.3.0 | MIT | Ivan Nikulin | [link](https://github.com/inikulin/parse5) |
| picocolors | 1.1.1 | ISC | Alexey Raspopov | [link](https://github.com/alexeyraspopov/picocolors) |
| postcss | 8.5.10 | MIT | Andrey Sitnik | [link](https://github.com/postcss/postcss) |
| postcss-selector-parser | 6.0.10 | MIT | - | [link](https://github.com/postcss/postcss-selector-parser) |
| prismjs | 1.30.0 | MIT | Lea Verou | [link](https://github.com/PrismJS/prism) |
| property-information | 6.5.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/property-information) |
| property-information | 7.1.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/property-information) |
| proxy-from-env | 2.1.0 | MIT | Rob Wu | [link](https://github.com/Rob--W/proxy-from-env) |
| react | 19.2.3 | MIT | - | [link](https://github.com/facebook/react) |
| react-dom | 19.2.3 | MIT | - | [link](https://github.com/facebook/react) |
| react-hook-form | 7.60.0 | MIT | Beier | [link](https://github.com/react-hook-form/react-hook-form) |
| react-i18next | 16.5.3 | MIT | Jan Mühlemann | [link](https://github.com/i18next/react-i18next) |
| react-markdown | 10.1.0 | MIT | Espen Hovlandsdal | [link](https://github.com/remarkjs/react-markdown) |
| react-markdown | 9.0.3 | MIT | Espen Hovlandsdal | [link](https://github.com/remarkjs/react-markdown) |
| react-remove-scroll | 2.7.1 | MIT | Anton Korzunov | [link](https://github.com/theKashey/react-remove-scroll) |
| react-remove-scroll-bar | 2.3.8 | MIT | Anton Korzunov | [link](https://github.com/theKashey/react-remove-scroll-bar) |
| react-style-singleton | 2.2.3 | MIT | Anton Korzunov | [link](https://github.com/theKashey/react-style-singleton) |
| react-syntax-highlighter | 16.1.1 | MIT | Conor Hastings | [link](https://github.com/react-syntax-highlighter/react-syntax-highlighter) |
| refractor | 4.9.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/refractor) |
| refractor | 5.0.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/refractor) |
| rehype | 13.0.2 | MIT | Titus Wormer | [link](https://github.com/rehypejs/rehype/tree/main/packages/rehype) |
| rehype-attr | 3.0.3 | MIT | Kenny Wong | [link](https://github.com/jaywcjlove/rehype-attr) |
| rehype-autolink-headings | 7.1.0 | MIT | Titus Wormer | [link](https://github.com/rehypejs/rehype-autolink-headings) |
| rehype-ignore | 2.0.2 | MIT | Kenny Wong | [link](https://github.com/jaywcjlove/rehype-ignore) |
| rehype-katex | 7.0.1 | MIT | Junyoung Choi | [link](https://github.com/remarkjs/remark-math/tree/main/packages/rehype-katex) |
| rehype-parse | 9.0.1 | MIT | Titus Wormer | [link](https://github.com/rehypejs/rehype/tree/main/packages/rehype-parse) |
| rehype-prism-plus | 2.0.0 | MIT | Timothy Lin | [link](https://github.com/timlrx/rehype-prism-plus) |
| rehype-prism-plus | 2.0.1 | MIT | Timothy Lin | [link](https://github.com/timlrx/rehype-prism-plus) |
| rehype-raw | 7.0.0 | MIT | Titus Wormer | [link](https://github.com/rehypejs/rehype-raw) |
| rehype-rewrite | 4.0.2 | MIT | Kenny Wong | [link](https://github.com/jaywcjlove/rehype-rewrite) |
| rehype-sanitize | 6.0.0 | MIT | Titus Wormer | [link](https://github.com/rehypejs/rehype-sanitize) |
| rehype-slug | 6.0.0 | MIT | Titus Wormer | [link](https://github.com/rehypejs/rehype-slug) |
| rehype-stringify | 10.0.1 | MIT | Titus Wormer | [link](https://github.com/rehypejs/rehype/tree/main/packages/rehype-stringify) |
| remark-gfm | 4.0.1 | MIT | Titus Wormer | [link](https://github.com/remarkjs/remark-gfm) |
| remark-github-blockquote-alert | 1.3.1 | MIT | Kenny Wong | [link](https://github.com/jaywcjlove/remark-github-blockquote-alert) |
| remark-math | 6.0.0 | MIT | Junyoung Choi | [link](https://github.com/remarkjs/remark-math/tree/main/packages/remark-math) |
| remark-parse | 11.0.0 | MIT | Titus Wormer | [link](https://github.com/remarkjs/remark/tree/main/packages/remark-parse) |
| remark-rehype | 11.1.2 | MIT | Titus Wormer | [link](https://github.com/remarkjs/remark-rehype) |
| remark-stringify | 11.0.0 | MIT | Titus Wormer | [link](https://github.com/remarkjs/remark/tree/main/packages/remark-stringify) |
| scheduler | 0.27.0 | MIT | - | [link](https://github.com/facebook/react) |
| semver | 7.7.3 | ISC | GitHub Inc. | [link](https://github.com/npm/node-semver) |
| sharp | 0.34.5 | Apache-2.0 | Lovell Fuller | [link](https://github.com/lovell/sharp) |
| sonner | 2.0.6 | MIT | Emil Kowalski | [link](https://github.com/emilkowalski/sonner) |
| source-map-js | 1.2.1 | BSD-3-Clause | Valentin 7rulnik Semirulnik | [link](https://github.com/7rulnik/source-map-js) |
| space-separated-tokens | 2.0.2 | MIT | Titus Wormer | [link](https://github.com/wooorm/space-separated-tokens) |
| stringify-entities | 4.0.4 | MIT | Titus Wormer | [link](https://github.com/wooorm/stringify-entities) |
| style-to-js | 1.1.17 | MIT | Mark | [link](https://github.com/remarkablemark/style-to-js) |
| style-to-object | 1.0.9 | MIT | Mark | [link](https://github.com/remarkablemark/style-to-object) |
| styled-jsx | 5.1.6 | MIT | - | [link](https://github.com/vercel/styled-jsx) |
| tailwind-merge | 3.3.1 | MIT | Dany Castillo | [link](https://github.com/dcastil/tailwind-merge) |
| tailwindcss | 4.1.11 | MIT | - | [link](https://github.com/tailwindlabs/tailwindcss) |
| trim-lines | 3.0.1 | MIT | Titus Wormer | [link](https://github.com/wooorm/trim-lines) |
| trough | 2.2.0 | MIT | Titus Wormer | [link](https://github.com/wooorm/trough) |
| tslib | 2.8.1 | 0BSD | Microsoft Corp. | [link](https://github.com/Microsoft/tslib) |
| typescript | 5.8.3 | Apache-2.0 | Microsoft Corp. | [link](https://github.com/microsoft/TypeScript) |
| unified | 11.0.5 | MIT | Titus Wormer | [link](https://github.com/unifiedjs/unified) |
| unist-util-filter | 5.0.1 | MIT | Eugene Sharygin | [link](https://github.com/syntax-tree/unist-util-filter) |
| unist-util-find-after | 5.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/unist-util-find-after) |
| unist-util-is | 6.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/unist-util-is) |
| unist-util-position | 5.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/unist-util-position) |
| unist-util-remove-position | 5.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/unist-util-remove-position) |
| unist-util-stringify-position | 4.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/unist-util-stringify-position) |
| unist-util-visit | 5.0.0 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/unist-util-visit) |
| unist-util-visit-parents | 6.0.1 | MIT | Titus Wormer | [link](https://github.com/syntax-tree/unist-util-visit-parents) |
| use-callback-ref | 1.3.3 | MIT | theKashey | [link](https://github.com/theKashey/use-callback-ref) |
| use-debounce | 10.0.6 | MIT | Nik | [link](https://github.com/xnimorz/use-debounce) |
| use-sidecar | 1.1.3 | MIT | theKashey | [link](https://github.com/theKashey/use-sidecar) |
| use-sync-external-store | 1.6.0 | MIT | - | [link](https://github.com/facebook/react) |
| util-deprecate | 1.0.2 | MIT | Nathan Rajlich | [link](https://github.com/TooTallNate/util-deprecate) |
| vfile | 6.0.3 | MIT | Titus Wormer | [link](https://github.com/vfile/vfile) |
| vfile-location | 5.0.3 | MIT | Titus Wormer | [link](https://github.com/vfile/vfile-location) |
| vfile-message | 4.0.2 | MIT | Titus Wormer | [link](https://github.com/vfile/vfile-message) |
| void-elements | 3.1.0 | MIT | hemanth.hm | [link](https://github.com/pugjs/void-elements) |
| web-namespaces | 2.0.1 | MIT | Titus Wormer | [link](https://github.com/wooorm/web-namespaces) |
| zod | 4.0.5 | MIT | Colin McDonnell | [link](https://github.com/colinhacks/zod) |
| zustand | 5.0.6 | MIT | Paul Henschel | [link](https://github.com/pmndrs/zustand) |
| zwitch | 2.0.4 | MIT | Titus Wormer | [link](https://github.com/wooorm/zwitch) |
