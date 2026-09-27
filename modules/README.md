# Optional modules

The default source build runs the original notebook without enabling optional
features. Core integration is limited to the module registry, authenticated API
gate, navigation/page host and module settings screen.

| Module | Ownership | Activation |
|---|---|---|
| `hybrid-search` | Multilingual passage search, rank fusion and local neural reranking for Search/Ask | Runtime UI/API gate |
| `multi-model-research` | Eight core research tasks plus four optional preliminary tasks, evidence protocol, imports, retries, run/stage controls, Chrome extension and native bridge | Runtime UI/API gate |
| `local-files` | Incremental local file catalog, filename/content retrieval, Office readers and local OCR | Runtime UI/API gate |
| `account-models` | Signed-in Codex/Claude/Gemini CLI adapter | External service |
| `local-audio` | Local Whisper transcription and macOS fallback speech | External service |
| `natural-voice` | Local neural speech, voice configuration | External service |
| `local-embeddings` | Ollama embedding setup profile | External service |
| `local-processing` | Source/provider/podcast compatibility overlays and CPU constraints | Build |
| `local-workspace` | Local interface/theme customizations | Build |
| `local-deployment` | Portable service initialization, backups and preserved launcher templates | Operator tooling |

No tokens, account profiles, private reports, downloaded models or audio references
are distributed. Code is contributed by `karacaismail`; the customization inventory
includes work developed collaboratively with Codex and Claude.

See the [feature and UX summary](../docs/7-DEVELOPMENT/module-feature-summary.md)
for the complete branch overview and validation boundaries.

## Build a selected installation

From the repository root, choose a **new directory outside this checkout**:

```sh
python scripts/prepare_modules.py --output /tmp/open-notebook-with-modules \
  --modules multi-model-research,local-workspace,local-processing,local-audio,natural-voice,local-embeddings,local-deployment
```

Dependencies (including `account-models`) are selected automatically. Build the
staged directory using the normal repository instructions. The existing Dockerfile
also works from this staged tree; containers may run through Colima. A host process
deployment can use the same staged Python and frontend sources.

For an upstream-only build, use `--modules ''` or build the original checkout.
Overlays are applied only after their upstream SHA-256 hashes match. An error means
the overlay must be reviewed/rebased; do not bypass it by copying the old file.

## Runtime configuration

Set the following on the **API process**, using the same research key as the native
sidecar (keep it in a private environment file, never in Git):

```dotenv
OPEN_NOTEBOOK_MODULES=multi-model-research
LOCAL_RESEARCH_URL=http://127.0.0.1:8320
LOCAL_RESEARCH_KEY=replace-with-your-private-sidecar-key
# Optional; defaults shown:
OPEN_NOTEBOOK_MODULE_DIR=modules
OPEN_NOTEBOOK_MODULE_STATE=data/modules.json
```

For a Colima API container with a host research service, the service URL is
`http://host.lima.internal:8320`. `modules/installed.json` is produced by the build
tool. A runtime module cannot be enabled if its UI/dependencies were not selected
for that build. The settings screen is `/settings/modules`; research keeps `/research`
and existing `?run=...` bookmarks.

Desired module states and per-module preferences persist in the module state file and override initial environment
defaults. They never delete data or terminate external services. Pause unfinished
research jobs and wait for active work to finish before disabling research.

## Settings and lifecycle

`/settings` opens **General**; **Modules settings** is the second tab.
`/settings/modules` is a compatible direct link to that tab. Every installed
module has preferences and a desired on/off switch. Dependencies are explicit.
Changes have a saved revision; stale edits are rejected without overwriting data.

Runtime integrations close admission for new notebook requests, preserving
running calls and files. Research requires idle/paused work. Local maintenance
is enforced by the new policy-aware CLI, not by killing existing launcher jobs.
Two legacy build adapters display **Build pending** until a new build applies
those choices; the running state is shown separately.

Download **Export configuration**, then prepare a build from the desired state:

```sh
python scripts/prepare_modules.py --output /tmp/notebook-next \
  --state /path/to/open-notebook-modules.json
```

This removes disabled build overlays, retains disabled runtime modules for later
re-enabling, and applies build preferences. Build and deploy the staged tree using
the existing process. `modules/defaults.json` only seeds new installations;
persistent `data/modules.json` takes precedence and is never replaced by a build.

For a quiescent backup using the current module policy:

```sh
python modules/local-deployment/backup.py \
  --module-state /path/to/open-notebook-modules.json \
  --output /private/backup.tar.gz /private/exported-data
```

