"""Deterministic passage, query and rank operations, independent of infrastructure."""
from __future__ import annotations
import hashlib
import re
import unicodedata

STOP = set('the a an is are of in on to and or for with what which how why does do can be this that from as at by ve veya bir bu şu ne nasıl neden hangi için ile olan olarak mı mi mu mü nedir nelerdir'.split())


def folded(text: str) -> str:
    # Turkish I is normalized before general Unicode case folding.
    return unicodedata.normalize('NFKC', text).replace('İ', 'i').replace('I', 'ı').casefold()


def query_terms(query: str) -> list[str]:
    terms = re.findall(r'[\w]+(?:[-./][\w]+)*', folded(query), re.UNICODE)
    return list(dict.fromkeys(t for t in terms if t not in STOP and (len(t) > 1 or t.isdigit())))[:16]


def passages(text: str, max_bytes: int = 1600, overlap: int = 160):
    """Exact source slices; bounded UTF-8 bytes leave space for embedding prompts.

    All characters are covered, including code, tables, URLs and fenced blocks.
    Sentence/newline boundaries are preferred; no whitespace normalization.
    """
    start = 0
    while start < len(text):
        end = min(len(text), start + max_bytes)
        while len(text[start:end].encode('utf-8')) > max_bytes:
            end = start + max(1, (end - start) * 9 // 10)
        if end < len(text):
            boundary = max(text.rfind('\n', start + (end-start)*2//3, end), text.rfind('. ', start + (end-start)*2//3, end))
            if boundary >= 0:
                end = boundary + 1
        body = text[start:end]
        yield {'content': body, 'start': start, 'end': end, 'sha256': hashlib.sha256(body.encode()).hexdigest()}
        if end == len(text):
            break
        start = max(start + 1, end - min(overlap, (end - start)//4))


def fuse(rankings: dict[str, list[dict]], k: int = 60) -> list[dict]:
    """Reciprocal rank fusion over channel families.

    The Turkish and English lexical indexes hold identical text and differ only in
    their analyzer, so a document found by both is one piece of evidence rather
    than two votes. Halving each of them expressed that, but it also halved a
    document that only one analyzer could match - exactly the exact-keyword case
    hybrid retrieval exists to serve. Collapsing them into one family at their
    best rank keeps the first property and removes the second.
    """
    merged = {}
    best = {}
    for channel, rows in rankings.items():
        family = 'lexical' if channel.startswith('bm25_') else channel
        seen = set()
        for rank, row in enumerate(rows, 1):
            key = str(row['id'])
            if key in seen:
                continue
            seen.add(key)
            hit = merged.setdefault(key, {**row, 'rrf_score': 0.0, 'channels': [], 'ranks': {}})
            hit['channels'].append(channel)
            hit['ranks'][channel] = rank
            slot = (family, key)
            if rank < best.get(slot, rank+1):
                best[slot] = rank
    for (_, key), rank in best.items():
        merged[key]['rrf_score'] += 1.0/(k+rank)
    return sorted(merged.values(), key=lambda r: (-r['rrf_score'], str(r['id'])))


def exact_match(query: str, row: dict) -> bool:
    content = folded(row['content'] + '\n' + row.get('title', ''))
    quoted = re.findall(r'"([^"\n]{2,})"', query)
    identifiers = re.findall(r'\b[\w]+[-./][\w./-]*\d[\w./-]*\b|\b\d{2,}(?:[./-]\d+)*\b', query)
    protected = quoted + identifiers
    return bool(protected) and all(re.search(r'(?<!\w)' + re.escape(folded(term)) + r'(?!\w)', content) for term in protected)


def group_results(rows: list[dict], limit: int, max_passages: int = 3) -> list[dict]:
    """Diversity by original document; duplicates never count as independent evidence."""
    result = {}
    for row in rows:
        key = str(row['doc_id'])
        entry = result.setdefault(key, {
            'id': key, 'parent_id': str(row['parent_id']), 'title': row['title'],
            'final_score': row.get('rerank_score', row['rrf_score']),
            'score_kind': 'reranker' if 'rerank_score' in row else 'rrf',
            'matches': [], 'passages': [], 'channels': [],
        })
        entry['channels'] = sorted(set(entry['channels']) | set(row['channels']))
        if len(entry['matches']) < max_passages and row['content'] not in entry['matches']:
            entry['matches'].append(row['content'])
            entry['passages'].append({k: row[k] for k in ('id', 'start', 'end', 'sha256', 'content')})
    return list(result.values())[:limit]


def diversify(rows: list[dict], max_per_document: int = 3) -> list[dict]:
    """Reserve reranker slots for different documents before additional passages."""
    groups = {}
    for row in rows:
        groups.setdefault(row['doc_id'], []).append(row)
    front = [values[n] for n in range(max_per_document) for values in groups.values() if len(values)>n]
    chosen = {r['id'] for r in front}
    return front + [r for r in rows if r['id'] not in chosen]
