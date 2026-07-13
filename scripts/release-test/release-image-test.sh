#!/bin/bash
# Release image gate: fresh-install and upgrade tests against built Docker images.
#
# Usage: release-image-test.sh <fresh|upgrade|all> <new-image> [old-image]
#   e.g. release-image-test.sh all lfnovo/open_notebook:1.12.0 lfnovo/open_notebook:1.11.0
#
# IMPORTANT: `make docker-build-local` tags the build with the CURRENT pyproject
# version. If that version matches a published release, `docker pull` the
# genuine old tag first or the upgrade test will compare the new build against
# itself.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="$DIR/docker-compose.release-test.yml"
NEW_IMAGE="${2:?usage: release-image-test.sh <fresh|upgrade|all> <new-image> [old-image]}"
OLD_IMAGE="${3:-}"
PASS=0; FAIL=0

ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
check() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected=$2, got=$3)"; fi; }

# Each phase gets its own ports so a leaked container can never answer for the
# wrong stack (learned the hard way: a leftover fresh-install app once served
# the whole upgrade test).
set_ports() { API_PORT=$1; FE_PORT=$2; PROXY_PORT=$3; API="http://localhost:$1"; FE="http://localhost:$2"; PROXY="http://localhost:$3"; }

compose_env() { env APP_IMAGE="$1" DATA_DIR="$2" API_PORT="$API_PORT" FE_PORT="$FE_PORT" PROXY_PORT="$PROXY_PORT" docker compose -p "$3" -f "$COMPOSE" "${@:4}"; }

compose_up() { # <image> <datadir> <project>
  local OUT
  OUT=$(compose_env "$1" "$2" "$3" up -d --quiet-pull 2>&1)
  if echo "$OUT" | grep -qi "error"; then
    bad "compose up ($3): $(echo "$OUT" | grep -i error | head -1)"
    return 1
  fi
  local RUNNING
  RUNNING=$(docker inspect "$3-app-1" --format '{{.State.Running}}' 2>/dev/null)
  check "container $3-app-1 running" "true" "$RUNNING"
}

compose_down() { # <project> <datadir-to-remove (optional)>
  compose_env unused /tmp/unused "$1" down -v >/dev/null 2>&1
  if docker ps --format '{{.Names}}' | grep -q "^$1-"; then
    bad "teardown of $1 left containers running"
  fi
  [ -n "${2:-}" ] && rm -rf "$2"
}

wait_api() { # up to 150s (startup has ~50s of DB-wait backoff + migrations)
  for i in $(seq 1 30); do
    if curl -sf -m 5 -o /dev/null "$API/docs"; then return 0; fi
    sleep 5
  done
  return 1
}

