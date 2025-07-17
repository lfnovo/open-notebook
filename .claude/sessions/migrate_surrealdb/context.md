# SurrealDB Migration Context

## Why This Is Being Built

We are migrating from sdblpy (lightweight SurrealDB client) to the official SurrealDB Python client for better functionality, long-term support, and access to the full feature set of SurrealDB.

## Expected Outcome

- Complete replacement of the database layer from synchronous to asynchronous operations
- Maintain all existing functionality while improving performance and reliability
- Modernize the codebase to use official SurrealDB client
- Ensure seamless user experience with no data loss or functionality regression

## Technical Approach

### 1. Database Layer Migration
- Replace `open_notebook/database/repository.py` with `open_notebook/database/new.py`
- Convert all database operations from synchronous to asynchronous
- Update all domain models to use async/await syntax

### 2. Environment Variable Compatibility
- Maintain backward compatibility by checking which environment variables are configured
- Convert `SURREAL_ADDRESS` + `SURREAL_PORT` to `SURREAL_URL` format when needed
- Support both old and new environment variable formats

### 3. Streamlit Integration
- Use `asyncio.run()` for async database calls in Streamlit pages
- Import `nest_asyncio` and run `apply()` method before anything else in all Streamlit pages
- Ensure all Streamlit functionality remains intact

### 4. Migration System
- Reimplement migration system using async SurrealDB client
- Inspect source code at `../../../experimentos/surreal-lite-py` for patterns
- Maintain existing migration file structure and functionality

### 5. API and Domain Models
- Update all FastAPI endpoints to properly handle async database calls
- Modify domain models (`base.py`, `models.py`, `notebook.py`) to use async patterns
- Ensure all relationships and complex queries continue to work

## Key Differences Between Old and New Systems

### Database Functions
- **Old**: All synchronous functions (repo_create, repo_query, etc.)
- **New**: All async functions with improved error handling and automatic timestamps

### Environment Variables
- **Old**: `SURREAL_ADDRESS`, `SURREAL_PORT`, `SURREAL_USER`, `SURREAL_PASS`
- **New**: `SURREAL_URL`, `SURREAL_USER`, `SURREAL_PASSWORD`

### Connection Management
- **Old**: `@contextmanager` for sync connections
- **New**: `@asynccontextmanager` for async connections with proper cleanup

### Data Processing
- **Old**: Manual data cleaning required (`surreal_clean` function)
- **New**: Built-in data handling, no manual cleaning needed

## Migration Scope

### Files Requiring Direct Changes (~40+ files)
1. **Core Domain Models**: `base.py`, `models.py`, `notebook.py`
2. **API Services**: All FastAPI endpoints and services
3. **Streamlit Pages**: All pages and components
4. **Migration System**: `migrate.py` replacement
5. **Database Layer**: Replace `repository.py` with `new.py`

### Testing Strategy
- Manual testing approach after completing each major component
- Test all database operations, API endpoints, and Streamlit functionality
- Verify data integrity and performance

## Dependencies and Constraints

### New Dependencies
- Official `surrealdb` Python client (already added)
- `nest_asyncio` for Streamlit compatibility

### Removed Dependencies
- `sdblpy` (custom lightweight client)
- `surreal_clean` utility function (no longer needed)

### Constraints
- Must maintain all existing functionality
- No data loss during migration
- Minimal disruption to user workflows
- Backward compatibility for environment variables

## Success Criteria

1. All database operations work with async/await pattern
2. All API endpoints function correctly
3. All Streamlit pages load and operate normally
4. Migration system works with new async client
5. Environment variables support both old and new formats
6. No functionality regression
7. Improved performance and reliability

## Risks and Mitigation

### Risks
- Async conversion might introduce subtle bugs
- Streamlit async integration complexity
- Migration system compatibility issues

### Mitigation
- Thorough manual testing of each component
- Incremental migration approach
- Maintain environment variable compatibility
- Careful inspection of surreal-lite-py source for migration patterns