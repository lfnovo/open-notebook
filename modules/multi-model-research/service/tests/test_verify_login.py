"""Cookie-name matching must be exact and domain-bounded."""
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import verify_login


def run(rows, monkeypatch, tmp_path):
    monkeypatch.setattr(verify_login, 'ROOT', tmp_path)
    monkeypatch.setattr(verify_login, 'read_cookies', lambda: rows)
    report = {}
    monkeypatch.setattr(verify_login, 'print', lambda text: report.update(__import__('json').loads(text)),
                        raising=False)
    verify_login.main()
    import json
    return json.loads((tmp_path / 'login-verification.json').read_text())


def state(report, provider):
    return next(p['session_cookie_present'] for p in report['providers'] if p['provider'] == provider)


def test_sidcc_alone_is_not_a_google_session(monkeypatch, tmp_path):
    # SIDCC is issued to signed-out visitors; prefix matching used to accept it as SID.
    assert state(run([('.google.com', 'SIDCC')], monkeypatch, tmp_path), 'Gemini') is False


def test_exact_google_session_cookie_counts(monkeypatch, tmp_path):
    assert state(run([('.google.com', 'SID')], monkeypatch, tmp_path), 'Gemini') is True


def test_chunked_chatgpt_session_cookie_counts(monkeypatch, tmp_path):
    rows = [('.chatgpt.com', '__Secure-next-auth.session-token.0')]
    assert state(run(rows, monkeypatch, tmp_path), 'ChatGPT') is True


def test_lookalike_name_is_rejected(monkeypatch, tmp_path):
    rows = [('.chatgpt.com', '__Secure-next-auth.session-token-backup')]
    assert state(run(rows, monkeypatch, tmp_path), 'ChatGPT') is False


def test_lookalike_domain_is_rejected(monkeypatch, tmp_path):
    assert state(run([('.notgoogle.com.evil.test', 'SID')], monkeypatch, tmp_path), 'Gemini') is False


def test_subdomain_of_the_real_host_counts(monkeypatch, tmp_path):
    assert state(run([('accounts.google.com', 'SID')], monkeypatch, tmp_path), 'Gemini') is True


def test_claude_session_cookie(monkeypatch, tmp_path):
    report = run([('.claude.ai', 'sessionKey')], monkeypatch, tmp_path)
    assert state(report, 'Claude') is True and state(report, 'ChatGPT') is False
    assert report['all_session_cookies_present'] is False


def test_extension_mode_does_not_read_legacy_profile_or_claim_sessions(monkeypatch, tmp_path, capsys):
    import json
    monkeypatch.setattr(verify_login,'ROOT',tmp_path)
    (tmp_path/'config.json').write_text('{"browser_transport":"extension"}')
    def forbidden():raise AssertionError('Legacy cookie database must not be read')
    monkeypatch.setattr(verify_login,'read_cookies',forbidden)
    assert verify_login.main()==2
    report=json.loads(capsys.readouterr().out)
    assert report['transport']=='extension' and report['account_sessions']=='not_checked'
