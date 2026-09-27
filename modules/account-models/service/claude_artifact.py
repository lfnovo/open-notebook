"""Recover a JSON artifact continued by the CLI after an output-token boundary.

Only recorded assistant text is concatenated. Reasoning, progress, tool results
and user text never become artifact bytes. Unrecognized boundaries fail closed.
"""
import hashlib
import json

CONTINUATION = ('Output token limit hit. Resume directly — no apology, no recap of what you were doing. '
                'Pick up mid-thought if that is where the cut happened. Break remaining work into smaller pieces.')


def recover_json_artifact(stdout, tail):
    if not isinstance(tail, str) or len(stdout.encode()) > 32 * 1024 * 1024: return None
    segments = []; session = None; message_id = None; continued = False; boundaries = 0
    seen = {}; terminal = None
    for line in stdout.splitlines():
        try: event = json.loads(line)
        except ValueError: return None
        if not isinstance(event, dict): return None
        ident = event.get('uuid')
        if ident:
            if ident in seen:
                if seen[ident] != event: return None
                continue
            seen[ident] = event
        kind = event.get('type'); message = event.get('message', {})
        content = message.get('content', []) if isinstance(message, dict) else []
        if not isinstance(content, list): content = []
        if kind in ('assistant', 'user') and any(b.get('type') in ('tool_use', 'tool_result') for b in content):
            segments = []; continued = False; boundaries = 0; session = None; message_id = None
        if kind == 'user':
            is_continuation = (event.get('isSynthetic') is True and len(content) == 1
                               and content[0].get('type') == 'text' and content[0].get('text') == CONTINUATION)
            if is_continuation and segments:
                if event.get('session_id') != session: return None
                continued = True; boundaries += 1
            else:
                segments = []; boundaries = 0; continued = False; session = None; message_id = None
        if kind == 'assistant' and not event.get('parent_tool_use_id'):
            for block in content:
                if block.get('type') != 'text': continue
                text = block.get('text')
                if not isinstance(text, str) or not message.get('id'): return None
                if segments and message.get('id') != message_id and not continued:
                    segments = []; boundaries = 0; session = None
                if session and session != event.get('session_id'): return None
                session = event.get('session_id'); message_id = message['id']; continued = False
                segments.append(text)
                if len(segments) > 8 or sum(len(s.encode()) for s in segments) > 2 * 1024 * 1024: return None
        if kind == 'result': terminal = event
    if (not terminal or terminal.get('subtype') != 'success' or terminal.get('is_error') is not False
            or terminal.get('stop_reason') != 'end_turn' or not session or terminal.get('session_id') != session
            or terminal.get('result') != tail or len(segments) < 2 or not boundaries or segments[-1] != tail):
        return None
    text = ''.join(segments)
    value = text.strip()
    if value.startswith('```json\n') and value.endswith('\n```'): value = value[8:-4]
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result: raise ValueError('Duplicate artifact key')
            result[key] = item
        return result
    def invalid_constant(value): raise ValueError('Non-finite artifact value')
    try: parsed = json.loads(value, object_pairs_hook=unique, parse_constant=invalid_constant)
    except ValueError: return None
    if not isinstance(parsed, dict): return None
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
    return {'kind':'claude-output-continuation-v1', 'text':text, 'sha256':sha(text),
            'tail_sha256':sha(tail), 'segments':len(segments), 'segment_sha256':[sha(s) for s in segments]}
