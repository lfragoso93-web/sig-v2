#!/usr/bin/env sh
set -eu
umask 077

CLOUDFLARED_LOG="/tmp/sgi-cloudflared.log"
CLOUDFLARED_SANITIZED_LOG="/tmp/sgi-cloudflared.sanitized.log"
trap 'rm -f -- "${CLOUDFLARED_LOG}" "${CLOUDFLARED_SANITIZED_LOG}"' EXIT

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

docker compose $COMPOSE_FILES logs --tail=120 cloudflared >"${CLOUDFLARED_LOG}" 2>&1 \
  || fail "cloudflared logs unavailable"

# cloudflared can emit masked fields such as token:***** and long precheck borders.
# Redact known-safe masked/report values before looking for real secrets.
sed -E 's/(token[=:])[[:space:]]*\*+/\1<masked>/Ig; s/(CLOUDFLARE_TUNNEL_TOKEN=)\*+/\1<masked>/g; s/INF \+[A-Za-z0-9_-]{80,}\+/INF +<precheck-border>+/g' \
  "${CLOUDFLARED_LOG}" >"${CLOUDFLARED_SANITIZED_LOG}"

TOKEN_PATTERN="CLOUDFLARE_TUNNEL_TOKEN=[^[:space:]]+|[A-Za-z0-9_-]{80,}"
if grep -E "$TOKEN_PATTERN" "${CLOUDFLARED_SANITIZED_LOG}" >/dev/null; then
  # Report only metadata for manual diagnosis; never print a candidate value.
  grep -nEo "$TOKEN_PATTERN" /tmp/sgi-cloudflared.sanitized.log | awk -F: '
    {
      line_number = $1
      candidate = $0
      sub(/^[^:]*:/, "", candidate)
      classes = (candidate ~ /[a-z]/ ? "l" : "-")
      classes = classes (candidate ~ /[A-Z]/ ? "u" : "-")
      classes = classes (candidate ~ /[0-9]/ ? "d" : "-")
      classes = classes (index(candidate, "-") > 0 ? "h" : "-")
      classes = classes (index(candidate, "_") > 0 ? "u" : "-")
      classes = classes (index(candidate, "+") > 0 ? "p" : "-")
      printf "[oci-smoke-test] token-like candidate line=%s length=%d classes=%s eyJ_prefix=%d%c", line_number, length(candidate), classes, candidate ~ /^eyJ/, 10
    }
  ' >&2
  fail "cloudflared logs may contain token-like content (candidate values suppressed)"
fi
ok "cloudflared logs captured without obvious token pattern"

if docker compose $COMPOSE_FILES config | grep -E "published:" >/tmp/sgi-published-ports.txt; then
  fail "compose config publishes host ports"
fi
ok "compose config publishes no host ports"

printf '%s\n' "[oci-smoke-test] smoke test passed"
