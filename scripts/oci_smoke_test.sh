#!/usr/bin/env sh
set -eu

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml"

fail() {
  printf '%s\n' "[oci-smoke-test] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-smoke-test] OK: $1"
}

[ -f docker-compose.yml ] || fail "run from repository root"
[ -f docker-compose.oci.yml ] || fail "docker-compose.oci.yml missing"

docker compose $COMPOSE_FILES ps || fail "compose ps failed"

docker compose $COMPOSE_FILES exec -T backend curl -fsS http://localhost:8000/health >/tmp/sgi-health.json \
  || fail "backend /health failed"
ok "backend /health succeeded"

docker compose $COMPOSE_FILES exec -T db pg_isready -U "${POSTGRES_USER:-sgi}" >/dev/null \
  || fail "postgres readiness failed"
ok "postgres ready"

docker compose $COMPOSE_FILES exec -T redis redis-cli ping | grep -q PONG \
  || fail "redis ping failed"
ok "redis pong"

docker compose $COMPOSE_FILES logs --tail=120 cloudflared >/tmp/sgi-cloudflared.log 2>&1 \
  || fail "cloudflared logs unavailable"

# cloudflared can emit masked fields such as token:***** and long precheck borders.
# Redact known-safe masked/report values before looking for real secrets.
sed -E 's/(token[=:])[[:space:]]*\*+/\1<masked>/Ig; s/(CLOUDFLARE_TUNNEL_TOKEN=)\*+/\1<masked>/g; s/INF \+[A-Za-z0-9_-]{80,}\+/INF +<precheck-border>+/g' \
  /tmp/sgi-cloudflared.log >/tmp/sgi-cloudflared.sanitized.log

if grep -E "CLOUDFLARE_TUNNEL_TOKEN=[^[:space:]]+|[A-Za-z0-9_-]{80,}" /tmp/sgi-cloudflared.sanitized.log >/dev/null; then
  fail "cloudflared logs may contain token-like content"
fi
ok "cloudflared logs captured without obvious token pattern"

if docker compose $COMPOSE_FILES config | grep -E "published:" >/tmp/sgi-published-ports.txt; then
  fail "compose config publishes host ports"
fi
ok "compose config publishes no host ports"

printf '%s\n' "[oci-smoke-test] smoke test passed"
