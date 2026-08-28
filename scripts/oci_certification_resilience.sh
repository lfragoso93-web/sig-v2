#!/usr/bin/env sh
set -eu

EXPECTED_SHA="${SGI_CERT_EXPECTED_SHA:-}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml"
MARKER_TABLE="sgi_cert_persistence_marker"
MARKER_VALUE="cert02-$(date +%s)"

fail() {
  printf '%s\n' "[oci-cert-resilience] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-cert-resilience] OK: $1"
}

wait_healthy() {
  service="$1"
  retries="${2:-60}"
  i=0
  while [ "$i" -lt "$retries" ]; do
    cid="$($COMPOSE ps -q "$service")"
    if [ -n "$cid" ]; then
      status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)"
      if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
        return 0
      fi
    fi
    i=$((i + 1))
    sleep 2
  done
  return 1
}

[ -f docker-compose.oci.yml ] || fail "run from repository root"
command -v git >/dev/null 2>&1 || fail "git required"
command -v docker >/dev/null 2>&1 || fail "docker required"

branch="$(git branch --show-current)"
[ "$branch" = "stable-15jun" ] || fail "branch must be stable-15jun, got $branch"
sha="$(git rev-parse HEAD)"
[ -z "$EXPECTED_SHA" ] || [ "$sha" = "$EXPECTED_SHA" ] || fail "HEAD $sha differs from expected $EXPECTED_SHA"
[ -z "$(git status --porcelain)" ] || fail "working tree must be clean"
ok "git baseline $sha on stable-15jun with clean tree"

printf '%s\n' "[oci-cert-resilience] Validating OCI compose contract"
$COMPOSE config >/tmp/sgi-cert02-compose.yml
if grep -Eq 'published:' /tmp/sgi-cert02-compose.yml; then
  fail "OCI compose unexpectedly publishes host ports"
fi
ok "OCI compose publishes no host ports"

printf '%s\n' "[oci-cert-resilience] Recording database persistence marker"
$COMPOSE exec -T db psql -U "${POSTGRES_USER:-sgi}" -d "${POSTGRES_DB:-sgi}" -v ON_ERROR_STOP=1 <<SQL
CREATE TABLE IF NOT EXISTS ${MARKER_TABLE} (
  id integer PRIMARY KEY,
  marker text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO ${MARKER_TABLE} (id, marker)
VALUES (1, '${MARKER_VALUE}')
ON CONFLICT (id) DO UPDATE SET marker = EXCLUDED.marker, created_at = now();
SQL
ok "database marker written"

printf '%s\n' "[oci-cert-resilience] Capturing persistent volume identity"
volume_name="$($COMPOSE config --volumes | grep -E 'postgres_data' | head -n1 || true)"
[ -n "$volume_name" ] || fail "postgres_data volume not declared"
volume_before="$(docker volume ls --format '{{.Name}}' | grep -E '(^|_)postgres_data$' | head -n1 || true)"
[ -n "$volume_before" ] || fail "postgres_data Docker volume not found"
ok "PostgreSQL persistent volume present ($volume_before)"

printf '%s\n' "[oci-cert-resilience] Restarting application services without removing volumes"
$COMPOSE restart db redis backend frontend
wait_healthy db 90 || fail "db did not recover after restart"
wait_healthy redis 60 || fail "redis did not recover after restart"
wait_healthy backend 90 || fail "backend did not recover after restart"
wait_healthy frontend 60 || fail "frontend did not recover after restart"
ok "services recovered after restart"

persisted="$($COMPOSE exec -T db psql -U "${POSTGRES_USER:-sgi}" -d "${POSTGRES_DB:-sgi}" -Atqc "SELECT marker FROM ${MARKER_TABLE} WHERE id=1;")"
[ "$persisted" = "$MARKER_VALUE" ] || fail "database marker was not preserved across restart"
volume_after="$(docker volume ls --format '{{.Name}}' | grep -E '(^|_)postgres_data$' | head -n1 || true)"
[ "$volume_before" = "$volume_after" ] || fail "PostgreSQL volume identity changed across restart"
ok "PostgreSQL data and volume identity persisted across restart"

printf '%s\n' "[oci-cert-resilience] Removing disposable persistence marker before schema drift validation"
$COMPOSE exec -T db psql -U "${POSTGRES_USER:-sgi}" -d "${POSTGRES_DB:-sgi}" -v ON_ERROR_STOP=1 -c "DROP TABLE IF EXISTS ${MARKER_TABLE};" >/dev/null
if $COMPOSE exec -T db psql -U "${POSTGRES_USER:-sgi}" -d "${POSTGRES_DB:-sgi}" -Atqc "SELECT to_regclass('public.${MARKER_TABLE}');" | grep -q .; then
  fail "disposable persistence marker table still exists before drift gate"
fi
ok "disposable marker removed before drift validation"

printf '%s\n' "[oci-cert-resilience] Validating migration head after restart"
current="$($COMPOSE exec -T backend alembic current 2>&1)"
printf '%s\n' "$current"
printf '%s\n' "$current" | grep -q '(head)' || fail "alembic current is not at head after restart"
$COMPOSE exec -T backend python -m app.governance.alembic_drift_gate
ok "migration head and drift gate passed after restart"

printf '%s\n' "[oci-cert-resilience] Testing Redis fail-open behavior"
$COMPOSE stop redis >/dev/null
sleep 2
backend_cid="$($COMPOSE ps -q backend)"
[ -n "$backend_cid" ] || fail "backend container missing during Redis outage"
backend_status="$(docker inspect -f '{{.State.Status}}' "$backend_cid")"
[ "$backend_status" = "running" ] || fail "backend stopped when Redis became unavailable"

$COMPOSE exec -T backend python - <<'PY'
import asyncio
from app.core import cache

async def main():
    cache._redis_client = None
    value = await cache.cache_get("cert02:redis-outage")
    if value is not None:
        raise SystemExit("cache_get returned unexpected value during Redis outage")
    await cache.cache_set("cert02:redis-outage", {"ok": True}, ttl=5)
    await cache.cache_delete("cert02:redis-outage")
    await cache.cache_delete_pattern("cert02:*")
    print("REDIS-FAIL-OPEN:PASS")

asyncio.run(main())
PY
ok "Redis outage kept cache boundary fail-open"

printf '%s\n' "[oci-cert-resilience] Recovering Redis"
$COMPOSE start redis >/dev/null
wait_healthy redis 60 || fail "redis did not recover"
$COMPOSE exec -T backend python - <<'PY'
import asyncio
from app.core import cache

async def main():
    cache._redis_client = None
    client = await cache.get_redis()
    if client is None:
        raise SystemExit("Redis client did not recover")
    pong = await client.ping()
    if not pong:
        raise SystemExit("Redis ping failed after recovery")
    print("REDIS-RECOVERY:PASS")

asyncio.run(main())
PY
ok "Redis recovered and backend cache boundary reconnected"

[ -z "$(git status --porcelain)" ] || fail "resilience certification dirtied working tree"
ok "working tree remained clean"

printf '%s\n' "[oci-cert-resilience] CERT-02 resilience gate passed for $sha"
printf '%s\n' "[oci-cert-resilience] ready_for_real_data remains unchanged; this gate does not authorize real seeds or imports"
