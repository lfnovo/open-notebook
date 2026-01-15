# Code Standards

This document outlines coding standards and best practices for Open Notebook contributions. All code should follow these guidelines to ensure consistency, readability, and maintainability.

## Python Standards

### Code Formatting

We follow **PEP 8** with some specific guidelines:

- Use **Ruff** for linting and formatting
- Maximum line length: **88 characters**
- Use **double quotes** for strings
- Use **trailing commas** in multi-line structures

### Type Hints

Always use type hints for function parameters and return values:

```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

async def process_content(
    content: str,
    options: Optional[Dict[str, Any]] = None
) -> ProcessedContent:
    """Process content with optional configuration."""
    # Implementation
```

### Async/Await Patterns

Use async/await consistently throughout the codebase:

```python
# Good
async def fetch_data(url: str) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Bad - mixing sync and async
def fetch_data(url: str) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_fetch(url))
```

### Error Handling

Use structured error handling with custom exceptions:

```python
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError

async def create_notebook(name: str, description: str) -> Notebook:
    """Create a new notebook with validation."""
    if not name.strip():
        raise InvalidInputError("Notebook name cannot be empty")

    try:
        notebook = Notebook(name=name, description=description)
        await notebook.save()
        return notebook
    except Exception as e:
        raise DatabaseOperationError(f"Failed to create notebook: {str(e)}")
```

### Documentation (Google-style Docstrings)

Use Google-style docstrings for all functions, classes, and modules:

```python
async def vector_search(
    query: str,
    limit: int = 10,
    minimum_score: float = 0.2
) -> List[SearchResult]:
    """Perform vector search across embedded content.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        minimum_score: Minimum similarity score for results

    Returns:
        List of search results sorted by relevance score

    Raises:
        InvalidInputError: If query is empty or limit is invalid
        DatabaseOperationError: If search operation fails
    """
    # Implementation
```

#### Module Docstrings
```python
"""
Notebook domain model and operations.

This module contains the core Notebook class and related operations for
managing research notebooks within the Open Notebook system.
"""
```

#### Class Docstrings
```python
class Notebook(BaseModel):
    """A research notebook containing sources, notes, and chat sessions.

    Notebooks are the primary organizational unit in Open Notebook, allowing
    users to group related research materials and maintain separate contexts
    for different projects.

    Attributes:
        name: The notebook's display name
        description: Optional description of the notebook's purpose
        archived: Whether the notebook is archived (default: False)
        created: Timestamp of creation
        updated: Timestamp of last update
    """
```

#### Function Docstrings
```python
async def create_notebook(
    name: str,
    description: str = "",
    user_id: Optional[str] = None
) -> Notebook:
    """Create a new notebook with validation.

    Args:
        name: The notebook name (required, non-empty)
        description: Optional notebook description
        user_id: Optional user ID for multi-user deployments

    Returns:
        The created notebook instance

    Raises:
        InvalidInputError: If name is empty or invalid
        DatabaseOperationError: If creation fails

    Example:
        ```python
        notebook = await create_notebook(
            name="AI Research",
            description="Research on AI applications"
        )
        ```
    """
```

## FastAPI Standards

### Router Organization

Organize endpoints by domain:

```python
# api/routers/notebooks.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

router = APIRouter()

@router.get("/notebooks", response_model=List[NotebookResponse])
async def get_notebooks(
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    order_by: str = Query("updated desc", description="Order by field and direction"),
):
    """Get all notebooks with optional filtering and ordering."""
    # Implementation
```

### Request/Response Models

Use Pydantic models for validation:

```python
from pydantic import BaseModel, Field
from typing import Optional

class NotebookCreate(BaseModel):
    name: str = Field(..., description="Name of the notebook", min_length=1)
    description: str = Field(default="", description="Description of the notebook")

class NotebookResponse(BaseModel):
    id: str
    name: str
    description: str
    archived: bool
    created: str
    updated: str
```

### Error Handling

Use consistent error responses:

