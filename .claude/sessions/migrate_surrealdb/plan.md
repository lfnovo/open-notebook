# SurrealDB Migration Implementation Plan

## Overview

This plan breaks down the migration from `sdblpy` to the official `surrealdb` Python client into manageable phases of approximately 2 hours each. Each phase is designed to be independent, testable, and builds upon the previous phase.

**Total Estimated Time**: 12-14 hours across 6-7 sessions
**Risk Level**: Medium-High (significant architecture changes)
**Rollback Strategy**: Git branches for each phase

---

## Phase 1: Foundation & Database Layer Migration (2 hours)

### 🎯 Goals
- Replace the synchronous database layer with async implementation
- Create environment variable compatibility layer
- Establish the foundation for all subsequent migrations

### 📁 Files to Change
1. `open_notebook/database/repository.py` - Replace with async version
2. `open_notebook/database/migrate.py` - Create async migration system
3. `pyproject.toml` - Remove sdblpy dependency
4. `.env.example` - Add new environment variable examples

### 🔧 Specific Implementation Steps

#### 1.1 Environment Variable Compatibility
```python
# Add to repository.py or new config.py
def get_database_url():
    """Get database URL with backward compatibility"""
    surreal_url = os.getenv("SURREAL_URL")
    if surreal_url:
        return surreal_url
    
    # Fallback to old format - WebSocket URL format
    address = os.getenv("SURREAL_ADDRESS", "localhost")
    port = os.getenv("SURREAL_PORT", "8000")
    return f"ws://{address}/rpc:{port}"

def get_database_password():
    """Get password with backward compatibility"""
    return os.getenv("SURREAL_PASSWORD") or os.getenv("SURREAL_PASS")
```

#### 1.2 Replace Database Layer
- Copy `database/new.py` → `database/repository.py`
- Update connection configuration to use compatibility functions
- Ensure all function signatures match existing API

#### 1.3 Async Migration System
Create `database/async_migrate.py`:
```python
class AsyncMigrationManager:
    def __init__(self):
        self.url = get_database_url()
        self.password = get_database_password()
        # ... async connection setup
    
    async def get_current_version(self) -> int:
        # Async version of migration tracking
    
    async def run_migration_up(self):
        # Async migration execution
```

#### 1.4 Update Dependencies
- Remove `sdblpy` from pyproject.toml
- Dependencies `surrealdb` and `nest-asyncio` are already properly configured

### ✅ Testing Strategy
1. Test database connection with both old and new env vars
2. Verify basic CRUD operations work
3. Test migration system initialization
4. Confirm no import errors in application

### ⚠️ Critical Notes
- **DO NOT** update any domain models in this phase
- Keep existing function signatures identical
- Test thoroughly before proceeding to Phase 2
- **STOP** at end of phase and request human approval before continuing

---

## Phase 2: Base Domain Model Migration (2.5 hours)

### 🎯 Goals
- Convert base classes (`ObjectModel`, `RecordModel`) to async
- Update simple domain models
- Establish async patterns for inheritance

### 📁 Files to Change
1. `open_notebook/domain/base.py` - Convert to async
2. `open_notebook/domain/models.py` - Update ModelManager to async

### 🔧 Specific Implementation Steps

#### 2.1 Async Base Classes
Convert `ObjectModel` and `RecordModel`:
```python
class ObjectModel(BaseModel):
    # ... existing code ...
    
    async def save(self):
        """Async save method"""
        data = self.model_dump()  # Pydantic v2 syntax
        if hasattr(self, 'id') and self.id:
            result = await repo_update(self.table_name, self.id, data)
        else:
            result = await repo_create(self.table_name, data)
        # Update self with returned data
        return self
    
    async def delete(self):
        """Async delete method"""
        if hasattr(self, 'id') and self.id:
            return await repo_delete(ensure_record_id(self.id))
        raise ValueError("Cannot delete object without ID")
    
    @classmethod
    async def get_all(cls, limit: int = 1000):
        """Async get all method"""
        result = await repo_query(f"SELECT * FROM {cls.table_name} LIMIT $limit", {"limit": limit})
        return [cls(**item) for item in result]
    
    @classmethod
    async def get(cls, id: str):
        """Async get by ID method"""
        result = await repo_query("SELECT * FROM $id", {"id": ensure_record_id(f"{cls.table_name}:{id}")})
        if result:
            return cls(**result[0])
        return None
```

#### 2.2 Convert Simple Models
Update these models to use async base methods:
- `ContentSettings` (RecordModel)
- `DefaultModels` (RecordModel) 
- `DefaultPrompts` (RecordModel)
- `Transformation` (ObjectModel)

