# ADR-015: Complete research briefs and multiple document inputs

- Status: Accepted
- Date: 2026-09-23

## Problem

The creation form silently limited pasted questions to 12,000 UTF-16 code units
and had no file input. A valid 39,982-character Markdown research program could
not be submitted through that field even though the existing service accepts
12,000 question characters plus 30,000 scope characters.

## Decision

Keep the existing service admission contract. A frontend adapter counts Unicode
code points, validates the full input, and distributes long briefs across the
two existing fields without deleting or rewriting text. It prefers paragraph
boundaries and includes additional criteria after the complete brief. Short
questions keep their original field semantics. Over-limit text remains editable
with an explicit error; no native maxlength silently clips a paste.

The optional research module accepts up to ten local documents, mixed with an
optional typed question. Supported suffixes are MD, Markdown, TXT, CSV, JSON,
YAML, YML, PDF and DOCX. Each extracted passage is labeled with its filename and
the SHA-256 of its original bytes. Failed files and exact duplicate files block
creation until the user removes or replaces them. File selection never starts a
research automatically. Existing idempotency keys remain stable for repeated
submissions of the same prepared body.

Extraction runs in the browser; no independent upload service or restart of an
active research engine is required. The stored research contains the extracted
text and hashes, not the original binary files. The interface states this before
submission. PDF.js uses a bundled local worker; DOCX processing reads bounded XML
parts with fflate and DOMParser. Hyperlink targets, table text, headers, footers,
footnotes and endnotes are retained where supported. No document macros, script
actions or external resources are executed. No user files are sent to a parser
service or CDN.

## Admission and integrity boundaries

- Allowlist plus blocked script/executable/macro extensions, including double extensions.
- Signature checks reject renamed PDFs, archives and executable binaries.
- UTF-8 decoding is strict. Text content, BOM and line endings are preserved.
- PDF/DOCX: 8 MiB per file, 32 MiB total; text: 168 KB; PDF: 250 pages.
- DOCX central-directory checks precede decompression: bounded entry count and
  expanded size, no encrypted entries, traversal paths, duplicates or embedded objects.
- PDF extraction has a deadline and destroys its worker when finished or failed.
  Any page without readable text rejects the extraction, including scanned/blank pages.
- The combined brief, document labels and criteria must fit 42,000 characters;
  separately entered criteria must fit 30,000. These are application admission
  limits, not promises about provider context capacity. Existing token gates remain.
- PDF/DOCX formatting, figures and images are not preserved as semantic input.
  Users must review and acknowledge the extracted text before submission.
  Hashing establishes file identity, not extraction completeness or factual accuracy.

## Verification

Regression tests cover complete long input, Unicode limits, mixed files, file-only
creation, review acknowledgement, blocked extensions, signature mismatch, archive
bounds, exact duplicates, and failed-file admission. Browser checks use actual
Markdown, CSV, searchable PDF and DOCX fixtures. Creation requests in UI checks
are intercepted so test runs cannot consume account quota.
