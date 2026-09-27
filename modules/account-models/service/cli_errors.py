"""Classify terminal failures, never arbitrary research text or tool results."""
import json
import re


def terminal_error(provider, stdout, stderr):
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict): events.append(event)
        except ValueError: pass
    try:
        whole = json.loads(stdout[stdout.find('{'):])
        if isinstance(whole, dict) and not events: events.append(whole)
    except ValueError: pass
    selected = None
    if provider == 'claude':
        for event in events:
            if event.get('type') == 'result' or 'result' in event and 'is_error' in event:
                selected = event
        if selected is not None:
            # A successful research result is data even if CLI cleanup returned nonzero.
            if not selected.get('is_error') and not selected.get('error'): return '', None
            code = selected.get('api_error_status')
            fields = [selected.get(k) for k in ('error', 'errors', 'terminal_reason')]
            # subtype=success + is_error has occurred in CLI releases. Do not scan
            # its result: it may contain an entire research report.
            if selected.get('subtype') != 'success': fields.append(selected.get('result'))
            return ' '.join(str(v) for v in fields if v).lower(), code
    if provider == 'codex':
        for event in events:
            if event.get('type') == 'turn.completed': selected = None
            elif event.get('type') in ('turn.failed', 'error'): selected = event
        if selected is not None:
            return str(selected.get('error') or selected.get('message') or '').lower(), None
        if events: return '', None
    # Restrict unstructured diagnostics to explicit error lines. Never inspect
    # stdout from an otherwise structured transcript.
    lines = [line for line in (stderr or (stdout if not events else '')).splitlines()
             if re.match(r'\s*(error|fatal|failed)\b', line, re.I)]
    return '\n'.join(lines).lower(), None