#### 2.3 Update ModelManager
```python
class ModelManager:
    async def get_models_by_type(self, model_type: str):
        """Async model retrieval"""
        return await repo_query(
            "SELECT * FROM model WHERE type = $type", 
            {"type": model_type}
        )
    
    # Update caching to be async-safe
```

### ✅ Testing Strategy
1. Test base class CRUD operations
2. Verify inheritance works correctly
3. Test simple model operations
4. Check ModelManager functionality

### ⚠️ Critical Notes
- This phase establishes the async pattern for all other models
- Property methods that use database queries will need attention in future phases
- Keep backward compatibility for method names
- **STOP** at end of phase and request human approval before continuing

---

## Phase 3: Medium Complexity Domain Models (2 hours)

### 🎯 Goals  
- Convert medium complexity models to async
- Handle property to async method conversion
- Update SQL queries to use parameterized syntax

### 📁 Files to Change
1. `open_notebook/domain/notebook.py` - Convert Notebook, Note, ChatSession
2. Update all property methods to async methods

### 🔧 Specific Implementation Steps

#### 3.1 Convert Property Methods to Async Methods
```python
class Notebook(ObjectModel):
    # Old property
    @property
    def sources(self):
        return repo_query(f"SELECT * FROM source WHERE notebook_id = '{self.id}'")
    
    # New async method  
    async def get_sources(self):
        return await repo_query(
            "SELECT * FROM source WHERE notebook_id = $id", 
            {"id": ensure_record_id(self.id)}
        )
    
    # Update all properties: sources, notes, chat_sessions
```

#### 3.2 Security: Parameterized Queries
Convert all f-string queries to parameterized:
```python
# OLD (Security risk)
result = await repo_query(f"SELECT * FROM reference WHERE out={self.id}")

# NEW (Secure)
result = await repo_query(
    "SELECT * FROM reference WHERE out=$id", 
    {"id": ensure_record_id(self.id)}
)
```

#### 3.3 Convert Models
- `Notebook` - Convert properties to async methods
- `Note` - Update save with embedding logic  
- `ChatSession` - Simple conversion
- `SourceEmbedding` - Simple with one relationship
- `SourceInsight` - Simple with one relationship

### ✅ Testing Strategy
1. Test each model's CRUD operations
2. Verify relationship queries work
3. Test parameterized query security
4. Check embedding functionality

### ⚠️ Critical Notes
- **BREAKING CHANGE**: Properties become async methods (`.sources` → `await .get_sources()`)
- All SQL queries must be parameterized for security
- Document property → method name changes
- **STOP** at end of phase and request human approval before continuing

---

## Phase 4: Complex Domain Models (2.5 hours)

### 🎯 Goals
- Convert the most complex model (Source) with vectorization
- Handle ThreadPoolExecutor integration with async
- Update search functions

### 📁 Files to Change
1. `open_notebook/domain/notebook.py` - Source model and search functions

### 🔧 Specific Implementation Steps

#### 4.1 Source Model Vectorization
```python
class Source(ObjectModel):
    async def vectorize(self):
        """Complex async vectorization with ThreadPoolExecutor"""
        # Keep ThreadPoolExecutor for CPU-bound embedding work
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor() as executor:
            # Run CPU-intensive embedding in thread pool
            embedding_task = loop.run_in_executor(
                executor, self._generate_embeddings
            )
            embeddings = await embedding_task
        
        # Async database operations
        for chunk_data in embeddings:
            await repo_create("source_embedding", chunk_data)
    
    def _generate_embeddings(self):
        """Sync method for CPU-bound embedding work"""
        # Existing embedding logic stays synchronous
        pass
    
    async def add_insight(self, insight_text: str):
        """Async insight creation"""
        return await repo_create("source_insight", {
            "source_id": self.id,
            "content": insight_text
        })
```

#### 4.2 Update Search Functions
```python
async def text_search(query: str, notebook_id: str = None):
    """Async text search with parameterized queries"""
    conditions = ["content CONTAINS $query"]
    params = {"query": query}
    
    if notebook_id:
        conditions.append("notebook_id = $notebook_id")
        params["notebook_id"] = ensure_record_id(notebook_id)
    
    sql = f"SELECT * FROM source WHERE {' AND '.join(conditions)}"
    return await repo_query(sql, params)

async def vector_search(query: str, limit: int = 10):
    """Async vector search"""
    # Implementation with async database calls
```

