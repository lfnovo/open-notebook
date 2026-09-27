import asyncio
import copy
import json
from types import SimpleNamespace

import pytest

from context_preparation import PreparationError, digest
from test_account_review import sample


def test_many_sources_are_preserved_and_response_bytes_remain_bounded():
    from review_contract import parse_map
    node = sample()
    node['findings'][0]['sources'] *= 11
    original = json.dumps(node)
    assert len(parse_map(original, 'P1', 'Only when dry.', {'C1'})['findings'][0]['sources']) == 11
    node['findings'][0]['statement'] = 'x' * (2 * 1024 * 1024)
    with pytest.raises(PreparationError, match='response size'):
        parse_map(json.dumps(node), 'P1', 'Only when dry.', {'C1'})


def test_unmatched_quote_is_recorded_without_becoming_verified(tmp_path, monkeypatch):
    import review_sources
    monkeypatch.setattr(review_sources, '_request', lambda *a: (
        200, {'content-type': 'text/plain'}, b'Not safe when wet.'))
    reader = review_sources.SourceReader(tmp_path)
    source = {'url': 'https://example.org/a', 'quote': 'Safe when wet.'}
    receipt = reader.assess(source)
    assert receipt['verification'] == 'passage_not_matched'
    assert receipt['body_sha256'] == digest('Not safe when wet.')
    assert 'passage_context' not in receipt
    assert source['quote'] == 'Safe when wet.'
    reader.validate_receipt(source, receipt)
    (tmp_path / (digest(source['url']) + '.body')).write_bytes(b'changed')
    with pytest.raises(PreparationError):
        reader.validate_receipt(source, receipt)


def test_short_version_or_status_quote_is_preserved_but_not_treated_as_verified(tmp_path, monkeypatch):
    import review_sources
    from review_contract import parse_map
    node = sample()
    node['findings'][0]['sources'][0]['quote'] = '^6.1.1'
    assert parse_map(json.dumps(node), 'P1', 'Only when dry.', {'C1'})['findings'][0]['sources'][0]['quote'] == '^6.1.1'
    monkeypatch.setattr(review_sources, '_request', lambda *a: (
        200, {'content-type': 'text/plain'}, b'Current version: ^6.1.1'))
    receipt = review_sources.SourceReader(tmp_path).assess(node['findings'][0]['sources'][0])
    assert receipt['verification'] == 'insufficient_passage'


def test_unavailable_source_is_not_an_integrity_or_security_exception(tmp_path, monkeypatch):
    import review_sources
    reader = review_sources.SourceReader(tmp_path)
    source = {'url': 'https://example.org/a', 'quote': 'Only when dry.'}
    def unavailable(*args):
        raise review_sources.SourceUnavailable('Source returned HTTP 403.')
    monkeypatch.setattr(review_sources, '_request', unavailable)
    receipt = reader.assess(source)
    assert receipt['verification'] == 'source_unavailable'
    assert 'body_sha256' not in receipt
    def corrupted(*args):
        raise PreparationError('Saved snapshot changed.')
    monkeypatch.setattr(reader, 'snapshot', corrupted)
    with pytest.raises(PreparationError): reader.assess(source)


def test_source_assessment_does_not_swallow_private_address_rejection(tmp_path, monkeypatch):
    import review_sources
    monkeypatch.setattr(review_sources.socket, 'getaddrinfo', lambda *a, **kw: [
        (2, 1, 6, '', ('127.0.0.1', 443))])
    with pytest.raises(PreparationError):
        review_sources.SourceReader(tmp_path).assess({'url': 'https://example.org/a', 'quote': 'Only when dry.'})


def make_runner(tmp_path):
    from review_execution import ReviewRunner
    from review_contract import partition
    stage = {'id': 'review_chatgpt'}
    run = {'id': 'fixture', 'stages': [stage], 'paused': False}
    async def get(rid): return run
    async def save(value): pass
    engine = SimpleNamespace(input_path=lambda *a: tmp_path / 'input-packet.md', lock=asyncio.Lock(),
        get=get, stage=lambda r, sid: stage, store=SimpleNamespace(save=save))
    runner = ReviewRunner(engine, run, stage, '')
    runner.plan = partition('Only when dry.', lambda s: True)
    runner.state = {'jobs': {}, 'plan': runner.plan}
    return runner


