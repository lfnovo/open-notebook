#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8099}"
API_KEY="${API_KEY:-dev-paper-key}"
REQUEST_ID="${REQUEST_ID:-00000000-0000-4000-8000-000000000001}"

curl -sS "$BASE_URL/lumina/v1/sources/search" \
  -H "Authorization: Bearer $API_KEY" \
  -H "X-Lumina-Request-Id: $REQUEST_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "source_key": "paper_search",
    "query": "graph",
    "limit": 5,
    "filters": {}
  }'
