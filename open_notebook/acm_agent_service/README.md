# ACM Scholar Agent Module

Search and discover ACM Digital Library papers via OpenAlex API.

## Usage

```python
from open_notebook.acm_agent_service import get_research_agent

agent = get_research_agent()

# Search for papers
results = agent.search_papers("Large Language Models")
for paper in results:
    print(f"- {paper['title']} ({paper['year']})")
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/acm/search` | GET | Search ACM papers |
| `/api/agent/acm/ingest` | POST | Download and ingest paper |

## Technical Details

- **Search Backend**: OpenAlex API
- **Filters**: ACM Publisher, Computer Science, Open Access
- **Dependencies**: `requests`, `loguru`
