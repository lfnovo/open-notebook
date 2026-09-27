# Research availability and optional-provider development plan

Updated: 2026-09-24. Scope: continuing research safely when one parallel provider is unavailable.

## Delivered in the first increment

- Explicit per-stage Skip, with a distinct persisted state and user-action audit record.
- Two-step confirmation, risk acknowledgement and prevention of duplicate submissions.
- A minimum of one completed parallel report; no skipping a merge or the final decision.
- Confirmed local stop before skipping an active request; completed reports remain immutable.
- Frozen downstream inputs prevent retroactive changes to provider coverage.
- Later packets record the absent provider. Prompts prohibit invented contributions or consensus.
- Progress separates resolved stages from actual saved reports and labels skipped contributions.
- Quota errors no longer trigger the 1/5/30/90/250-minute retry sequence.
- Terminal Gemini errors are parsed separately from report content; known reset times persist in the account bridge and prevent premature requests.

## Browser recovery hardening (2026-09-24)

- The task composer recognizes an uploaded packet by its exact card title or accessible name, including wrapped filenames. Sidebar and previous-message attachments cannot satisfy readiness.
- Short, finite entrance animations in the composer and Gemini research panel can settle while their task window is covered. Static hidden elements and indefinite activity animations remain unchanged.
- A completed or running research task cannot trigger an old plan's Start button.
- A confirmed conversation renews its two-hour observation window up to a 24-hour cap per monitoring session. Renewal only observes the existing conversation; it never uploads or submits the question again. Unconfirmed conversations still stop for review, and user stop/pause controls remain effective.
- Browser tests cover hidden and wrapped attachments, unrelated sidebar cards, completion beside an old plan, report recovery, a bounded monitor and the absence of any second submission.

## Re-research packet recovery (2026-09-24)

Malformed or nested code fences in a provider report must not absorb later reports into one oversized block. The partitioner now checks each serialized report/attachment boundary against its exact UTF-8 byte length and confines an unfinished fence to that frame. It does not edit the original report, remove fence characters, split genuine oversized code blocks, or increase model budgets. Invalid byte lengths or boundary labels still block submission.

Regression tests reproduce nested and unclosed fences, multibyte text, corrupted framing and an actually oversized code block. Real-packet validation reconstructed all 543,508 evidence bytes from 13 parts and produced an identical plan for both review providers. This establishes byte preservation and budget admission, not semantic completeness of generated findings. Existing completed reports and submitted subrequest journals remain immutable.

Source-count stalls are handled by resumable verification batches, with negative source outcomes preserved as unverified evidence. See [ADR-017](decisions/ADR-017-resumable-source-assessment.md) for the preservation guarantees, blocking integrity checks and regression coverage.

## Account request recovery (2026-09-25)

Terminal provider errors are separated from report text. A recovered Codex stream
error no longer overrides a subsequent successful completion. Private durable
receipts preserve complete responses and failed-call diagnostics before the HTTP
connection closes. Review and segmented synthesis can recover a saved result
without another model call; input and output hashes are checked first. Confirmed
failures retain their reason and settlement status, while unknown outcomes still
block implicit repetition. See [ADR-018](decisions/ADR-018-durable-account-request-results.md).

Original passage validation distinguishes literal identifier formatting from a
quotation taken from the supplied shared claim catalog. Shared-context findings
remain explicitly unverified and never establish current-part coverage; invented
passages still block. See [ADR-019](decisions/ADR-019-explicit-research-passage-scope.md).

Incomplete model quotations now have one explicit provenance-repair opportunity
per part. Exact source anchors supplement the immutable response; affected
findings and prior assessments remain unverified and cannot establish coverage.
Missing words, including negation, are exposed rather than normalized away.
Invalid or ambiguous repairs stop without repeating the research. See
[ADR-020](decisions/ADR-020-bounded-original-quotation-repair.md).

Explicit Claude CLI output-limit continuations can be reconstructed from recorded
assistant text without editing any byte or including reasoning/tool output.
Existing partial receipts remain unchanged; a separately hashed artifact can be
recovered through a read-only request. Source and record checks still apply. See
[ADR-021](decisions/ADR-021-cli-output-continuation-artifacts.md).

A single explicit JSON artifact can also be read when a provider adds surrounding
prose. All such prose remains in a separately hashed provider envelope, is passed
to reconciliation as untrusted context and is preserved in the final appendix.
Ambiguous or invalid artifacts still block. See
[ADR-022](decisions/ADR-022-preserved-research-json-envelopes.md).

## Planned next increments — not implemented

| Priority | Capability | Acceptance criteria |
| --- | --- | --- |
| P1 | Select required and optional providers when creating research | All remain enabled by default. The selected policy is stored with the run; optional never implies automatic omission without an explicitly accepted policy. |
| P1 | Provider availability card | Distinguish CLI/account quota, web Deep Research quota, sign-in, network failure and unknown availability. Display reset time in the user's timezone and label unknown times honestly. |
| P1 | Configurable evidence threshold | Minimum completed providers and mandatory roles are validated before allowing a skip. Warn that a single report provides no independent model cross-check. |
| P2 | Opt-in continuation after quota reset | Schedule at the reported reset, never before it. Recheck availability without resubmitting a completed report. Persist the user's choice through restarts. |
| P2 | Stop-and-skip as one guided action | Show the interruption risk, confirm cancellation, then revalidate the stage and dependencies before skipping. An unconfirmed cancellation must block the skip. |
| P2 | Fork after a skipped contribution | Create a separate research revision for later evidence, leaving the original run and frozen packets unchanged. No silent in-place restoration. |

## Validation gates

Test quota exhaustion with process exit code zero, report text containing misleading quota/auth keywords, restart persistence, expired reset times, unknown reset times, duplicate clicks, stale confirmation snapshots, running-stage races, missing peer evidence, immutable downstream packets and attempted imports into skipped stages. Browser checks must cover narrow screens, keyboard-accessible confirmation, visible missing-provider status and accurate report counts. Tests and previews must never launch a paid research request accidentally.
