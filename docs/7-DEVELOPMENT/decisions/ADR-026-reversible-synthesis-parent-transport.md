# ADR-026: Reversible, bounded synthesis parent transport

Status: implemented; deployment requires successful admission of the complete next level.

## Problem

Large synthesis jobs can finish every source part and claim-register batch but still
fail during reconciliation. Repeating the full catalog in every partial request
produces singleton groups and consumes the whole-stage call ceiling. A retry must
not change an already submitted request or disguise missing evidence.

## Decision

Use a versioned, self-contained transport for new parent requests when it is
measurably smaller. Encode repeated strings, ordered JSON objects, and JSON report
blocks with exact formatting information. Decode and compare the complete payload
before admission. Unsupported JSON, duplicate keys, unusual numeric spelling and
non-JSON text stay literal. No model summary replaces a saved child report.

A partial reconciliation receives unchanged catalog rows for explicit child claim
lineage and identifiers mentioned in its reports. Its notice makes that scope
explicit. Source URLs and source inventory remain complete. The final reconciliation
receives the full parent catalog; complete original records continue to be handled
by the existing claim-register batches. Scope partitioning is not a guarantee of
semantic completeness or model comprehension.

Previously submitted first-level reductions retain their exact requests, identities,
receipts and coverage. Recover unknown outcomes through the existing receipt path;
never resend them with the new encoding. Adopt only a contiguous valid prefix.
Pin new level membership and request hashes. Each level must cover every child
exactly once in order. Replays fail closed on changed content or grouping.

Keep the 64-call ceiling, four-level convergence bound, 70% reduction headroom,
95% final admission threshold, calibrated input budgets, source validation and
single-recovery limits. Reserve the entire next level and one final call before
submitting its first request. Invalid completed attempts still count. If a complete
level cannot be admitted, preserve progress and stop; do not silently trim reports,
raise budgets or assume another request will solve the problem.

## Validation and limits

Tests cover exact reconstruction, object order, Unicode, hybrid formatting, literal
marker collisions, repeated records, malformed/tampered packets, legacy completed
and in-flight recovery, deterministic replay, complete grouping and call admission.
A real saved-job replay retained 55 existing jobs and the frozen source plan exactly.
Packing reduced the next level from 51 singleton requests to 19 groups, but still
required at least 75 cumulative calls. It therefore correctly remained blocked by
the unchanged 64-call ceiling. This is a transport and admission improvement, not a
claim that this particular run has completed or that a larger call budget is safe
without an explicit operational decision.