### ✅ Testing Strategy
1. Test Source model CRUD operations
2. Verify vectorization process works
3. Test search functions with various queries
4. Check ThreadPoolExecutor integration

### ⚠️ Critical Notes
- ThreadPoolExecutor pattern for CPU-bound work
- Async/sync boundary management crucial
- Search functions are heavily used - test thoroughly
- **STOP** at end of phase and request human approval before continuing

---

## Phase 5: API Layer Migration (1.5 hours)

### 🎯 Goals
- Update all FastAPI endpoints to properly await domain operations
- Update service classes to use async domain methods
- Ensure proper error handling

### 📁 Files to Change
1. `api/notebook_service.py` - Update service methods
2. `api/notes_service.py` - Update service methods  
3. `api/models_service.py` - Update service methods
4. All files in `api/routers/` - Update route handlers

### 🔧 Specific Implementation Steps

#### 5.1 Update Service Classes
```python
class NotebookService:
    async def get_notebook(self, notebook_id: str):
        """Update to use async domain methods"""
        notebook = await Notebook.get(notebook_id)
        if notebook:
            # Property methods become async method calls
            sources = await notebook.get_sources()
            notes = await notebook.get_notes()
            return {
                "notebook": notebook,
                "sources": sources,
                "notes": notes
            }
        return None
    
    async def create_notebook(self, data: dict):
        """Async notebook creation"""
        notebook = Notebook(**data)
        return await notebook.save()
```

#### 5.2 Update API Routers
```python
@router.get("/notebooks/{notebook_id}")
async def get_notebook(notebook_id: str):
    """Ensure proper async/await usage"""
    service = NotebookService()
    result = await service.get_notebook(notebook_id)  # Await added
    if result:
        return result
    raise HTTPException(status_code=404, detail="Notebook not found")
```

### ✅ Testing Strategy
1. Test all API endpoints manually
2. Verify proper error handling
3. Check response formats remain consistent
4. Test with various data scenarios

### ⚠️ Critical Notes
- FastAPI endpoints are already async, just need proper await calls
- Service layer acts as adapter between API and domain
- Maintain existing API response formats
- **STOP** at end of phase and request human approval before continuing

---

## Phase 6: Streamlit Integration (2 hours)

### 🎯 Goals
- Add `nest_asyncio` to all Streamlit pages
- Wrap domain model calls with `asyncio.run()`
- Update complex UI operations

### 📁 Files to Change
1. All files in `pages/` directory (~15 files)
2. All files in `pages/stream_app/` directory (~10 files)
3. Files in `pages/components/` directory (~5 files)

### 🔧 Specific Implementation Steps

#### 6.1 Standard Streamlit Page Pattern
```python
# Add to top of every Streamlit file
import nest_asyncio
nest_asyncio.apply()

import asyncio
import streamlit as st
from open_notebook.domain.notebook import Notebook

# Async data loading
async def load_notebooks():
    return await Notebook.get_all()

async def load_notebook_details(notebook_id):
    notebook = await Notebook.get(notebook_id)
    if notebook:
        sources = await notebook.get_sources()
        notes = await notebook.get_notes()
        return notebook, sources, notes
    return None, [], []

# Streamlit app code
def main():
    st.title("My Page")
    
    # Wrap async calls
    notebooks = asyncio.run(load_notebooks())
    
    if st.selectbox("Select Notebook", notebooks):
        notebook_id = st.session_state.selected_notebook
        notebook, sources, notes = asyncio.run(load_notebook_details(notebook_id))
        
        # Display data...

if __name__ == "__main__":
    main()
```

#### 6.2 Handle Service Layer Calls
For pages using service layer HTTP calls:
```python
# These remain mostly unchanged since they use HTTP
service = NotebookService()
response = requests.get(f"/api/notebooks/{notebook_id}")
```

#### 6.3 Complex Chat Integration
```python
# pages/stream_app/chat.py - Special handling
async def process_chat_message(message: str, notebook_id: str):
    # LangGraph operations are already async
    result = await chat_graph.astream({
        "message": message,
        "notebook_id": notebook_id
    })
    return result

# In Streamlit
if user_input:
    response = asyncio.run(process_chat_message(user_input, notebook_id))
```

### ✅ Testing Strategy
1. Test each Streamlit page loads correctly
2. Verify all async operations work
3. Check session state management
4. Test complex chat functionality

### ⚠️ Critical Notes
- Some pages already use `nest_asyncio` - check before adding
- Service layer HTTP calls don't need changes
- Chat system needs special attention due to streaming
- **STOP** at end of phase and request human approval before continuing

---

## Phase 7: Migration System & Cleanup (1 hour)

