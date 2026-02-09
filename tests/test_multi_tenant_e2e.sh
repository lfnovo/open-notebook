#!/usr/bin/env bash
#
# End-to-end test for multi-tenant data isolation.
#
# Simulates what happens AFTER authentication (Dex + OAuth2 Proxy + ADFS/OIDC):
#   - OAuth2 Proxy authenticates the user via Dex/ADFS
#   - OAuth2 Proxy injects X-Forwarded-User header into every request
#   - Open Notebook reads the header and routes to per-user SurrealDB database
#
# This script bypasses the auth stack and injects headers directly with curl,
# which is exactly what the real proxy does after authentication succeeds.
#
# Prerequisites:
#   - Docker (for SurrealDB)
#   - Python 3.11+ with project deps (uv sync)
#
# Usage:
#   ./tests/test_multi_tenant_e2e.sh
#
# What it tests:
#   1. Health endpoint works without auth header
#   2. API rejects requests without X-Forwarded-User (401)
#   3. Alice creates a notebook — succeeds
#   4. Alice lists notebooks — sees her notebook
#   5. Bob lists notebooks — sees nothing (data isolation)
#   6. Bob creates a notebook — succeeds
#   7. Bob lists notebooks — sees only his notebook
#   8. Alice lists notebooks — still sees only her notebook
#   9. Cleanup
#
set -euo pipefail

API="http://localhost:5055"
SURREAL_CONTAINER="surrealdb-multitest"
SURREAL_PORT=8000
API_PID=""
PASS=0
FAIL=0
TOTAL=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Helpers ─────────────────────────────────────────────────────────────────

log()  { echo -e "${YELLOW}[TEST]${NC} $*"; }
pass() { PASS=$((PASS + 1)); TOTAL=$((TOTAL + 1)); echo -e "  ${GREEN}✓ PASS${NC}: $1"; }
fail() { FAIL=$((FAIL + 1)); TOTAL=$((TOTAL + 1)); echo -e "  ${RED}✗ FAIL${NC}: $1 — $2"; }

