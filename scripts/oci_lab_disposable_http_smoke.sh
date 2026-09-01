#!/usr/bin/env sh
set -eu

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml"

fail() {
  printf '%s\n' "[oci-lab-disposable-http-smoke] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-lab-disposable-http-smoke] OK: $1"
}

[ -f docker-compose.yml ] || fail "run from repository root"
[ -f docker-compose.oci.yml ] || fail "docker-compose.oci.yml missing"
[ -f backend/scripts/test_ready_http_smoke.py ] || fail "backend/scripts/test_ready_http_smoke.py missing"

docker compose $COMPOSE_FILES ps || fail "compose ps failed"

if docker compose $COMPOSE_FILES config | grep -E "published:" >/tmp/sgi-published-ports.txt; then
  fail "compose config publishes host ports"
fi
ok "compose config publishes no host ports"

docker compose $COMPOSE_FILES exec -T backend python scripts/test_ready_http_smoke.py \
  || fail "disposable HTTP smoke failed"
ok "disposable HTTP smoke passed"

docker compose $COMPOSE_FILES exec -T backend sh -c \
  'python - <<"PY"
import json
import urllib.error
import urllib.request

try:
    response = urllib.request.urlopen("http://localhost:8000/ready")
    status = response.status
    payload = json.loads(response.read().decode("utf-8"))
except urllib.error.HTTPError as exc:
    status = exc.code
    payload = json.loads(exc.read().decode("utf-8"))

assert status == 503, status
assert payload.get("ready_for_real_data") is False, payload
print(payload.get("state"), payload.get("ready_for_real_data"))
PY' >/tmp/sgi-disposable-ready-summary.txt \
  || fail "ready_for_real_data gate check failed"
ok "ready_for_real_data remains closed ($(cat /tmp/sgi-disposable-ready-summary.txt))"

ok "lab disposable HTTP journey passed without real data or real seed execution"
