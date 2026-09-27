# ADR-019: Keep research passage scope explicit

Status: Accepted

## Problem

A saved re-research response contained 41 findings. One quoted an identifier
without its inline Markdown backticks. Another quoted a real statement from the
supplied shared claim catalog instead of its current evidence part. An exact
substring check rejected the whole response, even though all original model
output remained available.

## Decision

Preserve raw responses and every finding's statement, quoted words, conditions,
counter-evidence, limitations and source pairs. Resolve only two bounded cases:

- Single inline backticks around a literal identifier may be presentation.
  Record the exact original passage and UTF-8 offsets. Never rewrite words,
  punctuation, whitespace, operators or code fences to force a match.
- A verbatim quotation from an explicitly linked, supplied claim is retained
  with `claim_catalog` scope. It is **not** evidence from the current part and
  cannot count toward that part's coverage. Downgrade the finding and its prior
  assessments to unverified, preserving original model statuses separately.

At least one finding must anchor to the actual part. Invented quotes, unrelated
claim IDs, invalid statuses, missing source data and wholly out-of-part responses
still fail. Validator-generated provenance overrides model-provided metadata;
original payloads remain immutable in the journal and bridge receipt.

The reconciler receives the scope rule and the final report includes a
deterministic scope warning and preserved working-record appendix. Repeated
verification downgrades cannot overwrite the provider's initial assessment.

## Recovery during deployment

A research-service restart can resume read-only observation of a still-running
bridge request. Keep its request ID as the cancellation target, validate each
receipt's input hash, and await its durable result. Never restart the provider
call. Missing or corrupt receipts remain blocked. Cancellation interrupts the
observer normally; the existing scoped stop path controls the provider process.

## Validation

Tests cover exact byte anchors, Unicode, lost backticks, altered negation and
operators, code fences, linked and unlinked catalog quotations, wholly out-of-part
responses, forged provenance, repeated downgrades, pending receipt observation,
unknown outcomes and preservation of the cancellation target on resume.

This validates provenance and byte preservation, not semantic completeness or
the factual truth of generated findings.
