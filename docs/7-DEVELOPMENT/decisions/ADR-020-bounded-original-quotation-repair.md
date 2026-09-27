# ADR-020: Preserve incomplete quotations with explicit, unverified source anchors

Date: 2026-09-25
Status: Accepted

## Context

A saved re-research response can omit source Markdown or a word inside an
`original_quote`. Literal matching correctly detects this. Repeating the entire
research request would spend quota and replace a completed response without
addressing the fault. Silently normalizing missing words could erase a condition
or negation and would misrepresent the source.

## Decision

Keep the complete provider response immutable. After checking the remaining
record schema, allow one separate, tool-free provenance request per evidence
part. It proposes exact source passages for the mismatched finding indexes; it
cannot return rewritten findings or statuses. A durable job key and the existing
request/result hashes preserve the repair through interrupted observation.

The validator requires the original response and part hashes, exactly one anchor
per affected finding, a unique literal source match, and bounded quote length.
Word/punctuation comparison permits only limited insertions into the model
quotation, never substitution or reordering. Added URLs, ambiguous matches,
unknown fields, altered hashes, missing findings and excessive additions fail
closed. Byte offsets are computed locally from the unchanged UTF-8 source.

Accepted anchors retain the model quotation, the exact source passage, source
offsets, inserted tokens and hashes separately. Both the finding and each linked
prior assessment remain **unverified**, with the original model opinion retained.
A repaired quotation never establishes part coverage. In particular, an omitted
negation is exposed as an insertion; it is not treated as a harmless formatting
change. At least one independently matching original quotation is still required
per part. Existing claim-catalog scope rules remain in force.

When the provider supplies an empty public-source list, the runner retains that
record as an explicitly unsourced, unverified observation. It does not infer that
the observation is correct or describes only local evidence, and cannot invent a
URL. Neither that finding nor its prior assessments establish verified research
or part coverage. Missing/malformed source structures still fail. A part containing
only unsourced, shared-context or repaired-quote observations cannot pass coverage.

Reconciliation receives these limits explicitly. The final Markdown includes a
deterministic warning and all working records, even if the model omits a warning.
A failed repair stops the stage and preserves both responses; there is no repair
loop and no automatic repetition of the original research.

## Consequences and validation

This recovers useful research without certifying an incomplete quotation or
claiming semantic equivalence. It adds at most one successful provenance request
per affected part; confirmed transport failures still follow the existing bounded
request policy, while uncertain submissions require receipt recovery.

Regression tests cover field preservation, UTF-8 offsets, lost negation, Markdown
omissions, unverified prior assessments, coverage exclusion, input hash tampering,
ambiguous/substituted/excessive passages, added URLs, missing/duplicate anchors,
invalid schema and a single bounded repair attempt. Existing durable-job tests
cover cached response reuse and input/output tampering after interruption.
