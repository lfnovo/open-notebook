import json
from unittest.mock import Mock

import pytest
import server


def test_research_words_cannot_become_auth_or_quota_errors(monkeypatch):
    events = [
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text':
            'Research: login, authentication, credentials, quota and 429.'}]}},
        {'type': 'result', 'subtype': 'error_during_execution', 'is_error': True,
         'result': 'Connection reset by peer', 'stop_reason': None},
    ]
    proc = Mock(returncode=1)
    proc.communicate.return_value = ('\n'.join(map(json.dumps, events)), '')
    monkeypatch.setattr(server.JOBS, 'spawn', lambda *a, **k: proc)
    with pytest.raises(server.BridgeError) as error:
        server.run_cli('claude-account', 'input', 'research_review')
    assert error.value.status == 502


def test_recovered_codex_stream_error_does_not_discard_final_response(monkeypatch):
    events = [
        {'type': 'error', 'message': 'Reconnecting after stream disconnect'},
        {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'Complete report'}},
        {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 4}},
    ]
    proc = Mock(returncode=0)
    proc.communicate.return_value = ('\n'.join(map(json.dumps, events)), '')
    monkeypatch.setattr(server.JOBS, 'spawn', lambda *a, **k: proc)
    assert server.run_cli('chatgpt-account', 'input', 'research_synthesis')[0] == 'Complete report'


def test_lost_http_response_can_be_recovered_without_calling_model(tmp_path, monkeypatch):
    from receipts import ReceiptStore
    store = ReceiptStore(tmp_path)
    monkeypatch.setattr(server, 'RECEIPTS', store)
    call = Mock(return_value=('Complete report', {}))
    monkeypatch.setattr(server, 'run_cli', call)
    body = {'model': 'claude-account', 'local_request_id': 'a' * 32,
            'messages': [{'role': 'user', 'content': 'Input'}]}
    first = server.completion(body)
    assert server.completion(body) == first
    assert call.call_count == 1
    recovered = ReceiptStore(tmp_path).read('a' * 32)
    assert recovered['result'] == first
    assert recovered['state'] == 'completed'
    assert recovered['request_sha256'] == store.fingerprint(body)
    assert (tmp_path / ('a' * 32) / 'receipt.json').stat().st_mode & 0o777 == 0o600
    with pytest.raises(server.BridgeError):
        server.completion(dict(body, messages=[{'role': 'user', 'content': 'Changed'}]))
    assert call.call_count == 1


def test_failed_request_retains_receipt_and_never_repeats_same_id(tmp_path, monkeypatch):
    from receipts import ReceiptStore
    monkeypatch.setattr(server, 'RECEIPTS', ReceiptStore(tmp_path))
    call = Mock(side_effect=server.BridgeError('Interrupted; partial output was not accepted.', 502))
    monkeypatch.setattr(server, 'run_cli', call)
    body = {'model': 'claude-account', 'local_request_id': 'b' * 32,
            'messages': [{'role': 'user', 'content': 'Input'}]}
    for _ in range(2):
        with pytest.raises(server.BridgeError) as error:
            server.completion(body)
        assert error.value.payload()['error']['request_settled'] is True
    assert call.call_count == 1


def test_unfinished_receipt_cannot_launch_duplicate(tmp_path, monkeypatch):
    from receipts import ReceiptStore
    store = ReceiptStore(tmp_path)
    monkeypatch.setattr(server, 'RECEIPTS', store)
    body = {'model': 'claude-account', 'local_request_id': 'c' * 32,
            'messages': [{'role': 'user', 'content': 'Input'}]}
    store.claim(body)
    call = Mock()
    monkeypatch.setattr(server, 'run_cli', call)
    with pytest.raises(server.BridgeError) as error:
        server.completion(body)
    assert error.value.status == 409
    assert not call.called


@pytest.mark.parametrize('status', [401, 429])
def test_explicit_terminal_status_survives_tool_activity(monkeypatch, status):
    events = [{'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'WebSearch', 'id': 's'}]}},
              {'type': 'result', 'subtype': 'success', 'is_error': True,
               'api_error_status': status, 'result': 'Partial report about login and quota'}]
    proc = Mock(returncode=1)
    proc.communicate.return_value = ('\n'.join(map(json.dumps, events)), '')
    monkeypatch.setattr(server.JOBS, 'spawn', lambda *a, **k: proc)
    monkeypatch.setattr(server.MODEL_POLICY, 'limited', Mock())
    with pytest.raises(server.BridgeError) as error:
        server.run_cli('claude-account', 'input', 'research_review')
    assert error.value.status == status


def test_private_transcript_is_preserved_when_terminal_response_is_rejected(tmp_path, monkeypatch):
    from receipts import ReceiptStore
    store = ReceiptStore(tmp_path)
    monkeypatch.setattr(server, 'RECEIPTS', store)
    stdout = json.dumps({'type': 'result', 'subtype': 'success', 'is_error': True,
                         'result': 'Partial research: authentication, login, quota'})
    proc = Mock(returncode=1); proc.communicate.return_value = (stdout, '')
    monkeypatch.setattr(server.JOBS, 'spawn', lambda *a, **k: proc)
    body = {'model': 'claude-account', 'local_request_id': 'd' * 32,
            'messages': [{'role': 'user', 'content': 'Input'}]}
    with pytest.raises(server.BridgeError) as error: server.completion(body)
    assert error.value.status == 502
    captured = tmp_path / ('d' * 32) / 'cli-0.json'
    assert json.loads(captured.read_text())['stdout'] == stdout
    assert captured.stat().st_mode & 0o777 == 0o600
    assert 'Partial research' not in str(error.value)
