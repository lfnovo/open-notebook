"""Read citation text through JSON serialization without rewriting any source URL."""
import json
import re


FENCE = re.compile(r'(?m)^(?P<fence>`{3,}|~{3,})(?:json|evidence-ledger)[ \t]*\r?\n'
                   r'(?P<body>[\s\S]*?)^(?P=fence)[ \t]*(?:\r?\n|$)')


def decoded(text):
    """Keep every object key and value, including duplicates, for inspection.

    This is citation extraction, not schema acceptance. A duplicate key must not
    hide an earlier URL; strict artifact validation remains a separate gate.
    """
    if not text.lstrip().startswith(('{', '[', '"')):
        return None
    try:
        return json.loads(text, object_pairs_hook=lambda pairs: [v for pair in pairs for v in pair])
    except (ValueError, RecursionError):
        return None


def strings(value):
    # Iterative traversal avoids Python recursion on a deeply nested object.
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            yield item
        elif isinstance(item, list):
            stack.extend(reversed(item))


def fragments(text, depth=0):
    """Decode only complete JSON or explicitly labelled, valid fenced JSON.

    Literal backslashes outside those containers are never treated as escapes.
    Unknown or malformed text stays visible to the original URL scanner. Nested
    report containers are bounded; no Unicode/percent decoding of URLs occurs.
    """
    if depth >= 16:
        yield text
        return
    value = decoded(text)
    if value is not None:
        for item in strings(value):
            yield from fragments(item, depth + 1)
        return
    offset = 0
    for match in FENCE.finditer(text):
        value = decoded(match['body'])
        if value is None:
            continue
        yield text[offset:match.start()]
        for item in strings(value):
            yield from fragments(item, depth + 1)
        offset = match.end()
    yield text[offset:]
