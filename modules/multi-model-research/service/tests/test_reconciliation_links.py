import copy
import json

import pytest

from context_preparation import PreparationError, digest
from test_review_reconciliation import Runner, payload

BASE = 'https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3232078.3232086'
FULL = BASE + '?fields=title,abstract,year,venue,authors'


def evidence(url=FULL):
    return {'source_receipts': {'receipt-1': {'url': url, 'verification': 'passage_not_matched'}}}


def test_unique_receipted_field_selector_is_restored_without_changing_prose_or_receipt():
    from reconciliation_links import restore_receipted_fields
    report = 'Türkçe: [' + BASE + '](' + BASE + '). Only under dry conditions.'
    data = evidence(); original = copy.deepcopy(data)
    rendered, audit = restore_receipted_fields(report, data, {FULL}, 'raw response')
    assert rendered.startswith(report.replace(BASE, FULL))
    assert 'not source verification' in rendered
    assert data == original
    assert audit['response_sha256'] == digest('raw response')
    assert audit['original_report_sha256'] == digest(report)
    assert audit['rendered_report_sha256'] == digest(rendered)
    assert len(audit['replacements']) == 2
    for edit in audit['replacements']:
        assert report.encode()[edit['start_byte']:edit['end_byte']].decode() == BASE
        assert edit['original_sha256'] == digest(BASE)
        assert edit['restored_url'] == FULL and edit['receipt_ids'] == ['receipt-1']
    assert audit['accepted_as_source_verification'] is False


@pytest.mark.parametrize('url', [
    BASE.replace('https:', 'http:'), BASE.replace('3232086', '3232087'),
    BASE.replace('api.semanticscholar.org', 'api.semanticscholar.org.evil.example'),
    BASE + '?fields=title', BASE + '#fragment',
    'https://example.org/paper', 'https://api.semanticscholar.org/graph/v1/paper/search',
])
def test_changed_identity_query_or_unknown_endpoint_stays_blocked(url):
    from reconciliation_links import restore_receipted_fields
    with pytest.raises(PreparationError):
        restore_receipted_fields(url, evidence(), {FULL}, 'raw')


@pytest.mark.parametrize('suffix', ['?id=123', '?fields=title&key=secret', '?fields=',
                                    '?fields=title#section', '?fields=title&fields=abstract'])
def test_arbitrary_or_ambiguous_query_is_never_restored(suffix):
    from reconciliation_links import restore_receipted_fields
    full = BASE + suffix
    with pytest.raises(PreparationError):
        restore_receipted_fields(BASE, evidence(full), {full}, 'raw')


def test_two_receipted_variants_cannot_be_guessed_and_mentions_are_not_receipts():
    from reconciliation_links import restore_receipted_fields
    data = evidence(); other = BASE + '?fields=title'
    data['source_receipts']['receipt-2'] = {'url': other}
    with pytest.raises(PreparationError):
        restore_receipted_fields(BASE, data, {FULL, other}, 'raw')
    with pytest.raises(PreparationError):
        restore_receipted_fields(BASE, {'source_receipts': {}}, {FULL}, 'raw')


def test_duplicate_receipts_for_same_exact_url_are_not_ambiguous():
    from reconciliation_links import restore_receipted_fields
    data = evidence(); data['source_receipts']['receipt-2'] = copy.deepcopy(data['source_receipts']['receipt-1'])
    _, audit = restore_receipted_fields(BASE, data, {FULL}, 'raw')
    assert audit['replacements'][0]['receipt_ids'] == ['receipt-1', 'receipt-2']


def test_restore_only_the_unique_variant_in_the_actual_dispatched_input():
    from reconciliation_links import restore_receipted_fields
    data = evidence(); other = BASE + '?fields=title'
    data['source_receipts']['elsewhere'] = {'url': other}
    rendered, audit = restore_receipted_fields(BASE, data, {FULL, other}, 'raw', {FULL})
    assert rendered.startswith(FULL) and audit['replacements'][0]['receipt_ids'] == ['receipt-1']
    with pytest.raises(PreparationError):
        restore_receipted_fields(BASE, data, {FULL, other}, 'raw', set())


def test_existing_url_is_byte_identical_and_other_invented_links_still_fail():
    from reconciliation_links import restore_receipted_fields
    report = 'No change: ' + FULL
    assert restore_receipted_fields(report, evidence(), {FULL}, 'raw') == (report, None)
    with pytest.raises(PreparationError):
        restore_receipted_fields(BASE + ' https://invented.example/claim', evidence(), {FULL}, 'raw')


@pytest.mark.asyncio
async def test_recovery_preserves_original_response_and_reuses_completed_calls():
    from review_reconciliation import reconcile
    runner = Runner(); original_call = runner.call; data = payload(4)
    data['working_findings'][0]['findings'][0]['sources'][0]['url'] = FULL
    data['source_receipts']['R0']['url'] = FULL
    async def shortened(key, request, profile):
        raw, usage = await original_call(key, request, profile)
        if key == 'reconcile-batch-1':
            value = json.loads(raw); value['report'] += ' ' + BASE
            raw = json.dumps(value)
        return raw, usage
    runner.call = shortened
    first = await reconcile(runner, data, 'Assess the evidence.\n')
    jobs = copy.deepcopy(runner.state['jobs']); count = len(runner.requests)
    assert 'citation_restoration' in first and FULL in first
    assert await reconcile(runner, data, 'Assess the evidence.\n') == first
    assert runner.state['jobs'] == jobs and len(runner.requests) == count
