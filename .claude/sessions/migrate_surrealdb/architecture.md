# SurrealDB Migration Architecture

## High-Level Overview

### Before Migration
```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                          Application Layer                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  FastAPI Services  │  Streamlit Pages  │  Domain Models (base.py, models.py, notebook.py)  │  Migration System  │  Utils (surreal_clean)  │  Background Tasks        │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                        Synchronous Database Layer                                                                                │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  repository.py: repo_query, repo_create, repo_upsert, repo_update, repo_delete, repo_relate  │  migrate.py: MigrationManager (sync)  │  @contextmanager              │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                       sdblpy (SurrealSyncConnection)                                                                             │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                           SurrealDB Database                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### After Migration
```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                          Application Layer                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  FastAPI Services  │  Streamlit Pages (nest_asyncio)  │  Domain Models (async/await)  │  Migration System (async)  │  Background Tasks (async)             │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                        Asynchronous Database Layer                                                                               │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  new.py: repo_query, repo_create, repo_upsert, repo_update, repo_delete, repo_relate, repo_insert  │  migrate.py: AsyncMigrationManager  │  @asynccontextmanager    │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                       surrealdb (AsyncSurreal)                                                                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                           SurrealDB Database                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Affected Components and Dependencies

### 1. Database Layer (Core Infrastructure)

#### 1.1 Repository Replacement
- **Replace**: `open_notebook/database/repository.py`
- **With**: `open_notebook/database/new.py` (rename to `repository.py`)
- **Changes**: 
  - All functions become async
  - Connection management via `@asynccontextmanager`
  - Improved error handling and logging
  - Automatic timestamp management
  - Built-in RecordID parsing

#### 1.2 Migration System Redesign
- **Replace**: `open_notebook/database/migrate.py`
- **With**: New async migration system based on sblpy patterns
- **Components**:
  - `AsyncMigrationManager` - Main migration controller
  - `AsyncMigration` - Individual migration wrapper
  - `AsyncMigrationRunner` - Migration execution engine
  - `db_processes` - Database version management
  - `sql_adapter` - SQL file processing

### 2. Domain Models (Data Access Layer)

#### 2.1 Base Model (`open_notebook/domain/base.py`)
- **Critical Changes**:
  - All methods become async: `get_all()`, `get()`, `save()`, `delete()`, `relate()`
  - `RecordModel.__init__()` and `update()` become async
  - Add proper async context handling
  - Maintain backward compatibility for method signatures

#### 2.2 Domain Models (`open_notebook/domain/models.py`)
- **Changes**:
  - `Model.get_models_by_type()` becomes async
  - All model instantiation becomes async

#### 2.3 Notebook Models (`open_notebook/domain/notebook.py`)
- **Complex Changes**:
  - All property getters become async methods
  - `text_search()` and `vector_search()` functions become async
  - Complex query methods require async handling
  - Embedding and vectorization operations become async

### 3. Application Layer

#### 3.1 FastAPI Services (API Layer)
- **Files**: `api/models_service.py`, `api/notebook_service.py`, `api/notes_service.py`
- **Changes**: 
  - All endpoints remain async (FastAPI already supports this)
  - Add proper async/await for database calls
  - Update error handling for async operations

#### 3.2 FastAPI Routers
- **Directory**: `api/routers/`
- **Changes**:
  - Update all route handlers to properly await database operations
  - Ensure proper async context management
  - Add async error handling

#### 3.3 Streamlit Pages (UI Layer)
- **Directory**: `pages/`
- **Changes**:
  - Import and apply `nest_asyncio` at the top of each file
  - Wrap async database calls with `asyncio.run()`
  - Maintain synchronous interface for Streamlit components
  - Add proper error handling for async operations

### 4. Environment Configuration

#### 4.1 Environment Variable Compatibility
- **Current**: `SURREAL_ADDRESS`, `SURREAL_PORT`, `SURREAL_USER`, `SURREAL_PASS`
- **New**: `SURREAL_URL`, `SURREAL_USER`, `SURREAL_PASSWORD`
- **Strategy**: 
  - Check for new format first
  - Fall back to old format and convert
  - Provide clear migration documentation

#### 4.2 Connection String Conversion
```python
# Old format detection and conversion
if not os.getenv("SURREAL_URL") and os.getenv("SURREAL_ADDRESS"):
    url = f"http://{os.getenv('SURREAL_ADDRESS')}:{os.getenv('SURREAL_PORT')}"
    os.environ["SURREAL_URL"] = url
    os.environ["SURREAL_PASSWORD"] = os.getenv("SURREAL_PASS")
```

## External Dependencies

### 4.1 New Dependencies
- `surrealdb` - Official SurrealDB Python client (already added)
- `nest_asyncio` - For Streamlit async compatibility

### 4.2 Removed Dependencies
- `sdblpy` - Custom lightweight client (remove from dependencies)

### 4.3 Updated Utilities
- Remove `surreal_clean` function from `utils.py` (no longer needed)
- Update any code that depends on `surreal_clean`

## Implementation Patterns

### 5.1 Async Context Management
```python
# Old pattern
@contextmanager
def db_connection():
    connection = SurrealSyncConnection(...)
    try:
        yield connection
    finally:
        connection.socket.close()

# New pattern
@asynccontextmanager
async def db_connection():
    db = AsyncSurreal(os.environ["SURREAL_URL"])
    await db.signin({"username": ..., "password": ...})
    await db.use(namespace, database)
    try:
        yield db
    finally:
        await db.close()
```

