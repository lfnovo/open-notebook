"""Bounded writes to derived passages; originals are never modified here."""
import hashlib
import json
import re

MAX_ROWS = 16
MAX_BYTES = 256 * 1024


def batches(rows):
    group = []; size = 2
    for row in rows:
        cost = len(json.dumps(row, ensure_ascii=False, allow_nan=False, default=str).encode()) + 1
        if cost + 2 > MAX_BYTES:
            raise ValueError('One index passage exceeds the bounded write size')
        if group and (len(group) >= MAX_ROWS or size + cost > MAX_BYTES):
            yield group
            group = []; size = 2
        group.append(row); size += cost
    if group:
        yield group


class PassageWriter:
    def __init__(self, query, record):
        self.query, self.record = query, record

    @staticmethod
    def table_name(table):
        if not re.fullmatch(r'hs_p_[a-zA-Z0-9]+', table):
            raise ValueError('Invalid derived index table')
        return table

    def metadata_id(self, table, doc):
        return self.record('hs_document:' + hashlib.sha256((table + doc).encode()).hexdigest())

    async def prune(self, table, where, variables):
        self.table_name(table)
        previous = None
        while True:
            ids = await self.query(f'SELECT VALUE id FROM {table} WHERE {where} LIMIT {MAX_ROWS}', variables)
            if not ids:
                return
            keys = [str(i) for i in ids]
            if len(keys) > MAX_ROWS or len(set(keys)) != len(keys) or keys == previous or any(not k.startswith(table + ':') for k in keys):
                raise ValueError('Invalid or non-progressing bounded index cleanup')
            await self.query('DELETE $ids RETURN NONE;', {'ids': [self.record(k) for k in keys]})
            previous = keys

    async def cleanup(self, table, doc, content_hash):
        await self.prune(table, 'doc_id=$doc AND doc_hash!=$hash', {'doc': doc, 'hash': content_hash})
        await self.query('UPDATE $record SET cleanup_pending=false WHERE doc_hash=$hash RETURN NONE;',
                         {'record': self.metadata_id(table, doc), 'hash': content_hash})

    async def replace(self, table, doc, content_hash, rows):
        self.table_name(table)
        identifiers = [str(row['id']) for row in rows]
        if (len(set(identifiers)) != len(rows) or any(not ident.startswith(table + ':') for ident in identifiers)
                or any(row.get('doc_id') != doc or row.get('doc_hash') != content_hash
                       or row.get('part') != n for n, row in enumerate(rows))):
            raise ValueError('Index payload identity or coverage changed')
        # Validate every size before writing even the first group.
        groups = list(batches(rows))
        for group in groups:
            await self.query(f'INSERT IGNORE INTO {table} $rows RETURN NONE;', {'rows': group})
            persisted = await self.query('SELECT id,doc_id,doc_hash,part FROM $ids;',
                                         {'ids': [r['id'] for r in group]})
            observed = {str(r['id']): (r.get('doc_id'), r.get('doc_hash'), r.get('part')) for r in persisted}
            expected = {str(r['id']): (doc, content_hash, r['part']) for r in group}
            if len(persisted) != len(group) or observed != expected:
                raise ValueError('A staged index batch was not preserved completely')
        # Publish only a complete document. Readers require this matching marker.
        await self.query(f'''-- publish complete document
            BEGIN TRANSACTION;
            LET $actual = (SELECT count() AS total FROM {table}
                WHERE doc_id=$doc AND doc_hash=$hash GROUP ALL);
            IF ($actual[0].total ?? 0) != $expected {{ THROW 'Incomplete staged index'; }};
            UPSERT $record CONTENT $meta;
            COMMIT TRANSACTION;''', {
                'doc': doc, 'hash': content_hash, 'expected': len(rows),
                'record': self.metadata_id(table, doc),
                'meta': {'doc_id': doc, 'doc_hash': content_hash, 'generation': table,
                         'parts': len(rows), 'cleanup_pending': True}})
        # Old and abandoned versions remain recoverable until publication succeeds.
        await self.cleanup(table, doc, content_hash)
