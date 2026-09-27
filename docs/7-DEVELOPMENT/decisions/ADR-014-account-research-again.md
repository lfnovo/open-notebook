# ADR-014: Account-based, partitioned re-research

- **Status**: Accepted
- **Date**: 2026-09
- **Related**: [ADR-013](ADR-013-evidence-preparation.md)

## Context

Large accumulated reports can exceed the Research again input window. Deleting prose
can remove qualifications; using two uploads within one model context does not enlarge
that context. Replacing research with source-only summaries would change the stage's purpose.

## Decision

New runs default to independent account CLI re-research by ChatGPT and Claude. Both use
the same frozen, byte-complete partition plan. Each part searches and reads public sources.
The application matches quoted passages against independently fetched, bounded public-source
snapshots. A tool-free reconciliation compares all findings, original passages and prior
claims. Deterministic appendices retain every accepted finding and prior claim identity.

Requests and responses are journaled. Confirmed results are reused; uncertain submissions
are not repeated automatically. Existing runs retain their original transports and reports.
The setting remains optional. See the [implementation guide](../../../modules/multi-model-research/RESEARCH_AGAIN.md)
for admission bounds, source security, recovery and validation.

## Alternatives considered

- Browser-only research retains provider Deep Research features but not the requested CLI orchestration.
- Sentence deletion and summary-only reduction cannot establish semantic preservation.
- Splitting files into a single conversation does not remove the combined context constraint.

## Consequences

Byte coverage and passage matching are testable; factual truth and complete understanding
are not guaranteed by them. Original evidence remains available. More parts consume more
account quota. Unsupported or inaccessible sources, ambiguous submissions and oversized
reconciliation stop explicitly. CLI research is cloud account processing, not offline
analysis or a claim of equivalence to the provider's Deep Research product.
