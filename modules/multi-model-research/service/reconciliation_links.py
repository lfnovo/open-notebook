"""Restore one documented omitted URL selector; never guess source identities."""
import re

from context_preparation import PreparationError, digest
from workflow import citations

URL = re.compile(r'https?://[^\s<>\[\]"`\x00-\x20]+')
PAPER = re.compile(r'https://api\.semanticscholar\.org/graph/v1/paper/DOI:10\.\d{4,9}/[A-Za-z0-9._;()/:+-]+')
FIELDS = re.compile(r'fields=[A-Za-z][A-Za-z0-9.]*(?:,[A-Za-z][A-Za-z0-9.]*)*')
NOTICE = ('\n\nCitation rendering note / Bağlantı gösterimi notu: An omitted API field selector '
          'was restored from its unique, exact supplied source receipt. This is not source verification '
          'and changes no finding status. The original provider response and byte-offset audit are retained. '
          'Eksik alan seçicisi özgün kaynak bağlantısından geri kondu; bu işlem kaynak doğrulaması değildir.\n')


def restore_receipted_fields(report, data, allowed, response, supplied=None):
    """Only Semantic Scholar's documented DOI detail endpoint + fields projection.

    https://webflow.semanticscholar.org/product/api/tutorial documents fields as
    response field selection, not paper identity. Arbitrary query removal, other
    endpoints, changed DOI/scheme/host, fragments and ambiguous variants fail.
    Even this narrow recovery substitutes the original full URL, never admits the
    shortened URL as a new source or changes an existing receipt's verification.
    """
    extra = set(citations(report)) - allowed
    if not extra:
        return report, None
    supplied = allowed if supplied is None else supplied
    replacements = {}
    for url in sorted(extra):
        candidates = {}
        if PAPER.fullmatch(url):
            for rid, receipt in data['source_receipts'].items():
                full = receipt.get('url', '')
                if (full in allowed and full in supplied and full.startswith(url + '?')
                        and FIELDS.fullmatch(full[len(url) + 1:])):
                    candidates.setdefault(full, []).append(rid)
        if len(candidates) != 1:
            raise PreparationError('Reconciliation invented an unprovided source URL.')
        full, receipt_ids = next(iter(candidates.items()))
        replacements[url] = (full, sorted(receipt_ids))
    edits = []

    def replace(match):
        raw = match.group(); found = citations(raw)
        url = found[0] if found else None
        if url not in replacements:
            return raw
        full, receipt_ids = replacements[url]
        if not raw.startswith(url):
            raise PreparationError('Citation restoration cannot identify an exact source span.')
        start = len(report[:match.start()].encode('utf-8'))
        edits.append({'start_byte': start, 'end_byte': start + len(url.encode('utf-8')),
                      'original_sha256': digest(url), 'restored_url': full, 'receipt_ids': receipt_ids})
        return full + raw[len(url):]

    rendered = URL.sub(replace, report) + NOTICE
    if not edits or set(citations(rendered)) - allowed:
        raise PreparationError('Reconciliation still contains an unprovided source URL.')
    return rendered, {'kind': 'restored-receipted-fields-v1', 'response_sha256': digest(response),
                      'original_report_sha256': digest(report), 'rendered_report_sha256': digest(rendered),
                      'accepted_as_source_verification': False, 'replacements': edits}
