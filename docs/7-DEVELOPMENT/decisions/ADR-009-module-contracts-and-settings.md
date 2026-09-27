# ADR 009 — Module contracts, settings and honest lifecycle states

Status: accepted. Date: 2026-09-21. Author: karacaismail.

## Context and decision

The original module catalog forced all external/build modules on and offered no
settings contract. Turn the application layer into a modular monolith with a
single composition root and typed in-process request/reply contracts. Keep native
CLI/MLX/Ollama processes as infrastructure adapters: combining their incompatible
runtimes into the API process would reduce isolation and destabilize active work.

The current feature services are **not all physically in one process**. The
framework provides a modular-monolith application boundary, not a claim that the
legacy research service has already been merged into the API worker.

- `Registry` owns discovery, graph validation and a versioned atomic settings
  repository. It has no presentation or transport responsibilities.
- `ModuleManager` owns application commands, admission/idle guards and the HTTP
  adapter. FastAPI controllers only validate requests and translate errors.
- `Module` is the abstract public interface; `ConfiguredModule` implements the
  manifest-defined settings/model contracts. `ModuleBus` is the composition root
  and synchronous query dispatcher. Consumers receive detached data objects.
- `SettingsQuery` and `ModelPolicyRequest` are versioned public contracts. No
  module imports another module's implementation or writes its storage.
- React uses **MVVM**, not class components: immutable `ModuleSettingsDraft`
  domain model, repository port + HTTP adapter, `useModuleSettings` view model,
  and schema-driven presentation components. Hooks are appropriate React view
  models; OOP is used for state/domain/data ports where it improves boundaries.

## Lifecycle semantics

All installed modules can have a desired enabled state. Disabling retains data,
credentials and preferences. Existing requests can finish. A dependent module
must be disabled before its dependency; no silent cascading shutdown.

Runtime integrations gate **new Open Notebook requests**. They do not stop an OS
service, sign out of an account, change vectors or remove model files. Research
also checks its scheduler: pause incomplete runs and finish active work first.
The local-maintenance module gates the policy-aware maintenance CLI; old operator
scripts and third-party direct CLI calls remain outside the notebook boundary.

`local-workspace` and `local-processing` are legacy whole-file build adapters.
For these, `enabled` means desired state, `active` means bundled/applied state,
and `pending_build` identifies any unapplied toggle or setting. The UI must never
present an unbuilt change as effective. Export configuration, run
`scripts/prepare_modules.py --state ...`, then build/deploy the isolated output.
Future modules should use runtime ports instead of adding whole-file overlays.

## Settings, consistency and persistence

Manifest `settings` owns typed fields/defaults/ranges. `model_policies` and
`request_defaults` reference those keys; invalid references fail preflight.
Unknown fields, bool-as-integer, out-of-range values and stale revisions are
rejected. No secret/executable/path fields are accepted by this UI schema.

State v2 contains `enabled`, `settings`, a snapshot `revision` and independent
`module_revisions`. Unrelated module edits do not conflict. v1 migrates without losing
previous runtime choices; forced external/build choices become explicit once.
New bundles enable their installed modules by default. Empty core builds stay
empty. Atomic rename and fsync protect writes; an exclusive POSIX lease serializes
API writers against active proxy requests. Optimistic revision checks prevent
lost updates across browser tabs. Worker reads do not cache policy state.

Exported policies are non-secret snapshots, **not live remote controllers**.
Maintenance CLIs require a fresh export and honor its enabled state. Building
preserves installed disabled runtime modules so they can be enabled later, but
removes disabled build overlays. `modules/defaults.json` seeds a fresh install;
it never overwrites an existing data directory's settings.

## Capability integration and limits

Notebook model construction and podcast configuration call the public model
policy port. Local embedding policy governs Ollama embedding models without
changing the chosen model or dimensions. Account/speech policies match their
specific managed model names. Request timeouts do not alter native CLI deadlines
or already-running calls. Research defaults only fill missing new-run fields;
report import and existing research records pass through unchanged.

Content-core constructs its own speech models and can fall back to another
provider. `ContentAudioAdapter` closes both provider slots with an unsupported
provider when the local module is disabled. Esperanto rejects that provider
before network access. Non-audio extraction remains available; no paid-provider
fallback is introduced. This is an explicit compatibility adapter until
content-core exposes a native model-admission hook.

## UX and extension rules

Settings opens General. Modules settings uses searchable navigation, explicit
state badges, a selected-module settings panel, staged edits, save/discard,
visible failure messages, accessible switches and progressive technical detail.
Switching modules/tabs retains edit drafts; catalog polling cannot overwrite them.
The reference UI-kit document informs these patterns; no competing UI framework
was introduced into the existing React/Tailwind/shadcn stack.

For a new module:

1. Own its manifest, settings, view-model/domain logic and adapters under its
   module directory. Keep core changes limited to reusable extension points.
2. Declare dependencies and public contracts. Pass immutable records or artifact
   references; do not mutate another module's reports or import its internals.
3. Make admission, completion, failure and cancellation explicit. Provide a
   user-visible reason and next action; never silently repeat ambiguous work.
4. Use the shared settings/component catalog, i18n, semantic labels and keyboard
   controls. Keep network access out of views; no direct Axios in components.
5. Test lifecycle, disabled admission, settings persistence/conflicts, boundaries,
   and real DOM behavior. New fields require an actual consumer and documented
   apply timing. Do not add decorative controls that do nothing.

## Tradeoffs

Declarative settings avoid one bespoke editor per module. A synchronous query
bus is enough for current configuration/model use cases; a durable event outbox
should be added only when a real asynchronous inter-module transfer requires it.
No arbitrary public RPC, dynamic code installation, process termination, report
migration or database schema change is included in this change.
