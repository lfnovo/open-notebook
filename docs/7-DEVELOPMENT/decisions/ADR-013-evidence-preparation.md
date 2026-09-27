# ADR-013: Verified evidence preparation and resumable segmented synthesis

- **Status**: Accepted
- **Date**: 2026-09-22
- **Related**: ADR-010, ADR-011; supersedes the single-request-only overflow behavior in ADR-010

## Context

Full research evidence can exceed a provider's admitted input even after Markdown packaging. Removing unique prose because it lacks a URL, number or claim ID loses conditions and counter-evidence. Keeping deleted prose in a local restoration file does not deliver it to the next model. Retry identity and semantic preservation are separate concerns.

## Decision

Use self-contained, exact reference encoding for profitable repeated lines, with the dictionary inside the transmitted input and byte-for-byte reconstruction enforced before submission. Never delete unique sentences, pronouns, warnings or history to meet a budget. If the complete account input still exceeds its budget, partition the original evidence deterministically against all peers' serialized input estimates. Every byte belongs to exactly one ordered, hashed part. Consolidation receives intermediate findings plus the unchanged protected claim register and source inventory.

Persist each subrequest before dispatch and its response before validation. Resume completed work without repeating it. An uncertain remote outcome requires attention; only confirmed cancellation permits that part to restart. Bound requests and reduction passes, measure every actual request, and stop on integrity or capacity failure. Existing sent single-request inputs remain frozen. UI and exports distinguish exact source coverage from the unprovable claim that generated summaries preserve every meaning.

## Alternatives considered

- Sentence deletion with a restoration sidecar: fails to preserve evidence delivered to the model.
- Lowering token margins to admit the packet: requires comparable, runtime-specific single-context measurements; aggregate usage is insufficient.
- Sending different evidence to each model: breaks the common-evidence contract.
- Unbounded summarization retries: can repeat quota consumption and progressively lose information.

## Consequences

Original reports, source ordering and audit history remain available. Oversized account synthesis can proceed through smaller calls, with additional quota usage disclosed. Generated intermediate findings may omit meaning despite complete byte coverage; this is not advertised as lossless synthesis. Web research keeps its existing transport and manual fallback. See the [module guide](../../../modules/multi-model-research/EVIDENCE-PREPARATION.md) for controls and validation boundaries.
