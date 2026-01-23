# Database Migration Plan: SurrealDB → SQLite

## Executive Summary

This document outlines a comprehensive plan to migrate Open Notebook from SurrealDB to SQLite. The migration involves replacing a graph database with vector search capabilities with a relational database, requiring careful consideration of vector search alternatives, full-text search implementation, and relationship modeling.

**Estimated Scope**: ~40-50 files affected, including migrations, domain models, repository layer, and API services.

---

## Table of Contents

1. [Motivation & Trade-offs](#1-motivation--trade-offs)
2. [Technology Decisions](#2-technology-decisions)
3. [Schema Design](#3-schema-design)
4. [Migration Phases](#4-migration-phases)
5. [Detailed Implementation Tasks](#5-detailed-implementation-tasks)
6. [Testing Strategy](#6-testing-strategy)
7. [Rollback Plan](#7-rollback-plan)
8. [Risk Assessment](#8-risk-assessment)

---

## 1. Motivation & Trade-offs

### Why Migrate to SQLite?

| Benefit | Description |
|---------|-------------|
| **Simplicity** | No separate database service; single file storage |
| **Portability** | Easy backup/restore, file-based deployment |
| **Maturity** | Battle-tested, widely supported, extensive tooling |
| **Reduced Dependencies** | Eliminates SurrealDB service from docker-compose |
| **Lower Resource Usage** | No separate database process consuming memory |

### What We Lose

| Feature | SurrealDB | SQLite Replacement |
|---------|-----------|-------------------|
| **Native Vector Search** | Built-in cosine similarity | Requires `sqlite-vec` extension |
| **Graph Relationships** | First-class RELATE syntax | Join tables with foreign keys |
| **BM25 Full-Text** | Custom analyzer, highlights | FTS5 (different tokenization) |
| **Async Driver** | Native async | `aiosqlite` wrapper |
| **Event Triggers** | SurrealQL DEFINE EVENT | SQLite triggers (limited) |
| **RecordID Type** | Native `table:id` format | String or integer IDs |

---

## 2. Technology Decisions

### 2.1 SQLite Extension for Vector Search

**Recommended: `sqlite-vec`**

```
pip install sqlite-vec
```

**Why sqlite-vec:**
- Pure Python/C extension, no external dependencies
- Supports cosine similarity, dot product, L2 distance
- Maintains vector data in virtual tables
- Active development, good performance

**Alternative considered:** `sqlite-vss` (uses Faiss, heavier dependency)

### 2.2 Full-Text Search

**Use: SQLite FTS5**

```sql
CREATE VIRTUAL TABLE source_fts USING fts5(
    title,
    full_text,
    content='source',
    content_rowid='id',
    tokenize='porter unicode61'
);
```

**Note:** FTS5 uses different tokenization than SurrealDB's custom analyzer. Search results may differ slightly.

### 2.3 Async Database Access

**Use: `aiosqlite`**

```python
import aiosqlite

async with aiosqlite.connect("database.db") as db:
    async with db.execute("SELECT * FROM notebook") as cursor:
        rows = await cursor.fetchall()
```

### 2.4 Connection Pooling

**Use: Connection pool for better concurrency**

```python
from contextlib import asynccontextmanager
import aiosqlite

class ConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.pool = asyncio.Queue(maxsize=max_connections)

    @asynccontextmanager
    async def acquire(self):
        conn = await self.pool.get()
        try:
            yield conn
        finally:
            await self.pool.put(conn)
```

### 2.5 Migration Framework

**Use: `alembic`** (industry standard for SQLAlchemy)

Or implement a simple version-tracked migration system similar to the existing `AsyncMigrationManager`.

---

## 3. Schema Design

### 3.1 Core Tables

```sql
-- Notebooks
CREATE TABLE notebook (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    archived INTEGER DEFAULT 0,
    created TEXT DEFAULT (datetime('now')),
    updated TEXT DEFAULT (datetime('now'))
);

-- Sources
CREATE TABLE source (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    url TEXT,
    title TEXT,
    topics TEXT,  -- JSON array
    full_text TEXT,
    command_id INTEGER,
    created TEXT DEFAULT (datetime('now')),
    updated TEXT DEFAULT (datetime('now'))
);

-- Notes
CREATE TABLE note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    note_type TEXT CHECK(note_type IN ('human', 'ai')),
    content TEXT,
    embedding BLOB,  -- Serialized float array
    created TEXT DEFAULT (datetime('now')),
    updated TEXT DEFAULT (datetime('now'))
);

-- Source Embeddings (chunks)
CREATE TABLE source_embedding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    chunk_order INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB,  -- Serialized float array
    FOREIGN KEY (source_id) REFERENCES source(id) ON DELETE CASCADE
);

-- Source Insights
CREATE TABLE source_insight (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    insight_type TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB,
    created TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (source_id) REFERENCES source(id) ON DELETE CASCADE
);

-- Chat Sessions
CREATE TABLE chat_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    model_override TEXT,
    created TEXT DEFAULT (datetime('now')),
    updated TEXT DEFAULT (datetime('now'))
);

-- Transformations
CREATE TABLE transformation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    prompt TEXT NOT NULL,
    apply_default INTEGER DEFAULT 0,
    created TEXT DEFAULT (datetime('now')),
    updated TEXT DEFAULT (datetime('now'))
);
```

### 3.2 Relationship Tables (Replacing Graph Edges)

```sql
-- source -> notebook (was: reference relation)
CREATE TABLE source_notebook (
    source_id INTEGER NOT NULL,
    notebook_id INTEGER NOT NULL,
    created TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (source_id, notebook_id),
    FOREIGN KEY (source_id) REFERENCES source(id) ON DELETE CASCADE,
    FOREIGN KEY (notebook_id) REFERENCES notebook(id) ON DELETE CASCADE
);

-- note -> notebook (was: artifact relation)
CREATE TABLE note_notebook (
    note_id INTEGER NOT NULL,
    notebook_id INTEGER NOT NULL,
    created TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (note_id, notebook_id),
    FOREIGN KEY (note_id) REFERENCES note(id) ON DELETE CASCADE,
    FOREIGN KEY (notebook_id) REFERENCES notebook(id) ON DELETE CASCADE
);

-- chat_session -> notebook/source (was: refers_to relation)
CREATE TABLE chat_session_reference (
    chat_session_id INTEGER NOT NULL,
    notebook_id INTEGER,
    source_id INTEGER,
    created TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (chat_session_id) REFERENCES chat_session(id) ON DELETE CASCADE,
    FOREIGN KEY (notebook_id) REFERENCES notebook(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES source(id) ON DELETE CASCADE,
    CHECK (notebook_id IS NOT NULL OR source_id IS NOT NULL)
);
```

### 3.3 Configuration Tables (Singleton Records)

```sql
-- Content Settings
CREATE TABLE content_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton
    default_content_processing_engine_doc TEXT DEFAULT 'auto',
    default_embedding_option TEXT DEFAULT 'ask',
    auto_delete_files TEXT DEFAULT 'no',
    youtube_preferred_languages TEXT DEFAULT '[]',  -- JSON array
    updated TEXT DEFAULT (datetime('now'))
);

-- Default Prompts
CREATE TABLE default_prompts (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton
    transformation_instructions TEXT,
    updated TEXT DEFAULT (datetime('now'))
);
```

### 3.4 Vector Search with sqlite-vec

```sql
-- Create vector index for source embeddings
CREATE VIRTUAL TABLE source_embedding_vec USING vec0(
    embedding float[1536]  -- Adjust dimension based on model
);

-- Create vector index for notes
CREATE VIRTUAL TABLE note_vec USING vec0(
    embedding float[1536]
);

-- Create vector index for insights
CREATE VIRTUAL TABLE source_insight_vec USING vec0(
    embedding float[1536]
);
```

### 3.5 Full-Text Search Tables

```sql
-- FTS5 for sources
CREATE VIRTUAL TABLE source_fts USING fts5(
    title,
    full_text,
    content='source',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- FTS5 for notes
CREATE VIRTUAL TABLE note_fts USING fts5(
    title,
    content,
    content='note',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- FTS5 for source embeddings (chunks)
CREATE VIRTUAL TABLE source_embedding_fts USING fts5(
    content,
    content='source_embedding',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- FTS5 for insights
CREATE VIRTUAL TABLE source_insight_fts USING fts5(
    content,
    content='source_insight',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER source_ai AFTER INSERT ON source BEGIN
    INSERT INTO source_fts(rowid, title, full_text) VALUES (new.id, new.title, new.full_text);
END;

CREATE TRIGGER source_ad AFTER DELETE ON source BEGIN
    INSERT INTO source_fts(source_fts, rowid, title, full_text) VALUES ('delete', old.id, old.title, old.full_text);
END;

CREATE TRIGGER source_au AFTER UPDATE ON source BEGIN
    INSERT INTO source_fts(source_fts, rowid, title, full_text) VALUES ('delete', old.id, old.title, old.full_text);
    INSERT INTO source_fts(rowid, title, full_text) VALUES (new.id, new.title, new.full_text);
END;
```

### 3.6 Indexes

```sql
-- Performance indexes
CREATE INDEX idx_source_embedding_source ON source_embedding(source_id);
CREATE INDEX idx_source_insight_source ON source_insight(source_id);
CREATE INDEX idx_source_notebook_notebook ON source_notebook(notebook_id);
CREATE INDEX idx_note_notebook_notebook ON note_notebook(notebook_id);
CREATE INDEX idx_chat_session_ref_notebook ON chat_session_reference(notebook_id);
CREATE INDEX idx_chat_session_ref_source ON chat_session_reference(source_id);
```

---

## 4. Migration Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up SQLite infrastructure
- [ ] Create new repository layer
- [ ] Implement connection management
- [ ] Write schema migrations

### Phase 2: Domain Models (Week 2)
- [ ] Adapt ObjectModel base class
- [ ] Adapt RecordModel base class
- [ ] Update all domain models
- [ ] Implement relationship methods

### Phase 3: Search Implementation (Week 3)
- [ ] Implement sqlite-vec integration
- [ ] Port vector_search function
- [ ] Implement FTS5 search
- [ ] Port text_search function

### Phase 4: API & Services (Week 4)
- [ ] Update API routes
- [ ] Update service layer
- [ ] Update command handlers
- [ ] Update LangGraph workflows

### Phase 5: Testing & Validation (Week 5)
- [ ] Port all existing tests
- [ ] Write migration-specific tests
- [ ] Performance benchmarking
- [ ] User acceptance testing

### Phase 6: Data Migration & Deployment (Week 6)
- [ ] Write data migration scripts
- [ ] Test migration on sample data
- [ ] Document deployment process
- [ ] Execute production migration

---

## 5. Detailed Implementation Tasks

### 5.1 Database Infrastructure

#### 5.1.1 Create SQLite Repository Module

**File: `open_notebook/database/sqlite_repository.py`**

```python
import aiosqlite
import sqlite_vec
import json
import struct
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
from pathlib import Path

DATABASE_PATH = Path(os.getenv("SQLITE_DB_PATH", "/data/sqlite-db/open_notebook.db"))

def serialize_embedding(embedding: List[float]) -> bytes:
    """Serialize embedding to bytes for storage."""
    return struct.pack(f'{len(embedding)}f', *embedding)

def deserialize_embedding(data: bytes) -> List[float]:
    """Deserialize embedding from bytes."""
    count = len(data) // 4
    return list(struct.unpack(f'{count}f', data))

@asynccontextmanager
async def db_connection():
    """Async context manager for database connections."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA journal_mode = WAL")

    # Load sqlite-vec extension
    await db.enable_load_extension(True)
    await db.load_extension(sqlite_vec.loadable_path())

    try:
        yield db
    finally:
        await db.close()

async def repo_query(query: str, params: tuple = ()) -> List[Dict]:
    """Execute a query and return results as dicts."""
    async with db_connection() as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def repo_create(table: str, data: Dict) -> Dict:
    """Insert a new record and return it with ID."""
    async with db_connection() as db:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        cursor = await db.execute(query, tuple(data.values()))
        await db.commit()

        # Return the created record
        result = await db.execute(f"SELECT * FROM {table} WHERE id = ?", (cursor.lastrowid,))
        row = await result.fetchone()
        return dict(row)

async def repo_update(table: str, id: int, data: Dict) -> Dict:
    """Update a record by ID."""
    async with db_connection() as db:
        data["updated"] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE id = ?"

        await db.execute(query, (*data.values(), id))
        await db.commit()

        result = await db.execute(f"SELECT * FROM {table} WHERE id = ?", (id,))
        row = await result.fetchone()
        return dict(row)

async def repo_delete(table: str, id: int) -> bool:
    """Delete a record by ID."""
    async with db_connection() as db:
        await db.execute(f"DELETE FROM {table} WHERE id = ?", (id,))
        await db.commit()
        return True

async def repo_relate(source_table: str, source_id: int,
                      target_table: str, target_id: int,
                      relation_table: str) -> bool:
    """Create a relationship between two records."""
    async with db_connection() as db:
        query = f"""
            INSERT OR IGNORE INTO {relation_table}
            ({source_table}_id, {target_table}_id)
            VALUES (?, ?)
        """
        await db.execute(query, (source_id, target_id))
        await db.commit()
        return True
```

#### 5.1.2 Update Migration System

**File: `open_notebook/database/sqlite_migrate.py`**

```python
import aiosqlite
from pathlib import Path
from loguru import logger

MIGRATIONS_DIR = Path(__file__).parent / "sqlite_migrations"

class SQLiteMigrationManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get_current_version(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(
                    "SELECT version FROM _migrations ORDER BY version DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
            except aiosqlite.OperationalError:
                return 0

    async def run_migrations(self):
        current = await self.get_current_version()
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        async with aiosqlite.connect(self.db_path) as db:
            # Ensure migrations table exists
            await db.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT DEFAULT (datetime('now'))
                )
            """)

            for migration_file in migration_files:
                version = int(migration_file.stem.split("_")[0])
                if version > current:
                    logger.info(f"Running migration {migration_file.name}")
                    sql = migration_file.read_text()
                    await db.executescript(sql)
                    await db.execute(
                        "INSERT INTO _migrations (version) VALUES (?)",
                        (version,)
                    )
                    await db.commit()
                    logger.info(f"Migration {version} completed")
```

### 5.2 Domain Model Updates

#### 5.2.1 Update Base Classes

**File: `open_notebook/domain/base.py`**

Key changes:
- Replace `RecordID` handling with integer IDs
- Change `table:id` format to just integer `id`
- Update `get()`, `save()`, `delete()` to use new repository
- Replace `relate()` with join table operations

```python
# Before (SurrealDB)
class ObjectModel:
    async def save(self):
        if self.id:
            return await repo_update(self.table_name, self.id, self.model_dump())
        else:
            result = await repo_create(self.table_name, self.model_dump())
            self.id = result["id"]  # e.g., "source:abc123"
            return result

# After (SQLite)
class ObjectModel:
    async def save(self):
        data = self.model_dump(exclude={"id"})
        if self.id:
            return await repo_update(self.table_name, self.id, data)
        else:
            result = await repo_create(self.table_name, data)
            self.id = result["id"]  # e.g., 42
            return result
```

#### 5.2.2 Update Notebook Model

**File: `open_notebook/domain/notebook.py`**

```python
# Before (SurrealDB)
async def get_sources(self) -> List["Source"]:
    result = await repo_query(
        "SELECT in as source FROM reference WHERE out=$id FETCH source",
        {"id": self.id}
    )
    return [Source(**r["source"]) for r in result]

# After (SQLite)
async def get_sources(self) -> List["Source"]:
    result = await repo_query("""
        SELECT s.* FROM source s
        JOIN source_notebook sn ON s.id = sn.source_id
        WHERE sn.notebook_id = ?
    """, (self.id,))
    return [Source(**r) for r in result]
```

#### 5.2.3 Update Source Model

```python
# Before (SurrealDB)
async def add_to_notebook(self, notebook_id: str):
    await repo_relate(self.id, "reference", notebook_id)

# After (SQLite)
async def add_to_notebook(self, notebook_id: int):
    await repo_query("""
        INSERT OR IGNORE INTO source_notebook (source_id, notebook_id)
        VALUES (?, ?)
    """, (self.id, notebook_id))
```

### 5.3 Search Implementation

#### 5.3.1 Vector Search Function

**File: `open_notebook/database/sqlite_search.py`**

```python
async def vector_search(
    query_embedding: List[float],
    match_count: int = 10,
    search_sources: bool = True,
    search_notes: bool = True,
    min_similarity: float = 0.2
) -> List[Dict]:
    """
    Perform vector similarity search using sqlite-vec.
    """
    results = []
    query_blob = serialize_embedding(query_embedding)

    async with db_connection() as db:
        if search_sources:
            # Search source embeddings
            cursor = await db.execute("""
                SELECT
                    se.id,
                    se.source_id,
                    se.content,
                    vec_distance_cosine(sev.embedding, ?) as distance
                FROM source_embedding se
                JOIN source_embedding_vec sev ON se.id = sev.rowid
                WHERE distance <= ?
                ORDER BY distance ASC
                LIMIT ?
            """, (query_blob, 1 - min_similarity, match_count))

            rows = await cursor.fetchall()
            for row in rows:
                results.append({
                    "type": "source_embedding",
                    "id": row["id"],
                    "source_id": row["source_id"],
                    "content": row["content"],
                    "similarity": 1 - row["distance"]
                })

            # Search source insights
            cursor = await db.execute("""
                SELECT
                    si.id,
                    si.source_id,
                    si.insight_type,
                    si.content,
                    vec_distance_cosine(siv.embedding, ?) as distance
                FROM source_insight si
                JOIN source_insight_vec siv ON si.id = siv.rowid
                WHERE distance <= ?
                ORDER BY distance ASC
                LIMIT ?
            """, (query_blob, 1 - min_similarity, match_count))

            rows = await cursor.fetchall()
            for row in rows:
                results.append({
                    "type": "source_insight",
                    "id": row["id"],
                    "source_id": row["source_id"],
                    "insight_type": row["insight_type"],
                    "content": row["content"],
                    "similarity": 1 - row["distance"]
                })

        if search_notes:
            cursor = await db.execute("""
                SELECT
                    n.id,
                    n.title,
                    n.content,
                    vec_distance_cosine(nv.embedding, ?) as distance
                FROM note n
                JOIN note_vec nv ON n.id = nv.rowid
                WHERE distance <= ?
                ORDER BY distance ASC
                LIMIT ?
            """, (query_blob, 1 - min_similarity, match_count))

            rows = await cursor.fetchall()
            for row in rows:
                results.append({
                    "type": "note",
                    "id": row["id"],
                    "title": row["title"],
                    "content": row["content"],
                    "similarity": 1 - row["distance"]
                })

    # Sort by similarity and limit
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:match_count]
```

#### 5.3.2 Full-Text Search Function

```python
async def text_search(
    query_text: str,
    match_count: int = 10,
    search_sources: bool = True,
    search_notes: bool = True
) -> List[Dict]:
    """
    Perform full-text search using FTS5.
    """
    results = []

    async with db_connection() as db:
        if search_sources:
            # Search source titles and full_text
            cursor = await db.execute("""
                SELECT
                    s.id,
                    s.title,
                    snippet(source_fts, 1, '<mark>', '</mark>', '...', 64) as snippet,
                    bm25(source_fts) as rank
                FROM source_fts
                JOIN source s ON source_fts.rowid = s.id
                WHERE source_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query_text, match_count))

            rows = await cursor.fetchall()
            for row in rows:
                results.append({
                    "type": "source",
                    "id": row["id"],
                    "title": row["title"],
                    "snippet": row["snippet"],
                    "score": -row["rank"]  # BM25 returns negative scores
                })

            # Search source embeddings (chunks)
            cursor = await db.execute("""
                SELECT
                    se.id,
                    se.source_id,
                    snippet(source_embedding_fts, 0, '<mark>', '</mark>', '...', 64) as snippet,
                    bm25(source_embedding_fts) as rank
                FROM source_embedding_fts
                JOIN source_embedding se ON source_embedding_fts.rowid = se.id
                WHERE source_embedding_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query_text, match_count))

            rows = await cursor.fetchall()
            for row in rows:
                results.append({
                    "type": "source_embedding",
                    "id": row["id"],
                    "source_id": row["source_id"],
                    "snippet": row["snippet"],
                    "score": -row["rank"]
                })

        if search_notes:
            cursor = await db.execute("""
                SELECT
                    n.id,
                    n.title,
                    snippet(note_fts, 1, '<mark>', '</mark>', '...', 64) as snippet,
                    bm25(note_fts) as rank
                FROM note_fts
                JOIN note n ON note_fts.rowid = n.id
                WHERE note_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query_text, match_count))

            rows = await cursor.fetchall()
            for row in rows:
                results.append({
                    "type": "note",
                    "id": row["id"],
                    "title": row["title"],
                    "snippet": row["snippet"],
                    "score": -row["rank"]
                })

    # Sort by score and limit
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:match_count]
```

### 5.4 Files to Modify

| File | Changes Required |
|------|-----------------|
| `open_notebook/database/repository.py` | Replace with SQLite implementation |
| `open_notebook/database/async_migrate.py` | Replace with SQLite migration system |
| `open_notebook/database/migrations/*.surrealql` | Convert to `.sql` files |
| `open_notebook/domain/base.py` | Update ID handling, remove RecordID |
| `open_notebook/domain/notebook.py` | Update all relationship queries |
| `open_notebook/domain/content_settings.py` | Update singleton pattern |
| `open_notebook/domain/transformation.py` | Minor query updates |
| `open_notebook/domain/models.py` | Update model config query |
| `open_notebook/domain/podcast.py` | Update relationship queries |
| `api/routers/search.py` | Update search function calls |
| `api/routers/notebook.py` | Update queries |
| `api/routers/source.py` | Update queries |
| `api/routers/note.py` | Update queries |
| `api/routers/chat.py` | Update queries |
| `api/main.py` | Update startup migration call |
| `commands/embedding_commands.py` | Update embedding storage |
| `docker-compose.yaml` | Remove SurrealDB service |
| `requirements.txt` / `pyproject.toml` | Add aiosqlite, sqlite-vec; remove surrealdb |
| `tests/test_*.py` | Update all database tests |

### 5.5 Data Migration Script

**File: `scripts/migrate_surreal_to_sqlite.py`**

```python
#!/usr/bin/env python3
"""
One-time migration script to transfer data from SurrealDB to SQLite.
"""
import asyncio
from surrealdb import AsyncSurreal
import aiosqlite
import json

async def migrate():
    # Connect to both databases
    surreal = AsyncSurreal("ws://localhost:8000/rpc")
    await surreal.signin({"user": "root", "pass": "root"})
    await surreal.use("open_notebook", "open_notebook")

    sqlite = await aiosqlite.connect("/data/sqlite-db/open_notebook.db")

    # Migrate notebooks
    notebooks = await surreal.query("SELECT * FROM notebook")
    for nb in notebooks[0]["result"]:
        await sqlite.execute("""
            INSERT INTO notebook (id, name, description, archived, created, updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            extract_id(nb["id"]),
            nb.get("name"),
            nb.get("description"),
            nb.get("archived", False),
            nb.get("created"),
            nb.get("updated")
        ))

    # Migrate sources
    sources = await surreal.query("SELECT * FROM source")
    for src in sources[0]["result"]:
        asset = src.get("asset", {})
        await sqlite.execute("""
            INSERT INTO source (id, file_path, url, title, topics, full_text, created, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            extract_id(src["id"]),
            asset.get("file_path"),
            asset.get("url"),
            src.get("title"),
            json.dumps(src.get("topics", [])),
            src.get("full_text"),
            src.get("created"),
            src.get("updated")
        ))

    # Migrate relationships (reference -> source_notebook)
    refs = await surreal.query("SELECT in, out FROM reference")
    for ref in refs[0]["result"]:
        await sqlite.execute("""
            INSERT INTO source_notebook (source_id, notebook_id)
            VALUES (?, ?)
        """, (extract_id(ref["in"]), extract_id(ref["out"])))

    # ... continue for all other tables ...

    await sqlite.commit()
    await sqlite.close()
    await surreal.close()

def extract_id(record_id: str) -> int:
    """Extract numeric ID from SurrealDB record ID (e.g., 'source:123' -> 123)."""
    return int(record_id.split(":")[1])

if __name__ == "__main__":
    asyncio.run(migrate())
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

- Test all repository functions in isolation
- Test domain model CRUD operations
- Test relationship creation and querying
- Test search functions with mock embeddings

### 6.2 Integration Tests

- Test API endpoints with SQLite backend
- Test LangGraph workflows with SQLite
- Test embedding command handlers
- Test migration system

### 6.3 Performance Tests

- Benchmark vector search with 10K, 100K, 1M embeddings
- Benchmark FTS5 with large documents
- Compare query latency vs SurrealDB baseline

### 6.4 Migration Tests

- Test data migration script on sample database
- Verify data integrity after migration
- Test rollback procedure

---

## 7. Rollback Plan

### 7.1 Pre-Migration Backup

```bash
# Backup SurrealDB data
surreal export --conn ws://localhost:8000 \
    --user root --pass root \
    --ns open_notebook --db open_notebook \
    backup_$(date +%Y%m%d).surql
```

### 7.2 Rollback Procedure

1. Stop application
2. Restore SurrealDB from backup
3. Revert code changes (git revert or checkout)
4. Restart with SurrealDB configuration
5. Verify functionality

### 7.3 Feature Flags (Optional)

Implement database backend toggle:

```python
DATABASE_BACKEND = os.getenv("DATABASE_BACKEND", "sqlite")  # or "surrealdb"

if DATABASE_BACKEND == "sqlite":
    from open_notebook.database.sqlite_repository import *
else:
    from open_notebook.database.repository import *
```

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Vector search performance degradation | Medium | High | Benchmark early, consider pgvector fallback |
| FTS5 tokenization differences | High | Low | Document differences, adjust queries |
| Data loss during migration | Low | Critical | Multiple backups, staged rollout |
| sqlite-vec compatibility issues | Medium | High | Test across platforms, have fallback |
| Concurrent write contention | Medium | Medium | Use WAL mode, connection pooling |
| Missing SurrealDB features | Low | Medium | Document workarounds before starting |

---

## Appendix A: Dependency Changes

### Remove
```
surrealdb>=1.0.0
```

### Add
```
aiosqlite>=0.19.0
sqlite-vec>=0.1.0
```

---

## Appendix B: Environment Variable Changes

### Remove
```
SURREAL_URL
SURREAL_ADDRESS
SURREAL_PORT
SURREAL_USER
SURREAL_PASSWORD
SURREAL_NAMESPACE
SURREAL_DATABASE
```

### Add
```
SQLITE_DB_PATH=/data/sqlite-db/open_notebook.db
```

---

## Appendix C: Docker Compose Changes

### Remove
```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:latest
    ...
```

### Add
```yaml
volumes:
  sqlite-data:
    driver: local

services:
  api:
    volumes:
      - sqlite-data:/data/sqlite-db
```

---

*Document Version: 1.0*
*Created: January 2026*
*Author: Claude Code Assistant*
