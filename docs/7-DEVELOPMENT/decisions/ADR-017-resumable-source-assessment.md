# ADR-017: Resume source assessment without accepting unverified evidence

Date: 2026-09-25

## Problem

Account re-research produced durable, complete responses but stopped before checking sources: one response had 25 URLs against a 24-URL ceiling, and another attached 11 passages to one finding against an eight-passage ceiling. Further inspection found short version/status quotations, inaccessible pages and quotations absent from retrieved text. Retrying the model would repeat already completed work and could change the evidence.

## Decision

Treat source volume as queued work. Process all supplied source/quote pairs in batches of 24 with a checkpoint and a user-control check before each fetch. Deduplicate identical pairs for verification, preserving every occurrence in the original findings. Keep the existing page byte limit, network deadline, DNS pinning and private-address restrictions. Bound structured map responses to 2 MiB and keep the 100-finding contract. Never clip an oversized response.

Record source outcomes as matched passage, unmatched passage, insufficient passage, or unavailable source. A short version or status label remains in the record but cannot establish meaningful support. A finding with any unresolved passage, and its linked prior assessments, become `unverified` in the working view. Preserve the provider's original `model_status`, statement, quotation, conditions, counter-evidence, limitations and immutable raw response. Unavailability is not evidence that a claim is false, and uncertainty alone is not a disagreement.

Security violations, snapshot corruption, changed requests, changed receipts and missing coverage remain blocking errors. Negative source outcomes do not abort unrelated research. Receipt hashes and snapshot hashes are checked when reusing completed checks. Previously completed model subrequests are reused byte-for-byte; the source-assessment policy is recorded separately from the immutable evidence partition plan.

The reconciliation request explicitly preserves `unverified` status. Its deterministic appendix retains all findings and receipts, and its report includes a source-verification warning when any passage is unresolved. Counts distinguish matched and unverified passages; they do not claim factual truth or semantic completeness.

## Validation

Regression tests cover source counts beyond both old ceilings, exact original-field preservation, short quotations, mismatches, unavailable pages, private targets, corrupted snapshots/receipts, continuation without repeated model calls, pause checkpoints, conservative claim status and a final report that retains unresolved evidence. The previously blocked responses can now be parsed and assessed without changing either saved map request or model response.

## Tradeoffs

Conservative downgrade can mark an otherwise supported multi-source finding unverified when only one passage fails. The original model assessment remains visible for review. Negative checks are frozen for that execution; later re-verification should be an explicit new assessment, not a silent rewrite of accepted history. Reconciliation is still subject to its measured context budget and must stop rather than truncate if it does not fit.
