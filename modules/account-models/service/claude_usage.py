"""Separate measured context windows from Claude's aggregate billing usage.

The terminal iterations array can contain only the last output continuation.
Prefer distinct root assistant messages in the captured stream. Repeated content
blocks for the same message are one observation, never separate model calls.
This module reads metadata only; it never reconstructs or changes report text.
"""
import json


def _input(usage):
    if not isinstance(usage, dict) or 'input_tokens' not in usage:
        return None
    values = tuple(usage.get(key, 0) for key in (
        'input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
    if any(type(value) is not int or value < 0 for value in values):
        return None
    return values


def context_usage(stdout, terminal):
    """Attest first/max only when every root context is accounted for.

Completeness requires successful termination, matching turn count and billing
input sum, valid counters, stable message identities and a single session. If
any proof is missing, telemetry is explicitly incomplete; the report itself is
unaffected. Terminal-only legacy output must meet the same accounting checks.
"""
    result = {'context_observations_complete': False}
    if not isinstance(terminal, dict):
        return result
    turns = terminal.get('num_turns')
    if type(turns) is int and turns > 0:
        result['cli_num_turns'] = turns
    else:
        turns = None
    raw = terminal.get('usage')
    total = _input(raw)
    if not isinstance(stdout, str) or len(stdout.encode()) > 32 * 1024 * 1024:
        return result
    messages = {}
    valid = True
    saw_root = False
    ended = False
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            valid = False
            continue
        if not isinstance(event, dict):
            valid = False
            continue
        if event.get('type') == 'result':
            if ended or event != terminal:
                valid = False
            ended = True
        if event.get('type') != 'assistant' or event.get('parent_tool_use_id'):
            continue
        saw_root = True
        message = event.get('message')
        if (ended or not isinstance(message, dict) or not terminal.get('session_id')
                or event.get('session_id') != terminal.get('session_id')):
            valid = False
            continue
        ident = message.get('id')
        tokens = _input(message.get('usage'))
        if not isinstance(ident, str) or not ident or tokens is None:
            valid = False
            continue
        if ident in messages and messages[ident] != tokens:
            valid = False
        else:
            messages[ident] = tokens
    if saw_root:
        contexts = [sum(tokens) for tokens in messages.values()]
        result['context_observation_source'] = 'assistant-messages'
        valid = valid and ended
    else:
        contexts = []
        result['context_observation_source'] = 'terminal-iterations'
        iterations = raw.get('iterations', []) if isinstance(raw, dict) else []
        if not isinstance(iterations, list):
            return result
        for item in iterations:
            if not isinstance(item, dict):
                valid = False
                continue
            if item.get('type') != 'message':
                continue
            tokens = _input(item)
            if tokens is None:
                valid = False
            else:
                contexts.append(sum(tokens))
    result['context_observations'] = len(contexts)
    if (valid and contexts and all(value > 0 for value in contexts)
            and turns == len(contexts) and total is not None and sum(contexts) == sum(total)
            and terminal.get('subtype') == 'success' and terminal.get('is_error') is False
            and terminal.get('stop_reason') == 'end_turn'):
        result.update(first_context_tokens=contexts[0], max_context_tokens=max(contexts),
                      context_observations_complete=True)
    return result
