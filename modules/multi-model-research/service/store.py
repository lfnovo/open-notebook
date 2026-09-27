"""Durable run snapshots; all mutation is serialized by the engine lock."""
import json
from pathlib import Path
import aiosqlite

class Store:
    def __init__(self, root: Path):
        self.root=root
        self.db=None
    async def open(self):
        self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.db=await aiosqlite.connect(self.root/'research.sqlite3')
        await self.db.execute('PRAGMA journal_mode=WAL')
        await self.db.execute('PRAGMA synchronous=FULL')
        await self.db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL, created TEXT NOT NULL, data TEXT NOT NULL)')
        await self.db.commit()
        (self.root/'research.sqlite3').chmod(0o600)
    async def close(self):
        await self.db.close()
    async def get(self, run_id):
        async with self.db.execute('SELECT data FROM runs WHERE id=?',(run_id,)) as cursor:row=await cursor.fetchone()
        return json.loads(row[0]) if row else None
    async def by_key(self,key):
        async with self.db.execute('SELECT data FROM runs WHERE idempotency_key=?',(key,)) as cursor:row=await cursor.fetchone()
        return json.loads(row[0]) if row else None
    async def all(self):
        async with self.db.execute('SELECT data FROM runs ORDER BY created DESC') as cursor:rows=await cursor.fetchall()
        return [json.loads(x[0]) for x in rows]
    async def save(self,run):
        await self.db.execute('INSERT INTO runs VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                              (run['id'],run['idempotency_key'],run['created_at'],json.dumps(run,ensure_ascii=False)))
        await self.db.commit()