### 🎯 Goals
- Update migration system to use async database client
- Remove obsolete code and dependencies
- Final testing and documentation

### 📁 Files to Change
1. `open_notebook/database/migrate.py` - Finalize async migration system
2. `open_notebook/utils.py` - Remove `surreal_clean` function
3. `pages/stream_app/utils.py` - Update migration check
4. Documentation updates

### 🔧 Specific Implementation Steps

#### 7.1 Finalize Async Migration System
```python
class AsyncMigrationManager:
    async def run_migration_up(self):
        """Complete async migration implementation"""
        current_version = await self.get_current_version()
        
        if self.needs_migration:
            for i in range(current_version, len(self.up_migrations)):
                migration = self.up_migrations[i]
                async with db_connection() as conn:
                    await conn.query(migration.sql)
                    await self.bump_version()
        
    async def needs_migration(self) -> bool:
        current = await self.get_current_version()
        return current < len(self.up_migrations)
```

#### 7.2 Remove Obsolete Code
- Remove `surreal_clean` function from `utils.py`
- Update any code that imported `surreal_clean`
- Clean up unused imports

#### 7.3 Update Migration Check
```python
# pages/stream_app/utils.py
async def check_migration():
    """Async migration check"""
    manager = AsyncMigrationManager()
    if await manager.needs_migration():
        await manager.run_migration_up()
```

### ✅ Testing Strategy
1. Test migration system works end-to-end
2. Verify application starts without errors
3. Test all major functionality paths
4. Performance check

### ⚠️ Critical Notes
- **STOP** at end of phase and request human approval
- Mark migration as complete in plan.md

---

## 🚨 Risk Mitigation Strategies

### Git Strategy
- Work directly on current branch (no additional branches needed)
- Human will review and commit after each phase completion
- Agent must request human approval before proceeding to next phase

### Testing Approach
- Manual testing after each phase
- Focus on CRUD operations, API endpoints, and UI functionality
- Test with realistic data volumes
- Performance monitoring

### Rollback Plan
- Each phase is designed to be independently rollback-able
- Keep environment variable compatibility for easy switching
- Maintain backup of current working state

---

## 📋 Success Criteria

### Phase Completion Criteria
- [ ] All code compiles without errors
- [ ] No breaking changes to external API interfaces
- [ ] All manual tests pass
- [ ] Performance is maintained or improved
- [ ] Environment variables work in both formats

### Final Success Metrics
- [ ] All existing functionality preserved
- [ ] Improved security with parameterized queries
- [ ] Clean async/await patterns throughout
- [ ] Official SurrealDB client integration complete
- [ ] Migration system working with async client
- [ ] Documentation updated

---

## 🎯 Implementation Notes

### Session Planning
- **Session 1**: Phase 1 (Foundation)
- **Session 2**: Phase 2 + start Phase 3 (Base models)
- **Session 3**: Complete Phase 3 + Phase 4 (Complex models)
- **Session 4**: Phase 5 + Phase 6 (API + Streamlit)
- **Session 5**: Phase 7 + final testing (Cleanup)

### Dependencies Between Phases
- Phase 2 depends on Phase 1 (database layer)
- Phase 3 builds on Phase 2 (base classes)
- Phase 4 completes domain model migration
- Phases 5-6 can be done in parallel if needed
- Phase 7 requires all previous phases

### Breaking Changes Documentation
- Properties become async methods (documented in each phase)
- Import changes (minimal, mostly internal)
- Environment variable additions (backward compatible)

This plan provides a systematic approach to migrating the entire codebase while minimizing risk and maintaining functionality throughout the process.

---

## 📝 Phase Completion Tracking

### Phase Status
- [ ] **Phase 1**: Foundation & Database Layer Migration - *PENDING*
- [ ] **Phase 2**: Base Domain Model Migration - *PENDING*  
- [ ] **Phase 3**: Medium Complexity Domain Models - *PENDING*
- [ ] **Phase 4**: Complex Domain Models - *PENDING*
- [ ] **Phase 5**: API Layer Migration - *PENDING*
- [ ] **Phase 6**: Streamlit Integration - *PENDING*
- [ ] **Phase 7**: Migration System & Cleanup - *PENDING*

### Important Notes for Agent
- **ALWAYS STOP** at the end of each phase and request human approval
- **UPDATE** this plan.md file after each successful phase:
  - Mark phase as complete with ✅
  - Add any lessons learned or additional notes
  - Update next steps if requirements change
- **ASK HUMAN** to review and commit changes before proceeding
- **DO NOT** proceed to next phase without explicit human approval