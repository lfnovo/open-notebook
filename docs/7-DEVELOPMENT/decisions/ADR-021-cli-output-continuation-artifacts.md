# ADR-021: Recover JSON artifacts across explicit CLI output continuations

Date: 2026-09-25
Status: Accepted

## Context

Claude's account CLI can reach an output-token boundary, retain its partial
assistant message, inject a synthetic continuation request, and finish the
artifact in another assistant message. The final successful `result` can contain
only the last fragment. Treating that fragment as the complete research response
loses the earlier recorded bytes and fails JSON validation.

## Decision

For structured re-research, reconstruct only an explicit CLI continuation chain.
Require the known synthetic output-limit continuation message, the same session,
a successful end-turn result and an exact match between that result and the final
assistant text fragment. Tool exchanges and ordinary user messages break the
chain. Unrecognized boundaries, conflicting event identities and output beyond
the bounded size/count limits do not qualify.

Concatenate recorded assistant text without inserting separators or editing any
character. Do not include thinking, tool results, system text or progress notes.
The joined artifact must be one valid JSON object, with duplicate keys and
non-finite constants rejected. Independent research-contract and source checks
still apply afterward; JSON validity alone is not evidence verification.

For old completed receipts, authenticated read-only recovery exposes the derived
artifact alongside the original result. It does not overwrite that result. The
research journal retains the original response/hash and stores the recovered
artifact separately, bound to the original tail, request/result identity and
capture hash. Subsequent observation reuses this saved artifact and never repeats
the paid research request.

New private CLI captures have a payload checksum. Legacy captures did not have
one: their provenance explicitly says the checksum was established at recovery,
not at original capture. Recovery still requires an exact match to the saved
result and request identity. Do not imply retroactive cryptographic attestation.

## Validation

Tests cover exact byte concatenation, exclusion of reasoning, unknown or ordinary
user continuations, intervening tools, session changes, unsuccessful or incomplete
termination, changed result tails, duplicate keys, conflicting UUIDs, size limits,
capture tampering and receipt immutability. Research tests verify artifact/result
hashes, retained provenance, cached reuse and absence of a repeated model call.
