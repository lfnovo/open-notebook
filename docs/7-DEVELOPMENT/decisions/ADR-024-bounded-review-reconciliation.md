# ADR-024: Reconcile large research results through bounded, durable batches

Status: Accepted

## Problem

Partitioning the research input does not bound its output. Hundreds of working
findings and source-passage receipts can exceed the reconciliation input budget
after every research part has completed. Repeating the research calls cannot
resolve this. Removing findings or raising an unmeasured model limit would put
evidence integrity at risk.

## Decision

Keep the existing single-request reconciliation when it fits or has already been
submitted. Otherwise partition complete working findings into measured batches,
with every referenced source receipt, unchanged part context, the complete shared
brief, all linked full prior-claim records and the global claim statement catalog.
Mark this scope explicitly and bind it to the complete prior register hash. Parent
reconciliations receive the complete prior register, including unlinked records;
the original register is never modified. Validate exact ordered finding equality,
part metadata, receipt equality and coverage before admitting any batch. Do not
split a finding, remove a field, or truncate a source passage. Each actual request
must fit the existing model policy; batch planning retains ten percent headroom.

Pin the payload, protocol and batch request hashes separately from the original
frozen research plan. Reuse the existing durable request journal and uncertain
submission rules. Never regenerate completed research parts to enable the new
reconciliation path. Provider receipts and source verification remain unchanged.

Reconcile batch reports through a bounded tree. Each parent receives the shared
brief, complete prior register, child narratives and a deterministic index of
finding identities, accepted statuses, prior-claim links and unresolved provenance.
Check the exact child finding lineage and part identities at every node. Reject
invented source URLs. Retain every intermediate report alongside the complete
original working evidence and deterministic claim ledger. Bound planning to 64
batches and four parent levels; stop without data removal if an indivisible item
does not fit or the tree cannot shrink.

## Limits

The final narrative sees child reconciliations, not every raw finding at once.
Its coverage list is lineage bookkeeping, not proof of direct original inspection
or semantic completeness. Cross-batch interactions can be missed or misinterpreted.
Prompts require unresolved dependencies and verification limits to remain explicit,
and a program-owned bilingual notice exposes this limitation even if the model
omits it. Unverified observations remain unverified in the retained working data
and claim ledger. Narrative correctness still requires substantive review.

This adds model calls and can increase latency. It does not relax context budgets,
alter source safety checks, claim lossless model summarization, or silently fall
back to a partial report when a batch or parent fails validation.

## Rich reconciliation annotations

Some providers return `reviewed_findings` as records with an explicit `id`,
justification and receipt annotations instead of plain identity strings. The
hierarchical runner may project those explicit identities through the unchanged
exact coverage check. It never infers missing identities from prose or fills them
from the input. Mixed forms, missing/duplicate/unknown identities and missing parts
still fail. The default merge parser remains strict.

The complete records and original response hash are appended as model annotations,
not source receipts or changes to the input's verification statuses. Unknown receipt
identities and conflicts with recorded verification are explicitly listed as
unresolved; they are never guessed, repaired or accepted as matching sources. A
program-owned bilingual notice states that these opinions cannot promote an
unverified finding. Narrative text and every annotation field remain unchanged,
and the original provider response stays immutable in the request journal. This
compatibility path requires no replacement model call or frozen prompt change.

## Restoring a documented omitted citation selector

