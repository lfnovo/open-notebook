# Contributing to Open Notebook

Thank you for your interest in contributing to Open Notebook! We welcome contributions from developers of all skill levels. This guide will help you get started and understand our development workflow.

## 🎯 Quick Start for Contributors

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/open-notebook.git
cd open-notebook

# Add the original repository as upstream
git remote add upstream https://github.com/lfnovo/open-notebook.git
```

### 2. Set Up Development Environment

```bash
# Install dependencies using uv (recommended)
uv sync

# Or using pip
pip install -e .

# Start the development environment
make start-all
```

### 3. Verify Setup

```bash
# Check that the API is running
curl http://localhost:5055/health

# Check that the frontend is accessible
open http://localhost:8502
```

## 🏗️ Development Workflow

### Branch Strategy

We use a **feature branch workflow**:

1. **Main Branch**: `main` - production-ready code
2. **Feature Branches**: `feature/description` - new features
3. **Bug Fixes**: `fix/description` - bug fixes
4. **Documentation**: `docs/description` - documentation updates

### Making Changes

1. **Create a feature branch**:
```bash
git checkout -b feature/amazing-new-feature
```

2. **Make your changes** following our coding standards

3. **Test your changes**:
```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run formatting
uv run ruff format .
```

4. **Commit your changes**:
```bash
git add .
git commit -m "feat: add amazing new feature"
```

5. **Push and create PR**:
```bash
git push origin feature/amazing-new-feature
# Then create a Pull Request on GitHub
```

### Keeping Your Fork Updated

```bash
# Fetch upstream changes
git fetch upstream

# Switch to main and merge
git checkout main
git merge upstream/main

# Push to your fork
git push origin main
```

## 📏 Code Standards

### Python Style Guide

We follow **PEP 8** with some specific guidelines:

#### Code Formatting
- Use **Ruff** for linting and formatting
- Maximum line length: **88 characters**
- Use **double quotes** for strings
- Use **trailing commas** in multi-line structures

#### Type Hints
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

#### Async/Await Patterns
Use async/await consistently:

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

#### Error Handling
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

#### Documentation
Use **Google-style docstrings**:

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
```

### FastAPI Standards

#### Router Organization
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
```

#### Request/Response Models
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

#### Error Handling
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

### Database Standards

#### SurrealDB Patterns
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

#### Schema Management
Use migrations for schema changes:

```surrealql
-- migrations/8.surrealql
DEFINE TABLE IF NOT EXISTS new_feature SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name ON TABLE new_feature TYPE string;
DEFINE FIELD IF NOT EXISTS description ON TABLE new_feature TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created ON TABLE new_feature TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS updated ON TABLE new_feature TYPE datetime DEFAULT time::now();
```

## 🧪 Testing Guidelines

### Test Structure

We use **pytest** with async support:

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

### Test Categories

1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test component interactions
3. **API Tests**: Test HTTP endpoints
4. **Database Tests**: Test data persistence and queries

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_notebooks.py

# Run with coverage
uv run pytest --cov=open_notebook

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/
```

### Test Fixtures

Use pytest fixtures for common setup:

```python
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
```

## 📚 Documentation Standards

### Code Documentation

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
```

### README Updates

When adding new features, update relevant documentation:

- **Feature documentation** in `docs/features/`
- **API documentation** in `docs/development/api-reference.md`
- **Architecture documentation** if adding new components
- **User guide** if adding user-facing features

## 🚀 Development Environment

### Prerequisites

- **Python 3.11+**
- **uv** (recommended) or **pip**
- **SurrealDB** (via Docker or binary)
- **Docker** (optional, for containerized development)

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
SURREAL_URL=ws://localhost:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=password
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=development

# AI Providers (add your API keys)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...

# Application
APP_PASSWORD=  # Optional password protection
DEBUG=true
LOG_LEVEL=DEBUG
```

### Local Development Setup

```bash
# Start SurrealDB
docker run -d --name surrealdb -p 8000:8000 \
  surrealdb/surrealdb:v1-latest start \
  --user root --pass password \
  --bind 0.0.0.0:8000 memory

# Install dependencies
uv sync

# Run database migrations
uv run python -m open_notebook.database.async_migrate

# Start the API server
uv run python run_api.py

# Start the Next.js frontend (in another terminal)
cd frontend && npm run dev
```

### Development Tools

We use these tools for development:

- **Ruff**: Linting and formatting
- **Pytest**: Testing framework
- **MyPy**: Type checking
- **Pre-commit**: Git hooks for code quality

