#!/usr/bin/env sh
set -eu

fail() {
  printf '%s\n' "[oci-source-tree-check] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-source-tree-check] OK: $1"
}

[ -f docker-compose.yml ] || fail "run from extracted repository root"
[ -f docker-compose.prod.yml ] || fail "docker-compose.prod.yml missing"
[ -f docker-compose.oci.yml ] || fail "docker-compose.oci.yml missing"
[ -f .env.oci.example ] || fail ".env.oci.example missing"
ok "required deployment files are present"

[ ! -f .env ] || fail ".env must not exist in transferred source"
[ ! -d .git ] || fail ".git must not exist in transferred source package"
[ ! -d node_modules ] || fail "root node_modules must not exist in transferred source"
[ ! -d frontend/node_modules ] || fail "frontend node_modules must not exist in transferred source"
[ ! -d backend/node_modules ] || fail "backend node_modules must not exist in transferred source"
[ ! -d artifacts/pre-prod-rebuild ] || fail "backup artifacts must not exist in transferred source"
ok "local secrets and runtime artifacts are absent"

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "transferred source should be a git archive, not a working tree"
fi
ok "source is not a git working tree"

if command -v docker >/dev/null 2>&1; then
  CLOUDFLARE_TUNNEL_TOKEN=dummy-preflight-token BACKEND_WORKERS=1 \
    docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml config \
    > /tmp/sgi-compose-rendered.yml

  if grep -E "published:" /tmp/sgi-compose-rendered.yml >/tmp/sgi-published-ports.txt; then
    fail "OCI compose config publishes host ports"
  fi
  grep -q "cloudflared:" /tmp/sgi-compose-rendered.yml || fail "cloudflared service missing from rendered compose"
  ok "OCI compose renders without host ports"
else
  printf '%s\n' "[oci-source-tree-check] WARN: docker not available; compose render skipped"
fi

printf '%s\n' "[oci-source-tree-check] source tree check passed"

