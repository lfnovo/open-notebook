# Testing Guide

This document provides guidelines for writing tests in Open Notebook. Testing is critical to maintaining code quality and preventing regressions.

## Testing Philosophy

### What to Test

Focus on testing the things that matter most:

- **Business Logic** - Core domain models and their operations
- **API Contracts** - HTTP endpoint behavior and error handling
- **Critical Workflows** - End-to-end flows that users depend on
- **Data Persistence** - Database operations and data integrity
- **Error Conditions** - How the system handles failures gracefully

### What NOT to Test

Don't waste time testing framework code:

- Framework functionality (FastAPI, React, etc.)
- Third-party library implementation
- Simple getters/setters without logic
- View/presentation layer rendering (unless it contains logic)

## Test Structure

We use **pytest** with async support for all Python tests:

```python
import pytest
from httpx import AsyncClient
from open_notebook.domain.notebook import Notebook

@pytest.mark.asyncio
async def test_create_notebook():
    """Test notebook creation."""
    notebook = Notebook(name="Test Notebook", description="Test description")
    await notebook.save()

    assert notebook.id is not None
    assert notebook.name == "Test Notebook"
    assert notebook.created is not None

@pytest.mark.asyncio
async def test_api_create_notebook():
    """Test notebook creation via API."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/notebooks",
            json={"name": "Test Notebook", "description": "Test description"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Notebook"
```

## Test Categories

### 1. Unit Tests

Test individual functions and methods in isolation:

```python
@pytest.mark.asyncio
async def test_notebook_validation():
    """Test that notebook name validation works."""
    with pytest.raises(InvalidInputError):
        Notebook(name="", description="test")

@pytest.mark.asyncio
async def test_notebook_archive():
    """Test notebook archiving."""
    notebook = Notebook(name="Test", description="")
    notebook.archive()
    assert notebook.archived is True
```

**Location**: `tests/unit/`

### 2. Integration Tests

Test component interactions and database operations:

```python
@pytest.mark.asyncio
async def test_create_notebook_with_sources():
    """Test creating a notebook and adding sources."""
    notebook = await create_notebook(name="Research", description="")
    source = await add_source(notebook_id=notebook.id, url="https://example.com")

    retrieved = await get_notebook_with_sources(notebook.id)
    assert len(retrieved.sources) == 1
    assert retrieved.sources[0].id == source.id
```

**Location**: `tests/integration/`

### 3. API Tests

Test HTTP endpoints and error responses:

```python
@pytest.mark.asyncio
async def test_get_notebooks_endpoint():
    """Test GET /notebooks endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/notebooks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_create_notebook_validation():
    """Test that invalid input is rejected."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/notebooks",
            json={"name": "", "description": ""}
        )
        assert response.status_code == 400
```

**Location**: `tests/api/`

### 4. Database Tests

Test data persistence and query correctness:

```python
@pytest.mark.asyncio
async def test_save_and_retrieve_notebook():
    """Test saving and retrieving a notebook from database."""
    notebook = Notebook(name="Test", description="desc")
    await notebook.save()

    retrieved = await Notebook.get(notebook.id)
    assert retrieved.name == "Test"
    assert retrieved.description == "desc"

@pytest.mark.asyncio
async def test_query_by_criteria():
    """Test querying notebooks by criteria."""
    await create_notebook("Active", "")
    await create_notebook("Archived", "")

    active = await repo_query(
        "SELECT * FROM notebook WHERE archived = false"
    )
    assert len(active) >= 1
```

**Location**: `tests/database/`

## Running Tests

### Run All Tests

```bash
uv run pytest
```

### Run Specific Test File

```bash
uv run pytest tests/test_notebooks.py
```

### Run Specific Test Function

```bash
uv run pytest tests/test_notebooks.py::test_create_notebook
```

### Run with Coverage Report

```bash
uv run pytest --cov=open_notebook
```

### Run Only Unit Tests

```bash
uv run pytest tests/unit/
```

### Run Only Integration Tests

```bash
uv run pytest tests/integration/
```

### Run Tests in Verbose Mode

```bash
uv run pytest -v
```

### Run Tests with Output

```bash
uv run pytest -s
```

## Test Fixtures

Use pytest fixtures for common setup and teardown:

```python
import pytest

@pytest.fixture
async def test_notebook():
    """Create a test notebook."""
    notebook = Notebook(name="Test Notebook", description="Test description")
    await notebook.save()
    yield notebook
    await notebook.delete()

@pytest.fixture
async def api_client():
    """Create an API test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def test_notebook_with_sources(test_notebook):
    """Create a test notebook with sample sources."""
    source1 = Source(notebook_id=test_notebook.id, url="https://example.com")
    source2 = Source(notebook_id=test_notebook.id, url="https://example.org")
    await source1.save()
    await source2.save()

    test_notebook.sources = [source1, source2]
    yield test_notebook

    # Cleanup
    await source1.delete()
    await source2.delete()
```

