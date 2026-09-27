"""Bounded public-source snapshots, with DNS-pinned connections and no credentials.

Quote matching proves presence in a retrieved text, not truth or entailment.
Models have no access to this process's filesystem or network credentials.
"""
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

from context_preparation import PreparationError, digest

MAX_BYTES = 2 * 1024 * 1024


class SourceUnavailable(PreparationError):
    """A public page cannot currently supply usable text; never a verified claim."""


class PassageNotMatched(PreparationError):
    """The page was retrieved, but its text does not contain the claimed quote."""


class InsufficientPassage(PassageNotMatched):
    """A short version/label is retained but cannot establish meaningful support."""


def validate_target(url):
    try:
        parsed = urlsplit(url)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.port not in (None, 80, 443)
                or any(ord(c) < 33 for c in url)):
            raise ValueError('invalid URL')
        host = parsed.hostname.encode('idna').decode('ascii')
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        addresses = list(dict.fromkeys(row[4][0] for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))
        if not addresses or any(not ipaddress.ip_address(address).is_global or ipaddress.ip_address(address).is_multicast
                                for address in addresses):
            raise ValueError('non-public address')
    except OSError as exc:
        raise SourceUnavailable('Public source hostname could not be resolved.') from exc
    except (ValueError, UnicodeError) as exc:
        raise PreparationError('Source URL is not a permitted public HTTP(S) target.') from exc
    return parsed, host, port, addresses[0]


