# ADR-027: Bounded passage writes and complete document publication

- **Status**: Accepted
- **Date**: 2026-09
- **Related**: ADR-012

## Context

Replacing thousands of passages in one transaction can produce a WAL batch larger than the database's memory limit. A recovered 3,386-passage document produced a 4.45 GB batch. Breaking that transaction apart without a publication gate would allow search to return an incomplete document as current evidence.

## Decision

Stage deterministic passage IDs in idempotent inserts of at most 16 records and 256 KiB of serialized payload. Validate each persisted batch and the complete document count before committing its existing `hs_document` marker. Search requires both the live original hash and the matching committed marker, fetching markers only for bounded retrieval candidates. Delete obsolete passages in groups of at most 16, only after publication. Persist pending cleanup so interrupted maintenance resumes without regenerating complete embeddings. Never modify the source or note itself.

## Alternatives considered

- Increasing database memory alone does not bound a transaction or prevent recurrence.
- Deleting the previous version first loses the last complete index during failure.
- Publishing every batch exposes incomplete evidence.

## Consequences

More database round trips and temporarily overlapping versions are deliberate. An interrupted replacement stays unavailable until complete and reports index updating. This bounds write input, not total database memory: indexes, reads and background work still require resource limits. The isolated SurrealDB 2.6 test covers 3,386 passages, partial-write interruption, replay, publication gating and bounded deletion with the production memory configuration; 512 MiB is insufficient for that full experiment. Original records and existing completed markers remain compatible. The index remains a single maintenance writer per application; multi-instance indexing would need a separate durable writer lease.
