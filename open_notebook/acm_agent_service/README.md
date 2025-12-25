# ACM Scholar Agent Module

This module implements the "ACM Scholar Agent" for Open Notebook, providing direct access to ACM Digital Library papers via OpenAlex.

## Architecture: Open Core Ready

This module is designed with a strict interface (`ResearchAgentInterface`) to support the "Open Core" commercialization strategy.

-   **Local Mode (Default)**: Runs the search logic locally using `tools.py`. Fully Open Source (MIT).
-   **Pro Mode (Future)**: Switchable to a remote API client (`RemoteProAgent`) for enterprise features without changing application code.

## Usage

### 1. Integration into Open Notebook

In your main application (e.g., `app/main.py` or a service layer):

```python
from acm_agent_service import get_research_agent

# 1. Get the agent (automatically configured via env vars)
agent = get_research_agent()

# 2. Search for papers
results = agent.search_papers("Gaussian Splatting")
for paper in results:
    print(f"- {paper['title']} ({paper['year']})")
    
# 3. Ingest a paper
if results:
    status = agent.ingest_paper(results[0]['pdf_url'])
    print(status)
```

### 2. Configuration

Control the behavior using Environment Variables:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `ACM_AGENT_MODE` | `LOCAL` | (Default) Uses the open-source local logic. |
| `ACM_AGENT_MODE` | `PRO` | Switches to the commercial API client. |
| `ACM_AGENT_API_KEY`| `sk-...` | Required if mode is PRO. |

## Technical Details

-   **Search Backend**: OpenAlex API (`https://api.openalex.org/works`)
-   **Filters Used**:
    -   `publisher`: ACM (`P4310319798`)
    -   `concept`: Computer Science (`C41008148`)
    -   `is_oa`: `true`
-   **Dependencies**: `requests`, `loguru`

## Trusted Open Access Sources

The agent prioritizes PDFs from these trusted repositories (direct download without authentication):

- arxiv.org
- ncbi.nlm.nih.gov (PubMed Central)
- europepmc.org
- biorxiv.org / medrxiv.org
- zenodo.org
- figshare.com

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/acm/search` | GET | Search ACM papers |
| `/api/agent/acm/ingest` | POST | Download and ingest paper |
| `/api/agent/health` | GET | Check agent status |

## Phase 1 (MVP) - Current

- Full open source implementation
- Search ACM papers via OpenAlex
- Auto-download PDFs from trusted OA sources
- Integrate with Open Notebook's source processing pipeline