Use a fresh export after changing settings. The CLI refuses disabled maintenance
and never overwrites an archive. With XZ selected, use a `.tar.xz` filename.

The standard for new modules is [ADR-009](../docs/7-DEVELOPMENT/decisions/ADR-009-module-contracts-and-settings.md):
class-based domain/adapters, typed public contracts, MVVM presentation, owned
settings, no cross-module internal imports, shared UI components and explicit
failure/apply feedback. Native AI processes remain external infrastructure; the
legacy research engine has not been physically merged into the API process.

## Native services

Initialize a private directory outside the repository, without overwriting keys:

```sh
python modules/local-deployment/install_sidecar.py account-models --state /private/path/accounts
python modules/local-deployment/install_sidecar.py multi-model-research --state /private/path/research
```

Create separate Python environments. Install each service's `requirements.lock`
where present; the account adapter uses the standard library. Review the generated
`config.json`: set CLI executable paths, available model IDs, account timeouts and
the research service's absolute `bridge_key_path`. Authenticate using each CLI's
official login flow. The examples record the original installation choices; they
do not guarantee model availability or subscription eligibility.

```sh
python modules/local-deployment/run_sidecar.py account-models \
  --state /private/path/accounts --python /private/path/accounts/venv/bin/python
python modules/local-deployment/run_sidecar.py multi-model-research \
  --state /private/path/research --python /private/path/research/venv/bin/python
```

For existing installations, point `RESEARCH_ROOT`, `ACCOUNT_BRIDGE_ROOT`,
`LOCAL_AUDIO_ROOT` and `NATURAL_VOICE_ROOT` at their **existing** private directories.
Keep the original research database, report folders, keys and voice assets. Do not
copy a Chrome profile or extract cookies. Natural voice references and model weights
must already exist in the selected private root; packaging does not regenerate them.

For the Chrome extension, load `multi-model-research/browser-extension` unpacked.
Copy its ID from `chrome://extensions`. Run `service/install_extension_host.py
--extension-id YOUR_EXTENSION_ID` with `RESEARCH_ROOT` set to the private research
directory containing `venv/bin/python`. The installer records that ID in private
configuration; `run_sidecar.py` passes it to the service. Keep the unpacked extension
in a stable directory (moving it can change its ID). Existing installations keep
their original path and ID. Chrome stays signed in under the user's existing account.
The module uses its own task windows; provider verification can still require a user.

## Existing launcher migration and backup

`local-deployment/legacy-templates` preserves the previous Colima-aware startup,
consistent backup and login scripts with home paths replaced by `__USER_HOME__`.
These are migration references, **not directly executable installation scripts**.
They expect the legacy directory layout. Keep an existing working launcher until
its operator-specific compose paths and service definitions have been migrated.

The portable `backup.py` creates a new private archive of explicitly selected
quiescent directories. For active SurrealDB or SQLite data, use a database-native
export or stop writers first. In Colima, a host directory with the same spelling as
a VM bind path may be empty: export the actual VM/container data before archiving.
Never change volume mounts as part of a module migration.

## Development and validation

* Module boundaries: `uv run pytest tests/test_module_system.py`.
* Research sidecar: run `python -m pytest tests` inside its `service` directory using
  its pinned environment. Tests create temporary keys/state and use local DOM fixtures.
* Account sidecar: run `python -m pytest test_server.py` inside its `service` directory.
* Frontend: run `npm ci`, `npm test`, `npx tsc --noEmit`, and `npm run build` in both
  the core and selected-module frontend directories.

See [the architecture decision](../docs/7-DEVELOPMENT/module-system.md) and the
machine-readable [customization inventory](CUSTOMIZATION-INVENTORY.json).

### Yerel arama ve ön araştırma ekleri

`local-files`, özel anahtarlı yerel servis üzerinden dosya kataloğu ve hibrit arama sunar. `FrontendSpec.search_widget` genel Search sayfasındaki sorguyu isteğe bağlı modül görünümüne iletir; modüller birbirlerinin iç kodlarını içe aktarmaz. `ServiceSpec.control_path` duraklatılabilen servislerin etkinlik durumunu modül ayarlarıyla eşleştirir. Servis geçişi başarısızsa önceki modül yapılandırması geri yüklenir. Dağıtıma ait `data/module-services.json`, konteyneri yeniden oluşturmadan sabit servis adresi ve anahtar dosyası tanımlayabilir; kullanıcı API isteği bu dosyayı değiştiremez.

Ayrıntılar: [yerel dosyalar](local-files/README.md), [ön araştırma](multi-model-research/PRELIMINARY-RESEARCH.md).