def _request(url, deadline):
    parsed, host, port, address = validate_target(url)
    timeout = max(.1, min(10, deadline - time.monotonic()))
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    # Pin the validated address; TLS still verifies the original hostname.
    def connect():
        sock = socket.create_connection((address, port), timeout=timeout)
        try:
            connection.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host) if parsed.scheme == 'https' else sock
        except Exception:
            sock.close(); raise
    connection.connect = connect
    try:
        path = urlunsplit(('', '', parsed.path or '/', parsed.query, ''))
        connection.request('GET', path, headers={'User-Agent': 'OpenNotebook-SourceVerifier/1.0',
            'Accept': 'text/html,text/plain,application/json', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        headers = dict((k.lower(), v) for k, v in response.getheaders())
        if response.status in (301, 302, 303, 307, 308): return response.status, headers, b''
        if response.status != 200: raise SourceUnavailable('Source returned HTTP ' + str(response.status) + '.')
        if headers.get('content-encoding', 'identity') != 'identity':
            raise SourceUnavailable('Compressed source response is not admitted by the bounded reader.')
        if int(headers.get('content-length', '0')) > MAX_BYTES:
            raise SourceUnavailable('Source exceeds the snapshot size limit.')
        content = bytearray()
        while len(content) <= MAX_BYTES:
            if time.monotonic() >= deadline: raise SourceUnavailable('Source snapshot deadline exceeded.')
            if connection.sock: connection.sock.settimeout(max(.1, min(5, deadline-time.monotonic())))
            block = response.read1(min(65536, MAX_BYTES + 1 - len(content)))
            if not block: break
            content.extend(block)
        if len(content) > MAX_BYTES: raise SourceUnavailable('Source exceeds the snapshot size limit; it was not truncated.')
        return response.status, headers, bytes(content)
    finally:
        connection.close()


def passage_matches(text, quote):
    # Deliberately no case folding, punctuation removal or negation rewriting.
    normalize = lambda s: re.sub(r'\s+', ' ', s).strip()
    return len(normalize(quote)) >= 12 and normalize(quote) in normalize(text)


class SourceReader:
    def __init__(self, root):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def snapshot(self, url):
        key = digest(url)
        record_path = self.root / (key + '.json')
        if record_path.exists():
            try:
                record = json.loads(record_path.read_text())
                raw = (self.root / (key + '.body')).read_bytes()
                if (record['url'] != url or hashlib.sha256(raw).hexdigest() != record['body_sha256']
                        or digest(record['text']) != record['text_sha256']):
                    raise PreparationError('Saved source snapshot failed its integrity check.')
                return record
            except (OSError,ValueError,KeyError,TypeError) as exc:
                raise PreparationError('Saved source snapshot is incomplete or failed its integrity check.') from exc
        current = url; deadline = time.monotonic() + 25
        try:
            for _ in range(5):
                status, headers, raw = _request(current, deadline)
                if status in (301, 302, 303, 307, 308):
                    if not headers.get('location'): raise SourceUnavailable('Source redirect has no destination.')
                    current = urljoin(current, headers['location']); continue
                break
            else: raise SourceUnavailable('Source redirect limit exceeded.')
            kind = headers.get('content-type', '').split(';')[0].strip().lower()
            if kind not in ('text/html', 'text/plain', 'text/markdown', 'application/json', 'application/xhtml+xml'):
                raise SourceUnavailable('Source format is not supported by the bounded passage verifier; use a public HTML/text source.')
            from bs4 import BeautifulSoup, UnicodeDammit
            text = UnicodeDammit(raw).unicode_markup
            if text is None: raise SourceUnavailable('Source text could not be decoded.')
            if kind in ('text/html', 'application/xhtml+xml'):
                document = BeautifulSoup(text, 'html.parser')
                for tag in document(['script', 'style', 'noscript', 'template']): tag.decompose()
                text = document.get_text(' ', strip=True)
            record = {'url': url, 'final_url': current, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'content_type': kind, 'bytes': len(raw), 'body_sha256': hashlib.sha256(raw).hexdigest(),
                'text_sha256': digest(text), 'text': text}
            for destination, content in [(self.root/(key+'.body'), raw), (record_path, json.dumps(record, ensure_ascii=False).encode())]:
                temporary = destination.with_suffix(destination.suffix + '.tmp')
                temporary.touch(mode=0o600); temporary.write_bytes(content); temporary.replace(destination)
            return record
        except (OSError, ValueError, http.client.HTTPException) as exc:
            if isinstance(exc, PreparationError): raise
            raise SourceUnavailable('Public source could not be independently retrieved.') from exc

    def verify(self, source):
        record = self.snapshot(source['url'])
        if len(re.sub(r'\s+', ' ', source['quote']).strip()) < 12:
            raise InsufficientPassage('The quotation is too short to establish meaningful source context.')
        if not passage_matches(record['text'], source['quote']):
            raise PassageNotMatched('A quoted passage was not found in the independently retrieved source.')
        text=re.sub(r'\s+',' ',record['text']).strip()
        quote=re.sub(r'\s+',' ',source['quote']).strip();start=text.index(quote);end=start+len(quote)
        # Expose nearby negation/qualifications to the reconciler, not just a potentially cherry-picked quote.
        left=max(0,start-600);right=min(len(text),end+600)
        return {k: v for k, v in record.items() if k != 'text'} | {
            'verification': 'passage_matched_not_fact_checked', 'passage_context':text[left:right],
            'context_is_excerpt':left>0 or right<len(text), 'quote_start_in_context':start-left}

    def assess(self, source):
        """Retain negative outcomes explicitly; security/corruption errors still stop."""
        try:
            return self.verify(source)
        except PassageNotMatched as exc:
            record = self.snapshot(source['url'])
            return {k: v for k, v in record.items() if k != 'text'} | {
                'verification': 'insufficient_passage' if isinstance(exc, InsufficientPassage) else 'passage_not_matched', 'reason': str(exc)}
        except SourceUnavailable as exc:
            return {'url': source['url'], 'verification': 'source_unavailable', 'reason': str(exc),
                    'checked_at': datetime.now(timezone.utc).isoformat()}

    def validate_receipt(self, source, receipt):
        """Reuse recorded checks without accepting a changed or missing snapshot."""
        if receipt.get('verification') not in ('source_unavailable', 'passage_not_matched', 'insufficient_passage', 'passage_matched_not_fact_checked'):
            raise PreparationError('Saved source receipt has an invalid verification status.')
        if receipt.get('url') != source['url']:
            raise PreparationError('Saved source receipt refers to a different URL.')
        if receipt.get('verification') == 'source_unavailable':
            return
        key = digest(source['url'])
        if not (self.root / (key + '.json')).is_file():
            raise PreparationError('Saved source receipt is missing its snapshot.')
        snapshot = self.snapshot(source['url'])
        if (receipt.get('body_sha256') != snapshot['body_sha256']
                or receipt.get('text_sha256') != snapshot['text_sha256']
                or receipt.get('final_url') != snapshot['final_url']):
            raise PreparationError('Saved source receipt differs from its snapshot.')
