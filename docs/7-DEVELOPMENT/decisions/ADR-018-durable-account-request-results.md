# ADR-018: Preserve account request results across transport failures

Status: Accepted

## Problem

The CLI bridge classified arbitrary transcript words as authentication or quota
failures. It also retained an early Codex stream error after a later successful
turn completion. Re-research converted every otherwise unclassified error into
an uncertain submission, even when the CLI had definitively stopped. Lost HTTP
responses could strand completed model work because only a process tombstone
was stored.

## Decision

Classify structured terminal error fields, never research prose or tool bodies.
A successful terminal Codex event clears recoverable earlier stream errors;
a terminal failure or truncated response remains a failure.

Persist each request's identity and complete result before responding over HTTP.
Receipts bind the canonical request body and response with SHA-256 and use
atomic, flushed writes. Request directories are private (0700); receipts and
CLI transcripts are private (0600), local, and excluded from public logs and
version control. Retained transcripts are diagnostics, not accepted reports.

An authenticated read-only endpoint recovers a result by request ID. The caller
verifies its frozen input and result hashes before accepting it. Replaying the
same completed request returns the saved result without another model call.
Changed inputs, unfinished requests, missing receipts, and corrupt receipts
cannot trigger an implicit duplicate. A confirmed failure records settlement
and the real error; existing bounded retry policy applies only where eligible.
Completed parts, frozen partition plans, and previous request identities remain
preserved when a rejected part is retried.

## Limits

Old `finished` process tombstones do not contain recoverable responses. They
cannot retroactively prove response content or source quality. Recovery of these
legacy jobs requires confirming settlement and an explicitly authorized retry.
An OS crash between provider completion and local persistence can still leave
an unknown outcome; missing evidence must never be reported as success.
Disk access by the owning OS user is trusted. Hashes detect accidental changes;
they do not protect against an attacker who can rewrite both files and hashes.

## Validation

Regression tests reproduce false transcript-based authentication/quota errors,
recovered Codex stream failures, lost HTTP responses, changed request bodies,
corrupt results, preserved private transcripts, and read-only recovery. Existing
research integrity, source verification, cancellation, and retry tests remain
required. No provider quota is used by these tests.
