# ADR-011: Research event/condition/action rules and measured token accounting

- Status: Accepted
- Date: 2026-09-21
- Modules: multi-model-research, account-models
- Supersedes ADR-010's measured limitation for the 4ab4eb02 final packet and its local calibration values.

## Decision

Use a deterministic `ResearchRules` service, immutable typed `Rule` definitions and versioned JSON decisions. Conditions inspect facts, never execute instructions from imported reports. Actions are restricted to reversible reference encoding, preservation warnings and blocking submission. This is structural policy, not a truth classifier or a generic scripting language.

The packet preview and launch path use the same evaluator. A preview is read-only. Every enforced pre-submission decision is appended to the stage's `policy_events`, with time, packet hash, rule version, triggered IDs, reasons and supporting facts. Exported `research.json` retains this history. The frontend displays findings and their evidence. Critical protections cannot be disabled through report text or settings. Rule changes require code review and regression tests.

`markdown-v2` recognizes fenced blocks as complete blocks, instead of a regex that can mistake a Mermaid closing fence for a new unlabelled block. The evidence audit and compact reference encoder share this parser. Backtick/tilde fences, fence length, CRLF, nested fence text, preceding diagrams, malformed ledgers and duplicate identities are covered. Exact repeated ledger bodies may share a reference; distinct candidate ledgers or duplicate claim IDs cannot. Report bytes are never rewritten. `markdown-v1` rendering remains available for old exports; sent packets remain SHA-pinned. Only never-sent unfinished account stages migrate.

A reference is legal only when inverse expansion restores the original complete assessment, including source unions, limits and rejection history. Identical report and attachment content is diagnosed but not deleted: different origins remain visible. Only exact URL strings deduplicate; query strings, fragments, trailing slashes and case are not normalized as if equivalent.

## Event / condition / action catalog

| ID | Event and condition | Action |
|---|---|---|
| ECA-001 | Packet prepared; exact duplicate URL entries | One bibliography entry, retain all stage attribution and inline citations |
| ECA-002 | Packet prepared; full assessment already exists unambiguously in report | Reversible reference with explicit overrides; validate inverse |
| ECA-003 | Packet prepared; identical report body across stages | Warn; keep both origins and both report bodies; no independent-vote claim |
| ECA-004 | Packet prepared; identical evidence attachments | Warn; retain every attachment and origin |
| ECA-005 | Packet prepared; conflicting ledger blocks or duplicate/malformed claim IDs | Warn; do not choose one or collapse ambiguous assessments |
| ECA-006 | Packet prepared; same claim has different statuses | Preserve complete history; do not use last-write-wins or majority |
| ECA-007 | Packet prepared; upstream evidence-audit warnings | Surface warnings; omission is neither rejection nor confirmation |
| ECA-008 | Packet prepared; research date missing | Warn; do not substitute import date |
| ECA-009 | Packet prepared; research date after target date | Warn; preserve content, distinguish research time from event time |
| ECA-010 | Before submission; input utilization >=85% and <=100% | Warn; do not pause merely for this warning |
| ECA-011 | Before submission; full counted input >configured budget | `context_limit`, no provider call, no auto-retry, no truncation |
| ECA-012 | Before submission; lossless reference round-trip fails | `integrity_error`, no provider call or auto-retry |
| ECA-013 | Before submission; attachment SHA mismatch | `integrity_error`, no provider call or auto-retry |
| ECA-014 | Packet prepared; no runtime-bound calibration | Label estimate uncalibrated |
| ECA-015 | Provider preflight; CLI/model/effort/instructions fingerprint changed or unavailable | `calibration_required`, no provider POST or auto-retry |
| ECA-016 | Before submission; report hash, saved input hash or required saved input fails | `integrity_error`; preserve original files, do not rebuild a different sent request |
| ECA-017 | Historical saved packet predates rules | Verify saved input hash, label historical audit unavailable; do not pretend a current reconstructed packet was the sent packet |
| ECA-018 | Same-round provider payload identities differ | Block with integrity_error before submission; compare exact data-file SHA-256, bytes and format |

