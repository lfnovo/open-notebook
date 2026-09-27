# Evidence preparation

The preparation gate compares the **next serialized input** with the receiving model's admission budget. Comparing a report's output length with its own earlier input length is not sufficient: subsequent inputs combine multiple reports, metadata and instructions.

## Processing order

1. Preserve archived reports and already submitted input hashes. Build the current canonical Markdown evidence from its declared predecessors.
2. Count complete transport input, including system/task instructions, with the configured provider margin. Same-round peers share evidence; provider tokenizer estimates can differ.
3. If needed, encode profitable exact repeated lines through an in-band dictionary. Preserve their original positions and attribution. Reject any representation that fails exact reconstruction, changes a unique sentence, or increases the measured size.
4. If an account stage still exceeds its budget, plan ordered source parts against every peer's budget. Each part includes byte offsets, source and part hashes. The normal target is at most 55% of each peer's admitted input, leaving room for findings and consolidation.
5. Process every part, then consolidate findings with the unchanged protected evidence register and source inventory. Intermediate reports use a strict JSON coverage envelope; the user receives the final Markdown report. New research runs also request concise working reports with explicit subjects, conditions and disagreements.
6. Validate every actual subrequest before dispatch. Stop on invalid coverage, changed hashes, an invented source URL, insufficient protected-register capacity, missing progress, or the bounded execution limit. No final answer is silently truncated to fit.

Source coverage and semantic completeness are different. The system verifies byte coverage, declared part coverage, source URL membership, the unchanged protected register in consolidation inputs, and request identity. A model can still omit an unstructured qualification or misinterpret a claim. These checks cannot prove that an LLM retained all meaning. The final human-facing answer is never passed through a sentence-removal filter.

## Decision on splitting instead of deleting

Prefer intact source partitions over deleting unique evidence to satisfy a budget. Do not hard-code two parts: measure the complete requests for every peer. Uploading two files into one model context does not reduce their combined token cost; separate processing and a consolidation step are required.

Residual risks include a condition separated from its exception, a cross-part contradiction missed during consolidation, a returned coverage list that overstates what the model understood, and a cited source that does not actually support the generated claim. Line-boundary preferences and a pinned claim register reduce some risks but do not solve unregistered semantic dependencies. No detector can guarantee discovery of every unknown dependency. A URL membership check is provenance validation, not fact verification. For high-consequence conclusions, review the relevant original passages and sources before relying on the generated answer.

Splitting is not anonymization. Account calls retain the existing provider destinations; the local journal contains plaintext research inputs and outputs with private file permissions, not a new encryption guarantee. Exports and backups require the same care as original documents. Imported material remains untrusted reference data. More calls add quota use and additional interruption points, which the bounded execution and checkpoint rules address.

## Configuration and compatibility

The research service accepts `context_compaction` (default `true`), `compaction_headroom` (default `0.05`) and `segmented_synthesis` (default `true`). Setting `segmented_synthesis` to `false` retains the context-limit/manual-import behavior. Changes do not rewrite already dispatched historical inputs. Browser research retains its existing Deep Research transport; segmentation applies only to account stages.

Fresh preliminary web research is excluded from source-only segmented synthesis: discovering new sources is a different operation. Its original input still passes admission checks. Preliminary brief consolidation and later account syntheses can use segmentation. Legacy JSON inputs keep their format and are not silently converted into segmented requests.

Admission estimates continue to use the existing per-provider limits and runtime bindings. The calibration helper admits only identified single-context serialized-input observations with known runtime and profile, no tool loop and one attempt. It rejects mixed runtimes and unknown aggregates. It does not automatically lower live margins, and fitting recorded points does not establish accuracy for unseen input distributions.

## Checkpoint and control behavior

- A private `segmented-journal.json` stores the original-input identity, immutable plan, part inputs, responses, hashes, budgets and usage. The all-files export includes this journal; it can contain the same private research evidence as the reports.
- A completed subrequest is validated and reused. Pausing after active work preserves the existing whole-stage behavior. Stopping now uses the active child request ID and the existing provider cancellation path.
- A connection loss or process interruption with an in-flight request is `submission_uncertain`. It is not sent again automatically. After confirmed provider cancellation, explicit resume can restart only that cancelled part.
- At most 64 distinct subrequests and four consolidation passes are allowed. Planning reserves at least one final call. A failed intermediate response remains available for inspection; changing the plan to conceal failure is not allowed.
- Same-round peers receive the same ordered original source parts. Their generated findings may differ by design. Source hashes, plan identity and additional call counts are shown in the preparation panel; final consolidation is not mislabelled as a copy of the original evidence.

## Validation

The regression suite covers unique conditions, prohibitions, uncertainty, CRLF, code and tables, reference corruption, exact source coverage, reordered/missing parts, shared peer inputs, protected-register forwarding, invented URLs, checkpoint reuse, confirmed cancellation, unknown outcomes and bounded calls. Fault-injection checks deliberately remove several guards to confirm that the corresponding tests fail.

A small provider comparison is a separate quality probe, not proof of universal preservation. Local validation found matching protected facts in two ChatGPT fixture outputs; Claude refused a referenced fixture, so its paired comparison remained incomplete. The complete large research was planned and measured without restarting it. Production use remains subject to provider refusal, available quota and the semantic limitations described above.