### 5.2 Domain Model Async Conversion
```python
# Old pattern
class RecordModel:
    def save(self):
        if hasattr(self, 'id') and self.id:
            return repo_update(self.id, self.model_dump())
        else:
            return repo_create(self.table_name, self.model_dump())

# New pattern
class RecordModel:
    async def save(self):
        if hasattr(self, 'id') and self.id:
            return await repo_update(self.table_name, self.id, self.model_dump())
        else:
            return await repo_create(self.table_name, self.model_dump())
```

### 5.3 SQL Safety and Parameterized Queries
```python
# Old pattern (SQL injection risk)
srcs = repo_query(f"""
    select * omit source.full_text from (
    select in as source from reference where out={self.id}
    fetch source
) order by source.updated desc
""")

# New pattern (SQL safe with parameters)
srcs = await repo_query("""
    select * omit source.full_text from (
    select in as source from reference where out=$id
    fetch source
) order by source.updated desc
""", {"id": ensure_record_id(self.id)})
```

### 5.4 Streamlit Async Integration
```python
# Pattern for Streamlit pages
import nest_asyncio
nest_asyncio.apply()

import asyncio
import streamlit as st

async def load_data():
    return await some_async_database_call()

# In Streamlit app
data = asyncio.run(load_data())
st.write(data)
```

## Migration System Architecture

### 6.1 Async Migration Components

#### AsyncMigrationManager
- Manages database connections and migration state
- Handles version checking and migration execution
- Provides async interface for all migration operations

#### AsyncMigration
- Wraps individual migration files
- Supports creation from files, strings, or lists
- Handles async execution with proper error handling

#### AsyncMigrationRunner
- Executes migrations in sequence
- Manages version bumping and rollbacks
- Provides incremental migration capabilities

### 6.2 Migration Database Schema
```sql
-- Migration tracking table (same as sblpy)
CREATE TABLE _sbl_migrations;
DEFINE FIELD version ON TABLE _sbl_migrations TYPE int;
DEFINE FIELD applied_at ON TABLE _sbl_migrations TYPE datetime;
```

### 6.3 Migration File Structure
```
migrations/
├── 1.surrealql    # Up migration
├── 1_down.surrealql    # Down migration
├── 2.surrealql
├── 2_down.surrealql
└── ...
```

## Constraints and Assumptions

### 7.1 Technical Constraints
- Maintain exact same API interface for all domain models
- Preserve all existing functionality
- Support both old and new environment variable formats
- Ensure Streamlit pages continue to work without major changes

### 7.2 Performance Assumptions
- Async operations will improve overall performance
- Connection pooling will be handled by the official client
- Memory usage may increase slightly due to async overhead

### 7.3 Compatibility Assumptions
- All existing SurrealQL queries will continue to work
- RecordID handling will be improved but maintain compatibility
- Migration files will not need to be modified

## Trade-offs and Alternatives

### 8.1 Chosen Approach: Complete Async Migration
**Pros**:
- Modern, future-proof architecture
- Better performance and scalability
- Official client support and features
- Cleaner code with better error handling

**Cons**:
- Requires updating all database-related code
- Potential for introducing bugs during conversion
- Learning curve for async patterns

### 8.2 Alternative: Hybrid Approach
**Pros**:
- Gradual migration possible
- Lower risk of breaking changes
- Easier to test incrementally

**Cons**:
- More complex codebase during transition
- Potential for inconsistencies
- Longer development time

### 8.3 Alternative: Wrapper Layer
**Pros**:
- Minimal changes to existing code
- Quick implementation
- Easy rollback

**Cons**:
- Performance overhead
- Doesn't leverage async benefits
- Technical debt accumulation

## Implementation Files

### 8.1 Files to Edit
1. `open_notebook/database/new.py` → `open_notebook/database/repository.py`
2. `open_notebook/database/migrate.py` (complete rewrite)
3. `open_notebook/domain/base.py` (async conversion)
4. `open_notebook/domain/models.py` (async conversion)
5. `open_notebook/domain/notebook.py` (async conversion)
6. All files in `api/` directory (~10 files)
7. All files in `pages/` directory (~15 files)
8. All files in `pages/stream_app/` directory (~10 files)
9. `open_notebook/utils.py` (remove surreal_clean)

### 8.2 Files to Create
1. `open_notebook/database/async_migrate.py` (new async migration system)
2. Environment compatibility helpers (if needed)

### 8.3 Files to Remove
1. `open_notebook/database/repository.py` (old version)
2. References to `sdblpy` in `pyproject.toml`

## Risk Mitigation

### 9.1 Data Safety
- Test all operations on development database first
- Backup production database before migration
- Verify all CRUD operations work correctly

### 9.2 Code Quality
- Comprehensive manual testing after each component
- Verify all async/await patterns are correct
- Test error handling and edge cases

### 9.3 Performance
- Monitor database connection efficiency
- Test with realistic data volumes
- Verify memory usage patterns

## Success Metrics

1. **Functionality**: All existing features work identically
2. **Performance**: No degradation in response times
3. **Reliability**: Proper error handling and logging
4. **Maintainability**: Clean async/await patterns throughout
5. **Compatibility**: Environment variables work in both formats
6. **Migration**: Database migrations work reliably

This architecture provides a comprehensive roadmap for migrating from the lightweight sdblpy client to the official SurrealDB Python client while maintaining all existing functionality and improving the overall system architecture.