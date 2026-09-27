"""Private, durable request results. A lost HTTP connection must not lose paid work."""
import hashlib
import json
import os
from pathlib import Path
import re
import threading


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class ReceiptStore:
    def __init__(self, root):
        self.root = Path(root)
        self.local = threading.local()

    @staticmethod
    def fingerprint(body):
        return hashlib.sha256(encoded({k: v for k, v in body.items()
                                      if k != 'local_request_id'}).encode()).hexdigest()

    def directory(self, ident):
        if not isinstance(ident, str) or not re.fullmatch('[a-f0-9]{32}', ident):
            raise ValueError('Invalid local request ID')
        return self.root / ident

    @staticmethod
    def write(path, value):
        temporary = path.with_suffix('.tmp')
        with open(temporary, 'w', opener=lambda name, flags: os.open(name, flags, 0o600)) as stream:
            stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())
        temporary.replace(path)

    def read(self, ident):
        path = self.directory(ident) / 'receipt.json'
        if not path.exists(): return None
        value = json.loads(path.read_text())
        if value.get('state') == 'completed':
            if hashlib.sha256(encoded(value['result']).encode()).hexdigest() != value.get('result_sha256'):
                raise ValueError('Saved request result failed its integrity check')
        return value

    def public_result(self, ident):
        """Expose a verified derived artifact without rewriting the original receipt."""
        value = self.read(ident)
        if not value or value.get('state') != 'completed': return value
        choices = value.get('result', {}).get('choices', [])
        if len(choices) != 1 or choices[0].get('finish_reason') != 'stop': return value
        tail = choices[0].get('message', {}).get('content')
        if not isinstance(tail, str): return value
        from claude_artifact import recover_json_artifact
        recovered = []
        for path in self.directory(ident).glob('cli-*.json'):
            raw = path.read_bytes(); capture = json.loads(raw)
            sealed = capture.pop('payload_sha256', None)
            if sealed and sealed != hashlib.sha256(encoded(capture).encode()).hexdigest():
                raise ValueError('Saved CLI capture failed its integrity check')
            if capture.get('provider') != 'claude' or capture.get('exit_code') != 0: continue
            artifact = recover_json_artifact(capture.get('stdout', ''), tail)
            if artifact:
                artifact.update(capture_sha256=hashlib.sha256(raw).hexdigest(),
                    capture_previously_sealed=bool(sealed), source_result_sha256=value['result_sha256'])
                recovered.append(artifact)
        if len(recovered) > 1: raise ValueError('Ambiguous CLI capture recovery')
        return dict(value, artifact_recovery=recovered[0]) if recovered else value

    def claim(self, body):
        ident = body['local_request_id']
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory = self.directory(ident)
        try: directory.mkdir(mode=0o700)
        except FileExistsError: return False
        self.write(directory / 'receipt.json', {'state': 'running', 'request_id': ident,
                   'request_sha256': self.fingerprint(body)})
        return True

    def finish(self, ident, **outcome):
        value = self.read(ident)
        if outcome.get('state') == 'completed':
            outcome['result_sha256'] = hashlib.sha256(encoded(outcome['result']).encode()).hexdigest()
        self.write(self.directory(ident) / 'receipt.json', dict(value, **outcome))

    def capture(self, provider, stdout, stderr, exit_code):
        ident = getattr(self.local, 'ident', None)
        if not ident: return
        directory = self.directory(ident)
        # Preserve transcripts only in the private local receipt, never server logs or Git.
        number = len(list(directory.glob('cli-*.json')))
        payload = {'provider': provider, 'stdout': stdout, 'stderr': stderr, 'exit_code': exit_code}
        self.write(directory / ('cli-' + str(number) + '.json'), dict(payload,
            payload_sha256=hashlib.sha256(encoded(payload).encode()).hexdigest()))