Retry, idempotency and uncertain browser-submission safeguards remain in their existing owners. The rules do not grant permission to repeat uncertain submissions or bypass provider verification. Account response truncation is rejected by the bridge. These are not new ECA implementations and are not counted as additional rules here.

## Measured calibration

Six ChatGPT samples (three historical completed calls plus three new no-tools/max-effort token probes) report exactly `o200k_base(serialized CLI input) + 11393`. Current probes span 4061, 32061 and 154878 raw tokens. Use local ChatGPT multiplier 1.0, overhead 15489 = observed 11393 + 4096 reserve, tied to the current CLI version/model/effort/system command fingerprint. No input limit increase. The probe wraps the full candidate in a quoted test envelope and requests only `CALIBRATION_OK`; it proves transport/usage, not synthesis quality.

The real new final packet has 154711 raw prompt tokens, 154836 raw CLI tokens and **170325 counted tokens**: 9675 spare (5.375%) under the unchanged 180000 limit. The full-size calibration probe adds 42 raw wrapper tokens and reports 166271 input tokens, i.e. exactly 154878 + 11393. All report/evidence bytes and structured claim histories round-trip.

Claude single-message observations including cache are 7910, 58537 and 186733 against 4061, 32061 and 109427 raw o200k tokens. Its old 1.25 multiplier underestimated this Turkish content. Local policy is now 1.95 + 4096, bound to its runtime fingerprint. Aggregated billable usage must not be called one context-window measurement; bridge responses expose first/max context counts separately when the CLI supplies iteration data. The large synthesis_claude example counts 217397; its measured one-message probe is 186733. The same CLI reports contextWindow=1000000 and maxOutputTokens=64000 for this model. After reporting this measurement to the user, the local installation uses a separate Claude input budget of 240000 (remaining counted space 22603); ChatGPT and the default remain 180000. This prevents the old shared ceiling from incorrectly treating unlike tokenizers as equal. The estimate, actual limit and remaining space are shown per stage. Increasing a provider limit above the default requires runtime-bound calibration; a changed runtime blocks before POST. No unmeasured increase or global limit raise is applied.

Example configuration remains portable and uncalibrated. Local calibration fingerprints/settings are installation-specific and must not be copied blindly to another machine. CLI/model/system changes cause preflight rejection until calibration is renewed. Remote tokenizer changes without a local fingerprint change remain a limitation: these measurements are observations, not a permanent provider contract.

## Strategic limits and next work

Semantic near-duplicates, copied sources behind different URLs, freshness of source publication dates, fabricated citations, numerical/unit conflicts and source entailment cannot be reliably decided from string equality. Preserve and flag them for model/human review; do not build automatic destructive filters for them. A future canonical-source graph needs fetched evidence and explicit provenance, not aggressive URL normalization. Semantic checks should produce additional assessments, never overwrite original claims. No extra LLM review round, summary, truncation, alternate transport or multi-pass decision is introduced by this change.

All guards run again at actual submission. Forecasts after round two remain estimates because reports not yet written have unknown length. A finite rule catalog cannot guarantee that every possible failure has been anticipated.

## One evidence standard, separate provider accounting

An input consists of task instructions (including the stage's claim-ID namespace) plus a common evidence file. Models in the same round must receive byte-identical evidence. `evidence_body` extracts the actual data bytes from the rendered/saved prompt; it never substitutes a current reconstruction for a historical sent input. `/packet` exposes its SHA-256, UTF-8 byte count and format; `/evidence` downloads those exact bytes. The archive stores a single shared file per round/hash. UI shows this common identity separately from provider token/capacity numbers. ECA-018 compares peer identities at preview and launch. Provider budgets never authorize dropping, reordering or summarizing evidence.

Historical verification: 4ab4eb02 synthesis inputs contain identical 511563-byte JSON evidence, SHA-256 f3ec7badec1ef9f2da5d5d807647d4593ad1524ec154026618fc5237fd87fcbb; 6ea006dc synthesis inputs share 294481-byte JSON evidence. New Markdown representations are also byte-identical across same-round models. JSON/Markdown transport presentation can evolve between versions; historical sent inputs remain pinned.