cleanup() {
    log "Cleaning up..."
    [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null && wait "$API_PID" 2>/dev/null || true
    docker rm -f "$SURREAL_CONTAINER" 2>/dev/null || true
    log "Done."
}
trap cleanup EXIT

assert_status() {
    local description="$1" expected="$2" actual="$3"
    if [ "$actual" -eq "$expected" ]; then
        pass "$description"
    else
        fail "$description" "expected HTTP $expected, got $actual"
    fi
}

assert_json_count() {
    local description="$1" expected="$2" json="$3"
    local count
    count=$(echo "$json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if not isinstance(data, list):
    print('-2')  # Not a list (e.g. error object)
else:
    print(len(data))
" 2>/dev/null || echo "-1")
    if [ "$count" = "-2" ]; then
        fail "$description" "response is not a JSON array"
    elif [ "$count" -eq "$expected" ]; then
        pass "$description"
    else
        fail "$description" "expected $expected items, got $count"
    fi
}

assert_json_field() {
    local description="$1" field="$2" expected="$3" json="$4"
    local actual
    actual=$(echo "$json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('$field',''))" 2>/dev/null || echo "")
    if [ "$actual" = "$expected" ]; then
        pass "$description"
    else
        fail "$description" "expected $field='$expected', got '$actual'"
    fi
}

wait_for_url() {
    local url="$1" max_wait="${2:-60}" elapsed=0
    while ! curl -sf "$url" > /dev/null 2>&1; do
        sleep 2
        elapsed=$((elapsed + 2))
        if [ "$elapsed" -ge "$max_wait" ]; then
            echo "Timeout waiting for $url after ${max_wait}s"
            return 1
        fi
    done
}

# ── Start SurrealDB ────────────────────────────────────────────────────────

log "Starting SurrealDB container..."
docker rm -f "$SURREAL_CONTAINER" 2>/dev/null || true
docker run -d --name "$SURREAL_CONTAINER" \
    -p "${SURREAL_PORT}:8000" \
    surrealdb/surrealdb:latest \
    start --user root --pass root 2>/dev/null

log "Waiting for SurrealDB..."
wait_for_url "http://localhost:${SURREAL_PORT}/health" 30
log "SurrealDB ready."

# ── Start API in multi-tenant mode ─────────────────────────────────────────

log "Starting API with MULTI_TENANT_MODE=true..."
cd "$(dirname "$0")/.."

export MULTI_TENANT_MODE=true
export SURREAL_URL="ws://localhost:${SURREAL_PORT}/rpc"
export SURREAL_USER=root
export SURREAL_PASSWORD=root
export SURREAL_NAMESPACE=open_notebook
export SURREAL_DATABASE=open_notebook

# Start API in background
uv run uvicorn api.main:app --host 0.0.0.0 --port 5055 &
API_PID=$!

log "Waiting for API (PID=$API_PID)..."
wait_for_url "${API}/health" 120
log "API ready."

echo ""
echo "================================================================"
echo "  Multi-Tenant E2E Tests"
echo "  Simulating: Dex → OAuth2 Proxy → X-Forwarded-User header"
echo "================================================================"
echo ""

# ── Test 1: Health (no auth needed) ────────────────────────────────────────

log "Test 1: Health endpoint (no auth header required)"
status=$(curl -s -o /dev/null -w "%{http_code}" "${API}/health")
assert_status "GET /health returns 200 without header" 200 "$status"

# ── Test 2: Reject missing header ──────────────────────────────────────────

log "Test 2: API rejects requests without X-Forwarded-User"
status=$(curl -s -o /dev/null -w "%{http_code}" "${API}/api/notebooks")
assert_status "GET /api/notebooks without header returns 401" 401 "$status"

# ── Test 3: Reject empty header ────────────────────────────────────────────

log "Test 3: API rejects empty X-Forwarded-User"
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-Forwarded-User: " "${API}/api/notebooks")
assert_status "GET /api/notebooks with empty header returns 401" 401 "$status"

# ── Test 4: Alice creates a notebook ───────────────────────────────────────
# This simulates: Alice logged in via ADFS → Dex → OAuth2 Proxy
# OAuth2 Proxy sets X-Forwarded-User: alice on every request

log "Test 4: Alice creates a notebook (simulating post-OAuth2-Proxy request)"
alice_create=$(curl -s -w "\n%{http_code}" \
    -X POST "${API}/api/notebooks" \
    -H "Content-Type: application/json" \
    -H "X-Forwarded-User: alice" \
    -d '{"name": "Alice Research", "description": "Alice private notebook"}')
alice_create_status=$(echo "$alice_create" | tail -1)
alice_create_body=$(echo "$alice_create" | sed '$d')
assert_status "Alice POST /api/notebooks returns 200" 200 "$alice_create_status"

# Extract notebook ID for later cleanup
alice_notebook_id=$(echo "$alice_create_body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # Handle both direct response and nested response
    if isinstance(data, dict) and 'id' in data:
        print(data['id'])
    elif isinstance(data, list) and len(data) > 0:
        print(data[0].get('id', ''))
    else:
        print('')
except: print('')
" 2>/dev/null)
log "  Alice's notebook ID: $alice_notebook_id"

# ── Test 5: Alice sees her notebook ────────────────────────────────────────

log "Test 5: Alice lists notebooks — should see her notebook"
alice_list=$(curl -s \
    -H "X-Forwarded-User: alice" \
    "${API}/api/notebooks")
assert_json_count "Alice sees 1 notebook" 1 "$alice_list"

# ── Test 6: Bob sees nothing (DATA ISOLATION) ─────────────────────────────
# Bob also authenticated via ADFS → Dex → OAuth2 Proxy
# But his database is completely separate from Alice's

log "Test 6: Bob lists notebooks — should see NOTHING (data isolation)"
bob_list=$(curl -s \
    -H "X-Forwarded-User: bob" \
    "${API}/api/notebooks")
assert_json_count "Bob sees 0 notebooks (isolated from Alice)" 0 "$bob_list"

# ── Test 7: Bob creates his own notebook ───────────────────────────────────

log "Test 7: Bob creates a notebook"
bob_create=$(curl -s -w "\n%{http_code}" \
    -X POST "${API}/api/notebooks" \
    -H "Content-Type: application/json" \
    -H "X-Forwarded-User: bob" \
    -d '{"name": "Bob Notes", "description": "Bob private notebook"}')
bob_create_status=$(echo "$bob_create" | tail -1)
assert_status "Bob POST /api/notebooks returns 200" 200 "$bob_create_status"

# ── Test 8: Bob sees only his notebook ─────────────────────────────────────

log "Test 8: Bob lists notebooks — should see only his"
bob_list2=$(curl -s \
    -H "X-Forwarded-User: bob" \
    "${API}/api/notebooks")
assert_json_count "Bob sees 1 notebook" 1 "$bob_list2"

# ── Test 9: Alice still sees only her notebook ─────────────────────────────

log "Test 9: Alice lists notebooks — still sees only hers"
alice_list2=$(curl -s \
    -H "X-Forwarded-User: alice" \
    "${API}/api/notebooks")
assert_json_count "Alice still sees 1 notebook (not Bob's)" 1 "$alice_list2"

# ── Test 10: Email-style user (simulating ADFS UPN) ────────────────────────
# ADFS typically sends userPrincipalName like user@domain.com

log "Test 10: Email-style user (ADFS UPN format: carol@company.com)"
carol_create=$(curl -s -w "\n%{http_code}" \
    -X POST "${API}/api/notebooks" \
    -H "Content-Type: application/json" \
    -H "X-Forwarded-User: carol@company.com" \
    -d '{"name": "Carol Work", "description": "Carol via ADFS"}')
carol_create_status=$(echo "$carol_create" | tail -1)
assert_status "carol@company.com POST /api/notebooks returns 200" 200 "$carol_create_status"

carol_list=$(curl -s \
    -H "X-Forwarded-User: carol@company.com" \
    "${API}/api/notebooks")
assert_json_count "carol@company.com sees 1 notebook" 1 "$carol_list"

# Verify Alice still isolated from carol
alice_list3=$(curl -s \
    -H "X-Forwarded-User: alice" \
    "${API}/api/notebooks")
assert_json_count "Alice still sees 1 notebook (isolated from carol)" 1 "$alice_list3"

# ── Summary ────────────────────────────────────────────────────────────────

echo ""
echo "================================================================"
echo "  Results: $PASS passed, $FAIL failed, $TOTAL total"
echo "================================================================"
echo ""
echo "Architecture tested:"
echo "  User → [ADFS/OIDC] → [Dex] → [OAuth2 Proxy] → X-Forwarded-User → API"
echo "  Each user gets: SurrealDB database 'user_<name>_<hash>'"
echo "    alice        → user_alice_2bd806c97f0e"
echo "    bob          → user_bob_81b637d8fcd2"
echo "    carol@co.com → user_carol_company_com_3dec473b35fb"
echo ""

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
