# Lumina Third-Party API Contract

This document defines the first-party contract for HTTP plugin providers that expose external sources and output generation to Lumina. In v1, Lumina system administrators configure the endpoint and API key, then grant enabled sources to teams with a monthly request quota.

## Authentication

Lumina calls every third-party endpoint with:

```http
Authorization: Bearer <api_key>
X-Lumina-Request-Id: <uuid>
Content-Type: application/json
```

The API key is configured by a Lumina system administrator and is never exposed to team users. Providers should treat `X-Lumina-Request-Id` as an idempotency and trace key.

## Required Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/.well-known/lumina-plugin.json` | Plugin manifest, capabilities, and version metadata. |
| `GET` | `/lumina/v1/health` | Connectivity and service readiness check. |
| `POST` | `/lumina/v1/sources/search` | Search an external source. |
| `POST` | `/lumina/v1/sources/fetch` | Fetch full details for a search result item. |
| `POST` | `/lumina/v1/outputs/generate` | Generate a third-party output artifact. |
| `GET` | `/lumina/v1/jobs/{external_job_id}` | Poll asynchronous job status. |

## Manifest

`GET /.well-known/lumina-plugin.json` returns:

```json
{
  "schema_version": "lumina-plugin-v1",
  "name": "Paper Search",
  "provider": "Example Labs",
  "version": "1.0.0",
  "capabilities": ["search", "fetch", "output"],
  "sources": [
    {
      "key": "paper_search",
      "name": "Paper Search",
      "description": "Search papers and fetch paper details.",
      "capabilities": ["search", "fetch", "output"]
    }
  ]
}
```

## Async Response Rules

Source search, fetch, and output generation may return a completed result immediately:

```json
{
  "status": "completed",
  "data": {}
}
```

Or accept a job for polling:

```json
{
  "status": "accepted",
  "external_job_id": "job_123",
  "next_poll_after_seconds": 2
}
```

`GET /lumina/v1/jobs/{external_job_id}` must return one of:

```json
{ "status": "accepted", "external_job_id": "job_123", "next_poll_after_seconds": 2 }
{ "status": "completed", "external_job_id": "job_123", "data": {} }
{ "status": "failed", "external_job_id": "job_123", "error": { "code": "provider_error", "message": "..." } }
```

## Source Search

Request:

```json
{
  "source_key": "paper_search",
  "query": "graph retrieval",
  "limit": 10,
  "filters": {
    "year_from": 2022
  }
}
```

Completed response:

```json
{
  "status": "completed",
  "data": {
    "items": [
      {
        "external_id": "arxiv:2401.00001",
        "title": "Graph Retrieval for Research Agents",
        "summary": "A concise abstract or snippet.",
        "url": "https://example.org/paper/2401.00001",
        "authors": ["Ada Lovelace"],
        "published_at": "2026-01-15",
        "metadata": { "venue": "ExampleConf" }
      }
    ]
  }
}
```

## Source Fetch

Request:

```json
{
  "source_key": "paper_search",
  "external_id": "arxiv:2401.00001",
  "metadata": {}
}
```

Completed response:

```json
{
  "status": "completed",
  "data": {
    "external_id": "arxiv:2401.00001",
    "title": "Graph Retrieval for Research Agents",
    "content_markdown": "# Graph Retrieval\n\nFull paper text or detail.",
    "url": "https://example.org/paper/2401.00001",
    "metadata": { "pdf_url": "https://example.org/paper.pdf" }
  }
}
```

## Output Generate

Request:

```json
{
  "source_key": "paper_search",
  "prompt": "Create a structured evidence table.",
  "input_text": "Optional user text",
  "items": [],
  "output_kind": "markdown",
  "options": {}
}
```

Completed response:

```json
{
  "status": "completed",
  "data": {
    "kind": "markdown",
    "title": "Evidence Table",
    "content": "| Claim | Evidence |\n| --- | --- |",
    "metadata": {}
  }
}
```

Supported output kinds are `markdown`, `json`, `file`, and `url`.

## Errors

Use standard HTTP status codes plus a structured body:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "query is required",
    "retryable": false
  }
}
```

Recommended codes:

| HTTP | Code | Meaning |
| --- | --- | --- |
| `400` | `invalid_request` | The request body is malformed or unsupported. |
| `401` | `invalid_api_key` | Missing or invalid API key. |
| `403` | `forbidden` | API key is valid but cannot use this source. |
| `404` | `not_found` | External item or job was not found. |
| `429` | `rate_limited` | Provider-side rate limit. Lumina quota is enforced separately. |
| `500` | `provider_error` | Non-retryable provider failure. |
| `503` | `temporarily_unavailable` | Retryable provider outage. |

## Lumina Quota Semantics

Quota is enforced by Lumina on `team + external source + calendar month`. Source search checks team authorization but does not consume quota. A source quota unit is consumed only when Lumina sends a `fetch` request that actually imports a third-party item as a local source. Provider job polling and Lumina internal retries do not consume additional quota. If local validation fails before the third-party request is sent, quota is not consumed.
