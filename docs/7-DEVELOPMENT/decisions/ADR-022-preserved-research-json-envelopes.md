# ADR-022: Preserve provider prose surrounding a structured research artifact

Date: 2026-09-25
Status: Accepted

## Context

A provider may precede an otherwise valid JSON research artifact with a progress
sentence, or add a caveat after its closing fence. Rejecting the entire saved
response can unnecessarily block a long-running research job. Dropping surrounding
text silently could discard a meaningful qualification.

## Decision

The working-record parser accepts exactly one explicitly fenced JSON object when
strict whole-response parsing fails. It retains every character outside the fence
as a separate, program-owned `provider_envelope`, with response/body hashes and
UTF-8 body offsets. The immutable raw response remains in the journal. No new model
call is required to extract an unambiguous recorded artifact.

Multiple artifacts, additional unfinished fences, invalid JSON, duplicate keys,
non-finite values and non-object payloads remain errors. Field, quotation, source,
identity and coverage checks apply unchanged to the extracted object. Provider
claims cannot forge envelope provenance.

The envelope is untrusted provider prose, not verified evidence or instructions.
Reconciliation receives it with that qualification. The deterministic final
appendix preserves it even if a model omits it. A schema repair cannot erase the
original envelope or add new surrounding prose. This policy applies to structured
working records; it does not use an arbitrary JSON-looking fragment to rewrite a
final human report.

## Validation

Tests exercise prefix/suffix preservation, exact multibyte offsets, malformed or
ambiguous fences, duplicate keys, forged metadata and unchanged ordinary JSON.
Pipeline tests verify preservation through source checks, schema repair,
reconciliation, final export and cached retries without repeated provider calls.