Install pre-commit hooks:

```bash
uv run pre-commit install
```

## 🔧 Common Development Tasks

### Adding a New API Endpoint

1. **Create the endpoint** in the appropriate router:
```python
# api/routers/notebooks.py
@router.post("/notebooks/{notebook_id}/archive")
async def archive_notebook(notebook_id: str):
    """Archive a notebook."""
    # Implementation
```

2. **Add request/response models** if needed:
```python
# api/models.py
class ArchiveRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for archiving")
```

3. **Update the domain model** if needed:
```python
# open_notebook/domain/notebook.py
async def archive(self, reason: Optional[str] = None) -> None:
    """Archive this notebook."""
    # Implementation
```

4. **Write tests**:
```python
# tests/test_notebooks.py
@pytest.mark.asyncio
async def test_archive_notebook():
    """Test notebook archiving."""
    # Test implementation
```

5. **Update documentation** in `docs/development/api-reference.md`

### Adding a New Domain Model

1. **Create the model**:
```python
# open_notebook/domain/new_model.py
from open_notebook.domain.base import BaseModel

class NewModel(BaseModel):
    """New domain model."""
    
    # Fields and methods
```

2. **Create database migration**:
```surrealql
-- migrations/N.surrealql
DEFINE TABLE IF NOT EXISTS new_model SCHEMAFULL;
-- Field definitions
```

3. **Add API endpoints**:
```python
# api/routers/new_model.py
# Router implementation
```

4. **Write comprehensive tests**

### Adding AI Processing Features

1. **Create the graph**:
```python
# open_notebook/graphs/new_feature.py
from langgraph import create_graph

@create_graph
async def new_feature_graph(state: NewFeatureState):
    """New AI processing feature."""
    # Implementation
```

2. **Add service layer**:
```python
# api/new_feature_service.py
# Service implementation
```

3. **Create API endpoints**:
```python
# api/routers/new_feature.py
# Router implementation
```

4. **Test with multiple AI providers**

## 🌟 Feature Contribution Guidelines

### Current Priority Areas

We're actively looking for contributions in these areas:

1. **Frontend Enhancement**: Help improve the Next.js/React UI with real-time updates and better UX
2. **Testing**: Expand test coverage across all components
3. **Performance**: Async processing improvements and caching
4. **Documentation**: API examples and user guides
5. **Integrations**: New content sources and AI providers

### Feature Proposal Process

1. **Check existing issues** to avoid duplicates
2. **Open a discussion** on GitHub for large features
3. **Create an issue** with detailed requirements
4. **Get approval** from maintainers before starting work
5. **Implement in phases** for large features

### Code Review Process

All contributions go through code review:

1. **Automated checks** must pass (linting, tests)
2. **Manual review** by maintainers
3. **Documentation review** for user-facing changes
4. **Integration testing** for complex features

## 🐛 Bug Reports and Issues

### Reporting Bugs

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected vs actual behavior**
4. **Environment details** (OS, Python version, etc.)
5. **Relevant logs** and error messages

### Bug Fix Process

1. **Reproduce the issue** locally
2. **Write a failing test** that demonstrates the bug
3. **Fix the issue** with minimal changes
4. **Verify the fix** passes all tests
5. **Update documentation** if needed

## 📞 Getting Help

### Community Support

- **Discord**: [Join our Discord server](https://discord.gg/37XJPXfz2w) for real-time help
- **GitHub Discussions**: For longer-form questions and ideas
- **GitHub Issues**: For bug reports and feature requests

### Mentorship

New contributors are welcome! We offer:

- **First-time contributor** guidance
- **Code review** and feedback
- **Architecture discussions**
- **Career development** advice

## 🏆 Recognition

We recognize contributions through:

- **GitHub credits** on releases
- **Community recognition** in Discord
- **Contribution statistics** in project analytics
- **Maintainer consideration** for active contributors

## 📜 Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/). Please:

- **Be respectful** and inclusive
- **Help others** learn and grow
- **Give constructive feedback**
- **Focus on the code**, not the person

## 🎉 Thank You!

Thank you for contributing to Open Notebook! Your contributions help make research more accessible and private for everyone. Whether you're fixing a typo, adding a feature, or helping with documentation, every contribution matters.

Join our community and let's build something amazing together! 🚀

---

For questions about this guide or contributing in general, please reach out on [Discord](https://discord.gg/37XJPXfz2w) or open a GitHub Discussion.