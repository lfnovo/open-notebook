# ADR-023: Preserve declined quotation repairs as unresolved observations

Status: Accepted

## Problem

The quotation repair contract explicitly permits an empty `anchors` array when
the provider cannot find an admissible exact passage. The working-record parser
treated this valid negative result as malformed output, stopping an entire part
even when its other findings had valid original anchors. Repeating the saved
repair could not resolve the stop, while replacing a changed quotation with a
guessed passage would misrepresent its provenance.

## Decision

The review runner explicitly enables preservation of a hash-bound negative
repair result. The strict default parser still rejects it. Two outcomes qualify:
an entirely empty array, or a complete mapping to bounded, unique verbatim source
passages whose relationship to the model quote fails the insertion-only rule.
The latter is a rejected association, never an accepted anchor or a claim of
semantic equivalence. Partial repairs, wrong hashes, invented fields or passages,
new source URLs, malformed records and invalid identities remain blocking errors.

Preserved observations retain their original statements, quotations, conditions,
counter-evidence, limitations, sources and model opinions. The validator assigns
`original_anchor.scope=unresolved_part_quote`, with the original quotation,
evidence-part and repair-response hashes. It does not invent passage text or
byte offsets. The finding and every linked prior assessment become `unverified`;
a subsequent public-source passage match cannot promote them. They cannot count
toward part coverage. A part with no independently anchored research finding
still stops.

Reconciliation receives an explicit instruction that these observations are not
support, rejection or decision evidence. A deterministic warning and the complete
working-record appendix preserve this limitation in the final artifact even if
the model omits it. The claim ledger also describes the unresolved provenance.

## Compatibility and limits

Frozen inputs, partition plans, map prompts, original responses and the one-shot
repair request remain unchanged. Recovery reuses the durable negative result;
it does not issue another model call. This is retention of an unresolved
observation, not successful repair or verification. Programmatic provenance and
coverage checks cannot guarantee the semantic correctness of narrative synthesis.

## Validation

Regression tests cover preservation, negative-result opt-in, exact hash binding,
malformed and partial repair rejection, invented metadata and identity rejection,
coverage failure, one bounded repair call, ledger warnings, and protection against
promotion by independently matched public-source passages.