A provider can omit the `fields` query from a supplied Semantic Scholar DOI
detail URL. The [official API tutorial](https://webflow.semanticscholar.org/product/api/tutorial)
documents this parameter as response field selection. For this exact HTTPS
endpoint only, a missing query can be restored from one unique full URL present
in the actual dispatched input, the allowed evidence and its source receipts. A
variant seen only by another batch is not a restoration candidate. The DOI, scheme, host and path
must be identical. Changed queries, fragments, unknown endpoints, identity or
authentication parameters and multiple possible variants still block. Other
unprovided URLs still fail the exact citation gate; no generic URL normalization
or new source admission is introduced.

Only the derived report's URL spans change. Raw provider responses, frozen
requests, findings and receipts remain immutable. A bilingual rendering notice
and byte-offset audit preserve response/report hashes, original URL hashes,
restored full URLs and receipt identities. This restores an existing citation;
it does not verify the source or promote a finding's status. Completed requests
are replayed locally without replacement model calls.

## Reversible table transport for metadata-bound parents

A root can fail to converge even after child narratives shrink: its complete
prior register and per-finding relationship index still repeat field names in
hundreds of objects. Before reporting that capacity failure, a parent may use
`lossless-json-tables-v1`. Lists of equally shaped records become explicit column
names and ordered rows; other values are unchanged. Reserved marker keys in
source objects are escaped. The program reconstructs the entire original JSON
and compares its canonical serialization byte for byte before measuring or
submitting any request. No record, repeated value, condition or narrative is
removed. Prompts explain the table representation and its untrusted-data scope.

Use the existing input limits and ten percent headroom. If columnar transport
also fails to fit or converge, stop normally. Keep all existing research,
reconciliation requests, results and plans immutable. Pin each fallback level's
protocol, encoded request hashes and decoded payload hashes separately under
`reconciliation_encodings`; use distinct `reconcile-tree-table-L-N` request keys.
Resumption must reproduce that encoding plan exactly. The final retained
appendix includes its manifest. This saves serialization overhead, not model
reasoning: byte reconstruction does not guarantee semantic interpretation.

## Output continuation and bounded artifact regeneration

Claude reconciliation must use verbose stream JSON, with tools still disabled,
so the bridge retains assistant artifact segments across output-token boundaries.
The same strict continuation/session/result checks used by re-research also apply
to merging. A saved fragment is first recovered through its read-only receipt;
raw receipts remain immutable.

Older JSON-only captures may contain just the final fragment, with no recoverable
prefix. A completed Claude reconciliation response that fails JSON syntax parsing
may then have exactly one separately journaled regeneration from the identical
complete frozen input. It uses an `-artifact-retry-1` key. The old response is not
replaced; the derived report and audit explicitly distinguish regeneration from
reconstruction of missing bytes. No repeated web research is needed. An invalid
replacement stops, and resumption reuses it rather than generating another.
Uncertain requests, duplicate JSON keys, missing coverage and invented sources
do not bypass their existing checks or become automatic regeneration triggers.

## Validation

Regression tests reject omitted or duplicate findings, altered source receipts,
changed statuses, lost negation/conditions, changed part dependencies and prior
registers, and invented citations. Tests cover within-part batching, indivisible
records, bounded depth/convergence, preserved intermediate outputs and idempotent
recovery after interruption. Live planning is validated offline against the saved
research results before deployment; no test calls the model provider.

### Ellipsis-only citation examples

A completed reconciliation discussed a malformed citation using the literal
`https://…` example. The URL extractor treated that hostless placeholder as an
invented external source. Ellipsis-only HTTP(S) examples are now excluded from
citation extraction; any actual host, including a URL with an ellipsis in its
path, remains subject to the same source admission checks. Original response
text and saved request receipts remain unchanged.

### Explicit finding identity field compatibility

One complete parent response returned all 77 expected finding records using
`finding_id` instead of `id`. The annotation adapter now accepts those two
explicit field names through the same exact identity and coverage validator.
Conflicting fields, invalid values, duplicates, missing identities and guessed
aliases still fail. Original records are unchanged; the retained annotation
appendix records which field supplied each identity. Annotation statuses and
`reviewed_by` text remain model opinions and cannot become source verification.
Existing responses using `id` retain their previous rendering byte-for-byte.

## Reversible text and string dictionary fallback

A later parent can still exceed capacity after ordinary column tables: child
reports contain canonical JSON annotation blocks inside strings, and registers
repeat long literal status, source and qualification values. Before stopping,
`lossless-json-text-tables-v1` may expose canonical, single-line JSON code blocks
as ordered text/JSON fragments, apply column tables, and reference repeated
literal strings through a shared dictionary. Every narrative character, JSON
field, repeated occurrence, condition, source URL and status reconstructs to the
identical canonical original payload. Noncanonical, ambiguous or invalid JSON
blocks remain literal text; duplicate keys are never repaired. Source objects
and strings that collide with transport markers are explicitly escaped.

Reconstruct and compare the entire canonical payload byte for byte before
measuring any candidate. Validate dictionary references, fragment shapes,
versions and the decoded payload hash. Prompts explain each layer, literal
escaping and the distinction between repeated text and independent evidence.
This is a serialization optimization, not evidence removal, model summarization
or a semantic correctness guarantee.

Existing submitted requests and old encoding plans retain their exact bytes.
Only an unsubmitted parent may choose the additional fallback after legacy and
ordinary table representations cannot converge. Pin the new version, protocol,
request and decoded hashes, using distinct `reconcile-tree-text-L-N` job keys.
Keep the same provider budget, ten percent admission headroom, batch limit and
four-level ceiling. If the new representation still cannot converge, stop.
Missing coverage, invented sources and unverified evidence keep existing gates.

Validation includes exact reconstruction of complete narratives and annotations,
Unicode, negations, numeric/null/boolean values, reserved markers and arbitrary
literal code blocks; tampered dictionaries/hashes, invalid references and
malformed fragments fail. Resume reuses identical jobs and rejects changed plans.
A read-only replay of the blocked Claude parent reused all 47 completed calls;
its two child reports, 304 finding identities and 74 complete prior claims fit
at 98,144/120,000 admission tokens, compared with 125,538 before the new transport.
No model call was made by that validation.

### Citation inspection across retained JSON and source redirects

Completed narratives can contain preserved reports as JSON strings. Scanning the
serialized bytes joined URL text with escaped line breaks and list markers,
creating nonexistent addresses such as `https://example.org/source\n-`.
Citation extraction now decodes complete JSON and valid, explicitly labelled
JSON/evidence-ledger fences before scanning their string keys and values.
Nested reports, duplicate object keys and trailing text remain visible. Invalid
containers retain literal scanning; escapes outside JSON and percent-encoded
URL bytes are not rewritten. The stored reports and provider responses never
change. This is transport decoding, not permission to invent or normalize URLs.

The final source gate also recognizes exact redirect destinations recorded by
the independent source reader. Only a receipt linked to an actual finding can
supply one; unavailable or unrelated receipts cannot. Reuse validates the
receipt's final URL against its retained snapshot in addition to body/text
hashes. A source redirect never promotes an unmatched quotation or unverified
claim. Other invented addresses and receipt tampering still stop execution.

Regression tests cover escaped newlines, slashes, Unicode, nested reports,
duplicate keys, Markdown boundaries, malformed containers, invented URLs,
matched/unmatched redirects and changed receipts. A read-only replay recovered
the complete Claude review from all 48 existing completed requests, with no new
provider call or source fetch and no changes to frozen requests or raw outputs.
