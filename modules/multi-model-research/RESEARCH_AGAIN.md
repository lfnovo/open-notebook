# Account-based, partitioned re-research

Implementation guide

## Problem

Research again previously required two browser Deep Research runs. Large accumulated
reports can exceed a provider's context capacity. Deleting sentences or passing only
summaries can remove qualifications and contrary evidence, even when URLs and claim
IDs survive. Uploading two files into the same context does not increase its capacity.

## Decision

New runs default to `account_review: true`. Round 2 uses independent ChatGPT and Claude
account CLI research profiles. Each profile can search and read public pages, with
shell, files, browser UI, MCP integrations and delegation unavailable. Initial browser
research and later source-only synthesis remain distinct. The setting can be disabled
for the original browser/import workflow. Existing stages are never migrated in place.

The application freezes a common evidence body and a deterministic partition plan for
both providers. Every original UTF-8 byte belongs to exactly one ordered part. Paragraphs,
tables and fenced blocks are indivisible; an oversized block stops planning. Each part
receives the original question, scope, date, language, claim catalog and bounded adjacent
paragraph context. A closing Mermaid fence cannot become a new opening fence.

Each part performs fresh research and produces typed working findings with exact
original passages, conditions, counter-evidence, limitations, source quotations and
cross-part dependencies. Observed search/read tool activity is required. The application
independently fetches the cited sources and matches their quotations after whitespace
normalization. Verified receipts include surrounding source text to expose omitted qualifications and negation. Repeated receipts are stored once and referenced by ID. A final tool-free account call reconciles all working findings and the
unaltered prior claim register. Every accepted working finding and prior claim identity
is retained in deterministic appendices, including claims not reassessed by the model.

Source verification uses DNS-pinned HTTP(S) requests without cookies, credentials or
environment proxies. Every redirect is revalidated. Private, loopback, link-local,
multicast and mixed public/private DNS targets are refused. TLS verifies the original
hostname. Snapshots are private files, bounded to 2 MiB per source; HTML and text are
supported. PDF, login-required, JavaScript-only and blocked pages may require another
public text source. They are never silently treated as verified.

Budgets are checked before every call. A part targets 35% of the admission budget,
leaving room for tool responses (an indivisible block may use 50%, with the full request capped at 55%); provider context exhaustion can still occur. Limits
are 32 parts, 100 findings per part, 24 distinct sources per part and 128 per stage.
One tool-free schema repair per part is permitted; it cannot rewrite or remove any existing evidence field, and it is journaled like other calls. At most 65 account calls are admitted for 32 parts. An oversized reconciliation stops without dropping findings. These are work bounds,
not compression targets or claims of complete research.

The durable journal records inputs before dispatch and responses before validation.
Completed calls are reused on resume. Unknown remote outcomes are not automatically
resubmitted. Existing confirmed cancellation, stage controls and run controls apply.
Original evidence, journals and source snapshots are included in the download archive.

## Guarantees and limits

Hashes establish byte identity; exact-ID checks establish structural coverage. Quote
matching establishes that text occurred in the independently fetched page. None proves
that an LLM understood every qualification, that a quotation entails its claim, that a
page is correct, or that all relevant sources were found. Working findings remain
derived material, never described as a lossless semantic substitute for originals.
Prompt injection, changing pages, conflicting definitions and cross-part relationships
remain relevant risks. Deterministic appendices and original passages make those risks
auditable; uncertain and contradictory findings must remain explicit.

Terminal orchestration still sends evidence to the selected cloud account provider.
It is not offline processing. CLI research is not represented as equivalent to the
provider's Deep Research product. More parts use more account quota and take longer.

## Validation

Tests cover exact UTF-8 coverage, fences/tables, missing or fabricated IDs, quotes and
statuses, source request limits, private-address rejection, redirects, snapshot integrity,
actual-tool trace requirements, source mismatch, complete reconciliation, saved-result
reuse, uncertain outcomes, confirmed cancellation, budget refusal, legacy transport
preservation and UI progress. Real-provider probes are recorded separately from unit
tests; a passing structural suite is not a semantic quality certification.
