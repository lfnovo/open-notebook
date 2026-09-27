import copy

import pytest

from context_preparation import PreparationError


@pytest.mark.parametrize('matched', [True, False])
def test_receipted_redirect_can_be_cited_without_upgrading_quote_status(tmp_path, monkeypatch, matched):
    import review_sources
    from review_execution import source_urls
    original = 'https://example.org/old'
    final = 'https://example.org/current'
    def request(url, deadline):
        if url == original:
            return 302, {'location': final}, b''
        assert url == final
        return 200, {'content-type': 'text/plain'}, b'Only when dry.'
    monkeypatch.setattr(review_sources, '_request', request)
    source = {'url': original, 'quote': 'Only when dry.' if matched else 'Not safe when wet.'}
    reader = review_sources.SourceReader(tmp_path)
    receipt = reader.assess(source)
    reader.validate_receipt(source, receipt)
    before = copy.deepcopy(receipt)
    nodes = [{'findings': [{'sources': [dict(source, receipt_id='R1')]}]}]
    assert source_urls(nodes, {'R1': receipt}) == {original, final}
    assert receipt == before
    assert receipt['verification'] == ('passage_matched_not_fact_checked' if matched else 'passage_not_matched')


def test_redirect_tampering_is_rejected_against_the_stored_snapshot(tmp_path, monkeypatch):
    import review_sources
    monkeypatch.setattr(review_sources, '_request', lambda *a: (200, {'content-type': 'text/plain'}, b'Only when dry.'))
    source = {'url': 'https://example.org/a', 'quote': 'Only when dry.'}
    reader = review_sources.SourceReader(tmp_path)
    receipt = reader.assess(source)
    receipt['final_url'] = 'https://invented.example/a'
    with pytest.raises(PreparationError, match='snapshot'):
        reader.validate_receipt(source, receipt)


def test_unavailable_receipt_cannot_admit_a_redirect_and_unrelated_receipts_are_ignored():
    from review_execution import source_urls
    original = 'https://example.org/a'
    nodes = [{'findings': [{'sources': [{'url': original, 'receipt_id': 'R1'}]}]}]
    receipts = {'R1': {'url': original, 'verification': 'source_unavailable', 'final_url': 'https://invented.example/b'},
                'unrelated': {'url': 'https://other.example/c', 'final_url': 'https://other.example/d', 'verification': 'passage_not_matched'}}
    assert source_urls(nodes, receipts) == {original}


def test_source_and_receipt_identity_mismatch_fails():
    from review_execution import source_urls
    nodes = [{'findings': [{'sources': [{'url': 'https://example.org/a', 'receipt_id': 'R1'}]}]}]
    with pytest.raises(PreparationError):
        source_urls(nodes, {'R1': {'url': 'https://different.example/b', 'verification': 'passage_not_matched'}})
