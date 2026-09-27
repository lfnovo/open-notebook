# ADR-010: Lossless research packets and explicit input admission budgets

- Status: Accepted
- Date: 2026-09-21
- Scope: multi-model-research and its account-models transport contract

## Problem

A seven-report final packet contains full reports, evidence attachments, provenance,
source attribution and an append-only claim register. Pretty JSON and a second JSON
conversation envelope add tokens. Counting only the exported prompt hides that second
representation. The old displayed estimate also hid a 1.25 multiplier and 4096 overhead.

## Decision

New runs use `markdown-v1`. The canonical structured packet and archival reports remain
unchanged. Full question, scope, report and evidence text appears verbatim inside a
collision-checked data boundary, with an explicit instruction not to execute source
instructions. Metadata keeps unknown dates as null. Exact URL strings are deduplicated
in a bibliography with reporting-stage attribution; inline citations remain untouched.
The claim register uses a reversible index to unambiguous evidence-ledger claims already
included in full, plus explicit overrides for audited source unions. Invalid/missing or
ambiguous ledgers fall back to full records. URL list references use the numbered inventory.
No claims, rejection history, upstream warnings, report words or evidence bytes are removed.

`research-markdown-v1` is an explicit account bridge protocol, accepted only for the
research profile with exactly system/user text and no tools/structured output. It joins
those two messages without JSON escaping. The research service verifies bridge support
before any model request. General account calls retain JSON. Contract tests compare the
actual bridge formatter with the budget representation.

`TokenBudget` counts both packet and serialized CLI input with o200k_base, then applies
an explicit per-provider multiplier and fixed overhead. This is an admission estimate,
not exact provider-tokenizer usage or a guaranteed model context size. The 180000 limit
is unchanged. `/packet` exposes raw, transport, counted, margin, effective raw ceiling
and remaining counted budget. Launches record their budget with the input hash.

The operator's ChatGPT configuration uses 1.15 + 4096, based on three historic calls
whose reported usage / JSON CLI input ratios were 1.076–1.137. This small sample is not a
provider tokenizer attestation. Claude usage ratios (1.714 and 3.814) cannot establish
single-context tokenization; they may include multiple internal calls/cache. Its old
1.25 + 4096 heuristic is retained and explicitly labelled uncalibrated. Unknown providers
also retain the conservative fallback. No automatic lowering based on usage is performed.

After round two, `/context-plan` reports actual synthesis input estimates and a final-stage
projection. Missing round-three reports reserve 32000 raw tokens each (configurable).
Warnings start at 85%; they do not stop the workflow. Projections are not upper bounds:
future text and accumulated claim metadata can grow beyond assumptions. Actual full input
is rechecked immediately before submission. Incomplete projections are never submitted.

## Compatibility and failure behavior

Saved sent inputs remain hash-pinned, including old JSON and CRLF bytes. Completed manual
imports without saved input keep their original format. On recovery, only never-submitted,
unfinished account stages adopt Markdown. Existing browser submissions/journals are not
rewritten. Old manual packet hashes become stale only for those explicitly migrated,
never-submitted stages and receive the existing reload-packet error.

Context overflow remains `context_limit`, with zero model submissions and no automatic
retry. Original exports and manual import remain available. No silent web-transport
fallback, model summarization, output trimming or extra model decision pass is introduced.

## Initial measurement (superseded by ADR-011)

The real 4ab4eb02 final packet becomes 160738 raw packet tokens, 160863 serialized CLI
input tokens, and 189089 counted tokens with the ChatGPT policy. All report/evidence bytes
and the claim register round-trip exactly. This does **not** meet the proposed 180000
ceiling with 5% headroom. Reducing it to approximately 143000 by dropping claim history
would violate the evidence requirement. That historical final stage is already completed
by manual import and is not rerun. A future oversized job still needs an explicit product
choice (manual import, approved alternate transport or approved multi-pass processing).

The later parser correction, six ChatGPT calibration samples and ECA controls are recorded in [ADR-011](ADR-011-research-eca-rules.md). The original large final packet now meets the 5% headroom target without losing report or claim data.
