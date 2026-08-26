#!/usr/bin/env sh
set -eu

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml"
PUBLIC_HOST="${SGI_PUBLIC_HOST:-https://sgi.lfconsultoria.dpdns.org}"
READY_STATUS=/tmp/sgi-ready.status

fail() {
  printf '%s\n' "[oci-lab-seed-readiness] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-lab-seed-readiness] OK: $1"
}

[ -f docker-compose.yml ] || fail "run from repository root"
[ -f scripts/oci_smoke_test.sh ] || fail "scripts/oci_smoke_test.sh missing"
[ -f scripts/oci_seed_contract_validation.sh ] || fail "scripts/oci_seed_contract_validation.sh missing"

sh scripts/oci_smoke_test.sh
ok "OCI smoke test passed"

sh scripts/oci_seed_contract_validation.sh
ok "seed/bootstrap contract validation passed"

docker compose $COMPOSE_FILES exec -T backend sh -c \
  'curl -sS -o /tmp/sgi-ready.json -w "%{http_code}" http://localhost:8000/ready' \
  > "$READY_STATUS" || true

status="$(cat "$READY_STATUS")"
[ "$status" = "503" ] || fail "backend /ready must stay 503 before real-data certification, got $status"

docker compose $COMPOSE_FILES exec -T backend sh -c \
  'python - <<"PY"
import json
payload = json.load(open("/tmp/sgi-ready.json"))
assert payload.get("ready_for_real_data") is False, payload
print(payload.get("state"), payload.get("ready_for_real_data"))
PY' >/tmp/sgi-ready-summary.txt
ok "backend /ready preserves ready_for_real_data=false ($(cat /tmp/sgi-ready-summary.txt))"

curl -fsSI "$PUBLIC_HOST" | sed -n '1,3p'
ok "public frontend hostname responded"

ok "lab is ready for controlled disposable-data seed rehearsal; real-data gates remain closed"