seed_and_verify() {
  NB=$(curl -s -X POST "$API/api/notebooks" -H "Content-Type: application/json" \
    -d '{"name":"release-probe","description":"release test seed"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])" 2>/dev/null)
  [ -z "$NB" ] && { bad "create notebook"; return 1; }
  ok "create notebook ($NB)"
  SRC=$(curl -s -X POST "$API/api/sources" -F "type=text" -F "notebooks=[\"$NB\"]" \
    -F "content=Release test content. The Turing test evaluates machine intelligence." \
    -F "title=release-probe-source" -F "async_processing=true" -F "embed=false" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])" 2>/dev/null)
  [ -z "$SRC" ] && { bad "create source"; return 1; }
  ok "create source ($SRC)"
  ST=""
  for i in $(seq 1 24); do
    ST=$(curl -s "$API/api/sources/$SRC/status" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
    [ "$ST" = "completed" ] && break
    sleep 5
  done
  check "in-image worker processed source" "completed" "$ST"
  FT=$(curl -s "$API/api/sources/$SRC" | python3 -c "import json,sys; d=json.load(sys.stdin); print('yes' if d.get('full_text') else 'no')" 2>/dev/null)
  check "full_text present" "yes" "$FT"
}

fresh_test() {
  echo "═══ FRESH INSTALL — $NEW_IMAGE"
  set_ports 15055 18502 18080
  local DD; DD=$(mktemp -d /tmp/onrel-fresh-XXXX)
  compose_up "$NEW_IMAGE" "$DD" onrelfresh || { compose_down onrelfresh "$DD"; return 1; }
  if wait_api; then ok "API up (migrations ran on boot)"; else
    bad "API did not come up in 150s"; docker logs onrelfresh-app-1 2>&1 | tail -20
    compose_down onrelfresh "$DD"; return 1
  fi
  N=$(curl -s "$API/api/notebooks" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
  check "GET /api/notebooks on a virgin database" "0" "$N"
  seed_and_verify
  for f in type title created updated insights_count embedded; do
    S=$(curl -s -o /dev/null -w '%{http_code}' "$API/api/sources?sort_by=$f&limit=2")
    check "sort_by=$f" "200" "$S"
  done
  S=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "$FE")
  if [ "$S" = "200" ] || [ "$S" = "307" ]; then ok "frontend responds ($S)"; else bad "frontend ($S)"; fi
  C=$(curl -s -m 10 "$PROXY/config")
  echo "$C" | grep -q apiUrl && ok "/config via nginx: $C" || bad "/config via nginx: $C"
  # Malformed Host: nginx may reject with 400 (correct) or the app falls back
  # (200). What must never happen is a 5xx.
  C=$(curl -s -m 10 -H 'Host: bad<host>!' "$PROXY/config" -o /dev/null -w '%{http_code}')
  if [ "$C" = "200" ] || [ "$C" = "400" ]; then ok "/config via nginx with malformed Host -> $C (no 5xx)"; else bad "/config malformed Host -> $C"; fi
  compose_down onrelfresh "$DD"
  echo
}

upgrade_test() {
  if [ -z "$OLD_IMAGE" ]; then echo "═══ UPGRADE skipped: no old image given"; return 0; fi
  echo "═══ UPGRADE — $OLD_IMAGE -> $NEW_IMAGE"
  set_ports 25055 28502 28080
  local DD; DD=$(mktemp -d /tmp/onrel-upg-XXXX)
  echo "-- phase 1: boot $OLD_IMAGE and seed"
  compose_up "$OLD_IMAGE" "$DD" onrelupg || { compose_down onrelupg "$DD"; return 1; }
  IMG=$(docker inspect onrelupg-app-1 --format '{{.Config.Image}}' 2>/dev/null)
  check "phase 1 runs the old image" "$OLD_IMAGE" "$IMG"
  if wait_api; then ok "old image up"; else
    bad "old image did not come up"; compose_down onrelupg "$DD"; return 1
  fi
  seed_and_verify
  echo "-- phase 2: swap to the new image on the SAME volume"
  compose_env unused /tmp/unused onrelupg stop app >/dev/null 2>&1
  compose_env unused /tmp/unused onrelupg rm -f app >/dev/null 2>&1
  compose_up "$NEW_IMAGE" "$DD" onrelupg || { compose_down onrelupg "$DD"; return 1; }
  IMG=$(docker inspect onrelupg-app-1 --format '{{.Config.Image}}' 2>/dev/null)
  check "phase 2 runs the new image" "$NEW_IMAGE" "$IMG"
  if wait_api; then ok "new image up on old data"; else
    bad "new image did not come up on old data"; docker logs onrelupg-app-1 2>&1 | tail -20
    compose_down onrelupg "$DD"; return 1
  fi
  FOUND=$(curl -s "$API/api/notebooks" | python3 -c "
import json,sys
nbs=json.load(sys.stdin)
print('yes' if any(n.get('name')=='release-probe' for n in nbs) else 'no')" 2>/dev/null)
  check "notebook seeded on old image survived the upgrade" "yes" "$FOUND"
  S=$(curl -s -o /dev/null -w '%{http_code}' "$API/api/sources?sort_by=title&limit=2")
  check "sort_by=title after upgrade" "200" "$S"
  echo "  phase 2 migration log:"
  docker logs onrelupg-app-1 2>&1 | grep -i "migrat" | tail -5 | sed 's/^/    /'
  compose_down onrelupg "$DD"
  echo
}

case "${1:-all}" in
  fresh)   fresh_test ;;
  upgrade) upgrade_test ;;
  all)     fresh_test; upgrade_test ;;
esac

echo "═══ RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
