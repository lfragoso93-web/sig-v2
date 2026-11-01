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

TOKEN_PATTERN="CLOUDFLARE_TUNNEL_TOKEN=[^[:space:]]+|[A-Za-z0-9_-]{80,}"
if grep -E "$TOKEN_PATTERN" /tmp/sgi-cloudflared.sanitized.log >/dev/null; then
  # Report only metadata for manual diagnosis; never print a candidate value.
  grep -nEo "$TOKEN_PATTERN" /tmp/sgi-cloudflared.sanitized.log | awk -F: '
    {
      line_number = $1
      candidate = $0
      sub(/^[^:]*:/, "", candidate)
      count = split(candidate, characters, "")
      for (i = 1; i <= count; i++) {
        if (!(characters[i] in seen)) {
          seen[characters[i]] = 1
          unique_count++
        }
      }
      printf "[oci-smoke-test] token-like candidate line=%s length=%d unique_chars=%d plus=%d hyphen=%d spaces=%d eyJ_prefix=%d%c", line_number, length(candidate), unique_count, index(candidate, "+") > 0, index(candidate, "-") > 0, candidate ~ /[[:space:]]/, candidate ~ /^eyJ/, 10
      delete seen
      unique_count = 0
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