@pytest.mark.asyncio
async def test_sources_cross_old_limits_resume_and_keep_every_original_field(tmp_path):
    runner = make_runner(tmp_path)
    calls = []
    def assess(source):
        calls.append(source['url'])
        status = ('passage_not_matched' if source['url'].endswith('/0') else
                  'source_unavailable' if source['url'].endswith('/1') else 'passage_matched_not_fact_checked')
        return {'verification': status, 'url': source['url']}
    runner.reader = SimpleNamespace(assess=assess, validate_receipt=lambda *a: None)
    node = sample()
    node['findings'][0]['sources'] = [
        {'url': 'https://example.org/' + str(i), 'quote': 'Only when dry.'} for i in range(145)]
    original = copy.deepcopy(node)
    receipts = {}
    await runner.check_sources(node, 'P1', receipts)
    finding = node['findings'][0]
    assert len(calls) == len(receipts) == len(finding['sources']) == 145
    assert finding['status'] == 'unverified' and finding['model_status'] == 'supported'
    assert finding['prior_assessments'][0]['status'] == 'unverified'
    assert finding['prior_assessments'][0]['model_status'] == 'supported'
    for field in ('statement', 'original_quote', 'conditions', 'counter_evidence', 'limits'):
        assert finding[field] == original['findings'][0][field]
    assert [(s['url'], s['quote']) for s in finding['sources']] == [(s['url'], s['quote']) for s in original['findings'][0]['sources']]
    assert runner.stage['preparation']['checked_sources'] == 145
    assert runner.stage['preparation']['unverified_sources'] == 2
    runner.state = json.loads(runner.path.read_text())
    await runner.check_sources(copy.deepcopy(original), 'P1', {})
    assert len(calls) == 145
    key = next(iter(runner.state['source_checks']))
    runner.state['source_checks'][key]['receipt']['verification'] = 'corrupt'
    with pytest.raises(PreparationError, match='receipt'):
        await runner.check_sources(copy.deepcopy(original), 'P1', {})


@pytest.mark.asyncio
async def test_source_check_pause_keeps_progress_and_checks_before_next_fetch(tmp_path):
    from engine import ServiceError
    runner = make_runner(tmp_path)
    calls = []
    def assess(source):
        calls.append(source)
        runner.run['paused'] = True
        return {'verification': 'passage_matched_not_fact_checked'}
    runner.reader = SimpleNamespace(assess=assess, validate_receipt=lambda *a: None)
    node = sample()
    node['findings'][0]['sources'].append({'url': 'https://example.org/b', 'quote': 'Only when dry.'})
    with pytest.raises(ServiceError): await runner.check_sources(node, 'P1', {})
    assert len(calls) == 1
    assert len(json.loads(runner.path.read_text())['source_checks']) == 1


def test_ledger_never_calls_an_unverified_receipt_matched():
    from review_execution import ledger
    node = sample()
    row = node['findings'][0]
    row.update(id='P1:F1', status='unverified', model_status='supported', verification={'unverified_sources': 1})
    row['prior_assessments'][0].update(status='unverified', model_status='supported')
    result = ledger({'protected_register': {'claims': [{'id': 'C1', 'statement': 'Only when dry.'}]}}, [node], 'review_chatgpt')
    assert all(c['status'] == 'unverified' for c in result['claims'])
    assert all('Source passage matched' not in c['reason'] for c in result['claims'])


def test_unverified_assessment_is_not_an_invented_disagreement():
    from review_execution import ledger
    known, unknown = sample(), sample()
    known['findings'][0]['id'] = 'P1:F1'
    unknown['findings'][0]['id'] = 'P2:F1'
    unknown['findings'][0]['prior_assessments'][0]['status'] = 'unverified'
    plan = {'protected_register': {'claims': [{'id': 'C1', 'statement': 'Only when dry.'}]}}
    assert ledger(plan, [known, unknown], 'review_chatgpt')['claims'][0]['status'] == 'unverified'
    unknown['findings'][0]['prior_assessments'][0]['status'] = 'rejected'
    assert ledger(plan, [known, unknown], 'review_chatgpt')['claims'][0]['status'] == 'disputed'


@pytest.mark.asyncio
async def test_repeated_downgrade_keeps_original_provider_assessment(tmp_path):
    runner = make_runner(tmp_path)
    runner.reader = SimpleNamespace(assess=lambda source: {'verification':'source_unavailable'},
                                    validate_receipt=lambda *a: None)
    node = sample(); row = node['findings'][0]
    row.update(status='unverified', model_status='supported')
    row['prior_assessments'][0].update(status='unverified', model_status='rejected')
    await runner.check_sources(node, 'P1', {})
    assert row['model_status'] == 'supported' and row['status'] == 'unverified'
    assert row['prior_assessments'][0]['model_status'] == 'rejected'


def test_catalog_anchor_cannot_claim_part_verification_in_ledger():
    from review_execution import ledger
    node=sample(); row=node['findings'][0]
    row.update(id='P1:F1', status='unverified', model_status='supported', original_anchor={'scope':'claim_catalog'})
    result=ledger({'protected_register':{'claims':[]}},[node],'review_chatgpt')
    assert result['claims'][0]['status']=='unverified'
    assert 'not this evidence part' in result['claims'][0]['reason']