```python
from fastapi import HTTPException
from loguru import logger

try:
    result = await some_operation()
    return result
except InvalidInputError as e:
    raise HTTPException(status_code=400, detail=str(e))
except DatabaseOperationError as e:
    logger.error(f"Database error: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### API Documentation

Use FastAPI's automatic documentation features:

```python
@router.post(
    "/notebooks",
    response_model=NotebookResponse,
    summary="Create a new notebook",
    description="Create a new notebook with the specified name and description.",
    responses={
        201: {"description": "Notebook created successfully"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"}
    }
)
async def create_notebook(notebook: NotebookCreate):
    """Create a new notebook."""
    # Implementation
```

## Database Standards

### SurrealDB Patterns

Use the repository pattern consistently:

```python
from open_notebook.database.repository import repo_create, repo_query, repo_update

# Create records
async def create_notebook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new notebook record."""
    return await repo_create("notebook", data)

# Query with parameters
async def find_notebooks_by_user(user_id: str) -> List[Dict[str, Any]]:
    """Find notebooks for a specific user."""
    return await repo_query(
        "SELECT * FROM notebook WHERE user_id = $user_id",
        {"user_id": user_id}
    )

# Update records
async def update_notebook(notebook_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a notebook record."""
    return await repo_update("notebook", notebook_id, data)
```

### Schema Management

Use migrations for schema changes:

```surrealql
-- migrations/8.surrealql
DEFINE TABLE IF NOT EXISTS new_feature SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name ON TABLE new_feature TYPE string;
DEFINE FIELD IF NOT EXISTS description ON TABLE new_feature TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created ON TABLE new_feature TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS updated ON TABLE new_feature TYPE datetime DEFAULT time::now();
```

## TypeScript Standards

### Basic Guidelines

Follow TypeScript best practices:

- Use strict mode enabled in `tsconfig.json`
- Use proper type annotations for all variables and functions
- Avoid using `any` type unless absolutely necessary
- Use `interface` for object shapes, `type` for unions and other advanced types

### Component Structure

- Use functional components with hooks
- Keep components focused and single-responsibility
- Extract reusable logic into custom hooks
- Use proper TypeScript types for props

### Error Handling

- Handle errors explicitly
- Provide meaningful error messages
- Log errors appropriately
- Don't suppress errors silently

## Code Quality Tools

We use these tools to maintain code quality:

- **Ruff**: Linting and code formatting
  - Run with: `uv run ruff check . --fix`
  - Format with: `uv run ruff format .`

- **MyPy**: Static type checking
  - Run with: `uv run python -m mypy .`

- **Pytest**: Testing framework
  - Run with: `uv run pytest`

## Common Patterns

### Async Database Operations

```python
async def get_notebook_with_sources(notebook_id: str) -> Notebook:
    """Retrieve notebook with all related sources."""
    notebook_data = await repo_query(
        "SELECT * FROM notebook WHERE id = $id",
        {"id": notebook_id}
    )
    if not notebook_data:
        raise InvalidInputError(f"Notebook {notebook_id} not found")

    sources_data = await repo_query(
        "SELECT * FROM source WHERE notebook_id = $notebook_id",
        {"notebook_id": notebook_id}
    )

    return Notebook(
        **notebook_data[0],
        sources=[Source(**s) for s in sources_data]
    )
```

### Model Validation

```python
from pydantic import BaseModel, validator

class NotebookInput(BaseModel):
    name: str
    description: str = ""

    @validator('name')
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
```

## Code Review Checklist

Before submitting code for review, ensure:

- [ ] Code follows PEP 8 / TypeScript best practices
- [ ] Type hints are present for all functions
- [ ] Docstrings are complete and accurate
- [ ] Error handling is appropriate
- [ ] Tests are included and passing
- [ ] No debug code (console.logs, print statements) left behind
- [ ] Commit messages are clear and follow conventions
- [ ] Documentation is updated if needed

---

**See also:**
- [Testing Guide](testing.md) - How to write tests
- [Contributing Guide](contributing.md) - Overall contribution workflow
