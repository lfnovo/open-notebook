# Lumina Paper Search Plugin Example

This is a runnable FastAPI mock service for Lumina's third-party API contract.

## Run

```bash
cp .env.example .env
uvicorn main:app --reload --port 8099
```

The mock API key is `dev-paper-key` by default.

## Endpoints

- `GET /.well-known/lumina-plugin.json`
- `GET /lumina/v1/health`
- `POST /lumina/v1/sources/search`
- `POST /lumina/v1/sources/fetch`
- `POST /lumina/v1/outputs/generate`
- `GET /lumina/v1/jobs/{external_job_id}`

## Curl

```bash
./client_examples/search.sh
```

## Python

```bash
python client_examples/client.py
```

Configure a Lumina external API connection with:

- Base URL: `http://localhost:8099`
- API key: `dev-paper-key`
- Source key: `paper_search`
- Capabilities: `search`, `fetch`, `output`