## Best Practices

### 1. Write Descriptive Test Names

```python
# Good - clearly describes what is being tested
async def test_create_notebook_with_valid_name_succeeds():
    ...

# Bad - vague about what's being tested
async def test_notebook():
    ...
```

### 2. Use Docstrings

```python
@pytest.mark.asyncio
async def test_vector_search_returns_sorted_results():
    """Test that vector search results are sorted by relevance score."""
    # Implementation
```

### 3. Test Edge Cases

```python
@pytest.mark.asyncio
async def test_search_with_empty_query():
    """Test that empty query raises error."""
    with pytest.raises(InvalidInputError):
        await vector_search("")

@pytest.mark.asyncio
async def test_search_with_very_long_query():
    """Test that very long query is handled."""
    long_query = "x" * 10000
    results = await vector_search(long_query)
    assert isinstance(results, list)

@pytest.mark.asyncio
async def test_search_with_special_characters():
    """Test that special characters are handled."""
    results = await vector_search("@#$%^&*()")
    assert isinstance(results, list)
```

### 4. Use Assertions Effectively

```python
# Good - specific assertions
assert notebook.name == "Test"
assert len(notebook.sources) == 3
assert notebook.created is not None

# Less good - too broad
assert notebook is not None
assert notebook  # ambiguous what's being tested
```

### 5. Test Both Success and Failure Cases

```python
@pytest.mark.asyncio
async def test_create_notebook_success():
    """Test successful notebook creation."""
    notebook = await create_notebook(name="Research", description="AI")
    assert notebook.id is not None
    assert notebook.name == "Research"

@pytest.mark.asyncio
async def test_create_notebook_empty_name_fails():
    """Test that empty name raises error."""
    with pytest.raises(InvalidInputError):
        await create_notebook(name="", description="")

@pytest.mark.asyncio
async def test_create_notebook_duplicate_fails():
    """Test that duplicate names are handled."""
    await create_notebook(name="Research", description="")
    with pytest.raises(DuplicateError):
        await create_notebook(name="Research", description="")
```

### 6. Keep Tests Independent

```python
# Good - test is self-contained
@pytest.mark.asyncio
async def test_archive_notebook():
    notebook = Notebook(name="Test", description="")
    await notebook.save()
    await notebook.archive()
    assert notebook.archived is True

# Bad - depends on another test's state
@pytest.mark.asyncio
async def test_archive_existing_notebook():
    # Assumes test_create_notebook ran first
    await notebook.archive()  # notebook undefined
```

### 7. Use Fixtures for Reusable Setup

```python
# Instead of repeating setup:
@pytest.fixture
async def client_with_auth(api_client, mock_auth):
    """Client with authentication set up."""
    api_client.headers.update({"Authorization": f"Bearer {mock_auth.token}"})
    yield api_client

@pytest.mark.asyncio
async def test_protected_endpoint(client_with_auth):
    """Test protected endpoint."""
    response = await client_with_auth.get("/api/protected")
    assert response.status_code == 200
```

## Coverage Goals

- Aim for 70%+ overall coverage
- 90%+ coverage for critical business logic
- Don't obsess over 100% - focus on meaningful tests
- Use `--cov` flag to check coverage: `uv run pytest --cov=open_notebook`

## Async Test Patterns

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async function."""
    result = await some_async_function()
    assert result is not None
```

### Testing Concurrent Operations

```python
@pytest.mark.asyncio
async def test_concurrent_notebook_creation():
    """Test creating multiple notebooks concurrently."""
    tasks = [
        create_notebook(f"Notebook {i}", "")
        for i in range(10)
    ]
    notebooks = await asyncio.gather(*tasks)
    assert len(notebooks) == 10
    assert all(n.id for n in notebooks)
```

## Common Testing Errors

### Error: "event loop is closed"

Solution: Use the async fixture properly:
```python
@pytest.fixture
async def notebook():  # Use async fixture
    notebook = Notebook(name="Test", description="")
    await notebook.save()
    yield notebook
    await notebook.delete()
```

### Error: "object is not awaitable"

Solution: Make sure you're using await:
```python
# Wrong
result = create_notebook("Test", "")

# Right
result = await create_notebook("Test", "")
```

---

**See also:**
- [Code Standards](code-standards.md) - Code formatting and style
- [Contributing Guide](contributing.md) - Overall contribution workflow
