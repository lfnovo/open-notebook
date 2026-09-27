"""Report whether the dedicated profile holds a provider session cookie.

Scope and limits, stated plainly:
  * This reads cookie *names* and host keys only. The database is opened read-only and
    is not copied anywhere; no value column is ever selected, so encrypted values are
    neither read nor moved.
  * A session cookie being present is a necessary condition, not a sufficient one. It
    does not prove the cookie is still valid, unexpired, or that the provider will
    accept it — still less that the account has Deep Research access. Treat a positive
    result as "worth trying", never as a deployment gate on its own.
  * The everyday Chrome profile is never touched.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(os.environ.get('RESEARCH_ROOT',
                           Path.home() / 'Library/Application Support/OpenNotebookResearch'))
PROFILE = ROOT / 'browser-profile'
# Exact cookie names a provider issues only after a completed sign-in. Anonymous
# visitors also receive device, analytics and bot-management cookies, and names such as
# Google's SIDCC exist while signed out, so prefix matching is deliberately not used.
SESSION_COOKIES = {
    'ChatGPT': ('chatgpt.com', ('__Secure-next-auth.session-token',)),
    'Gemini': ('google.com', ('__Secure-1PSID', '__Secure-3PSID', 'SID')),
    'Claude': ('claude.ai', ('sessionKey',)),
}


def host_matches(host_key, domain):
    """Match on domain boundaries so 'google.com' never matches 'notgoogle.com.evil'."""
    host = (host_key or '').lstrip('.').lower()
    domain = domain.lower()
    return host == domain or host.endswith('.' + domain)


def name_matches(name, expected):
    """Exact name, or a provider's numbered chunk of that exact name (…token.0)."""
    for want in expected:
        if name == want:
            return True
        if name.startswith(want + '.') and name[len(want) + 1:].isdigit():
            return True
    return False


def read_cookies():
    source = PROFILE / 'Default' / 'Cookies'
    if not source.is_file():
        raise SystemExit('Araştırma profili bulunamadı: ' + str(source))
    try:
        with sqlite3.connect('file:' + str(source) + '?mode=ro', uri=True) as db:
            return db.execute('SELECT host_key, name FROM cookies').fetchall()
    except sqlite3.OperationalError as exc:
        raise SystemExit('Çerez veritabanı okunamadı (' + str(exc) + '). Araştırma '
                         'tarayıcısı açıksa Cmd+Q ile tamamen kapatıp tekrar deneyin.')


def main():
    config = ROOT / 'config.json'
    if config.is_file() and json.loads(config.read_text()).get('browser_transport') == 'extension':
        from extension_bridge import ExtensionBridge, EXTENSION_ID
        connected = ExtensionBridge(ROOT / 'extension-bridge').connected()
        report = {'transport':'extension', 'native_connected':connected, 'expected_extension_id':EXTENSION_ID,
                  'account_sessions':'not_checked',
                  'means':'Bu kontrol yerel eklenti baglantisini olcer; hesap girisi veya Deep Research kotasini kanitlamaz. Eski Playwright profili ve cerezler okunmadi.'}
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if connected else 2
    rows = read_cookies()
    report = {'profile': str(PROFILE), 'total_cookies': len(rows),
              'means': 'Oturum çerezinin varlığı gerekli koşuldur, yeterli değildir. '
                       'Geçerlilik, süre ve Deep Research erişimi ayrıca doğrulanmalıdır.',
              'providers': []}
    every = True
    for provider, (domain, names) in SESSION_COOKIES.items():
        owned = [n for h, n in rows if host_matches(h, domain)]
        present = any(name_matches(n, names) for n in owned)
        every = every and present
        report['providers'].append({
            'provider': provider, 'cookie_domain': domain, 'cookies': len(owned),
            'session_cookie_present': present,
            # Retained so existing review scripts keep working; same measurement.
            'signed_in': present,
            'message': 'Oturum çerezi bulundu. Geçerliliği bu kontrolle kanıtlanmaz.' if present else
                       'Oturum çerezi yok. Bu hesaba bu profilde giriş yapılmamış.'})
    report['all_session_cookies_present'] = every
    report['all_signed_in'] = every
    print(json.dumps(report, ensure_ascii=False, indent=2))
    out = ROOT / 'login-verification.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    out.chmod(0o600)
    return 0 if every else 2


if __name__ == '__main__':
    sys.exit(main())
