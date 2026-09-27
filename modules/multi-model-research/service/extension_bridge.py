"""Private local command transport for the Chrome native messaging connection.

No listening network port; no browser credentials; no executable command payloads.
The host speaks only to the installed research extension and private spool files.
Processes running as this OS user can write the private spool: this is a trusted
single-user boundary, not isolation from other programs running as the same user.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import struct
import sys
import threading
import time
import uuid

EXTENSION_ID = os.environ.get('RESEARCH_EXTENSION_ID', 'diheppcpeakdedliglnjfgegpoakeanb')
if not re.fullmatch(r'[a-p]{32}', EXTENSION_ID):
    raise ValueError('Invalid RESEARCH_EXTENSION_ID')
ORIGIN = 'chrome-extension://' + EXTENSION_ID + '/'
DEFAULT_ROOT = Path(os.environ.get('RESEARCH_EXTENSION_ROOT', Path.home() / 'Library/Application Support/OpenNotebookResearch/extension-bridge'))
OPERATIONS = {'open', 'inspect', 'select_research', 'fill', 'submit', 'start_plan', 'collect', 'close', 'diagnose'}
MAX_COMMAND = 900_000
MAX_RESPONSE = 8 * 1024 * 1024
ID = re.compile(r'^[a-f0-9]{32}$')
JOB = re.compile(r'^(?:[a-f0-9]{32}:[a-z_]+|connection:(?:ChatGPT|Gemini|Claude)|probe:(?:ChatGPT|Gemini|Claude))$')
PROVIDERS = {'ChatGPT', 'Gemini', 'Claude'}


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(raw); out.flush(); os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def folders(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    for name in ('commands', 'results', 'sent'):
        (root / name).mkdir(exist_ok=True, mode=0o700)
        (root / name).chmod(0o700)
    return root


def validate_command(data, at=None):
    at = time.time() if at is None else at
    if not isinstance(data, dict) or not ID.fullmatch(str(data.get('id', ''))):
        raise ValueError('invalid_id')
    if data.get('op') not in OPERATIONS or data.get('provider') not in PROVIDERS:
        raise ValueError('invalid_operation')
    if not JOB.fullmatch(str(data.get('job', ''))):
        raise ValueError('invalid_job')
    expires = data.get('expires_at')
    if not isinstance(expires, (int, float)) or not at < expires <= at + 180:
        raise ValueError('expired_command')
    if len(json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_COMMAND:
        raise ValueError('command_too_large')


class ExtensionBridge:
    def __init__(self, root=DEFAULT_ROOT):
        self.root = folders(root)

    def connected(self):
        try:
            data = json.loads((self.root / 'connection.json').read_text())
            return data.get('origin') == ORIGIN and time.time() - data.get('heartbeat_at', 0) < 45
        except (OSError, ValueError):
            return False

    async def request(self, op, provider, job, timeout=120, **params):
        from browser_runtime import BrowserAttention
        if not self.connected():
            raise BrowserAttention('Chrome araştırma eklentisini açıp Yerel bağlantıyı başlat düğmesine basın.', 'browser_unavailable')
        ident = uuid.uuid4().hex
        command = {'id': ident, 'op': op, 'provider': provider, 'job': job,
                   'expires_at': time.time() + timeout, 'params': params}
        try:
            validate_command(command)
        except ValueError as exc:
            if str(exc) == 'command_too_large':
                raise BrowserAttention('Tam araştırma paketi Chrome aktarımının 900.000 UTF-8 bayt sınırını aşıyor. '
                    'Metin kesilmedi ve istek gönderilmedi. Paketi indirip raporu içe aktarabilirsiniz.', 'context_limit') from exc
            raise BrowserAttention('Yerel tarayıcı komutu geçersiz; istek gönderilmedi.', 'browser_changed') from exc
        path = self.root / 'commands' / (ident + '.json')
        result = self.root / 'results' / (ident + '.json')
        atomic_json(path, command)
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                if result.is_file():
                    if result.stat().st_size > MAX_RESPONSE:
                        raise BrowserAttention('Eklenti yanıtı boyut sınırını aştı.', 'browser_changed')
                    data = json.loads(result.read_text())
                    if data.get('id') != ident:
                        raise BrowserAttention('Eklenti yanıt kimliği uyuşmuyor.', 'browser_changed')
                    if data.get('error'):
                        error = data['error']
                        raise BrowserAttention(str(error.get('message', 'Tarayıcı işlemi tamamlanamadı.'))[:1200], error.get('kind', 'browser_changed'))
                    return data.get('result')
                await asyncio.sleep(0.2)
            raise BrowserAttention('Chrome bağlantısı zaman aşımına uğradı; gönderim otomatik tekrarlanmadı.', 'interrupted')
        finally:
            path.unlink(missing_ok=True)
            result.unlink(missing_ok=True)
            (self.root / 'sent' / (ident + '.json')).unlink(missing_ok=True)


def read_exact(stream, size):
    chunks = []
    remaining = size
    while remaining:
        part = stream.read(remaining)
        if not part:
            return None
        chunks.append(part); remaining -= len(part)
    return b''.join(chunks)


def read_frame(stream):
    raw = read_exact(stream, 4)
    if raw is None:
        return None
    size = struct.unpack('=I', raw)[0]
    if not 0 < size <= MAX_RESPONSE:
        raise ValueError('invalid_frame_size')
    payload = read_exact(stream, size)
    if payload is None:
        raise ValueError('truncated_frame')
    return json.loads(payload.decode('utf-8'))


def write_frame(stream, message):
    raw = json.dumps(message, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_COMMAND:
        raise ValueError('native_message_too_large')
    stream.write(struct.pack('=I', len(raw)) + raw)
    stream.flush()


def native_main(origin, root=DEFAULT_ROOT):
    if origin != ORIGIN:
        return 2
    os.umask(0o077)
    root = folders(root)
    lock = (root / 'host.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 3
    stopped = threading.Event()
    pid = os.getpid()

    def heartbeat():
        atomic_json(root / 'connection.json', {'origin': origin, 'pid': pid, 'heartbeat_at': time.time()})

    def receive():
        try:
            while not stopped.is_set():
                message = read_frame(sys.stdin.buffer)
                if message is None:
                    break
                if message.get('type') == 'heartbeat':
                    heartbeat(); continue
                ident = str(message.get('id', ''))
                if not ID.fullmatch(ident) or not (root / 'sent' / (ident + '.json')).is_file():
                    continue
                atomic_json(root / 'results' / (ident + '.json'), message)
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        finally:
            stopped.set()

    reader = threading.Thread(target=receive, daemon=True)
    reader.start()
    heartbeat()
    try:
        while not stopped.wait(0.2):
            for command_path in sorted((root / 'commands').glob('*.json')):
                try:
                    if command_path.stat().st_size > MAX_COMMAND:
                        raise ValueError('command_too_large')
                    data = json.loads(command_path.read_text())
                    validate_command(data)
                    if command_path.stem != data['id']:
                        raise ValueError('filename_mismatch')
                    sent = root / 'sent' / command_path.name
                    # Mark before writing: an interrupted delivery is never blindly replayed.
                    os.replace(command_path, sent)
                    write_frame(sys.stdout.buffer, data)
                except FileNotFoundError:
                    continue
                except (ValueError, TypeError, KeyError):
                    command_path.unlink(missing_ok=True)
                except (OSError, BrokenPipeError):
                    stopped.set(); break
    finally:
        try:
            current = json.loads((root / 'connection.json').read_text())
            if current.get('pid') == pid:
                atomic_json(root / 'connection.json', {'origin': origin, 'pid': pid, 'heartbeat_at': 0})
        except (OSError, ValueError):
            pass
        lock.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(native_main(sys.argv[1] if len(sys.argv) > 1 else ''))
