#!/usr/bin/env sh
set -eu

EXPECTED_SHA="${SGI_CERT_EXPECTED_SHA:-}"
BACKEND_CERT_IMAGE="sgi-v2-backend-cert"
CERT_NETWORK="sgi-v2-cert-net"
CERT_DB="sgi-v2-cert-db"
POSTGRES_IMAGE="postgres:16-alpine"
NODE_IMAGE="node:22-bookworm-slim"

fail() {
  printf '%s\n' "[oci-cert-quality] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-cert-quality] OK: $1"
}

cleanup() {
  docker rm -f "$CERT_DB" >/dev/null 2>&1 || true
  docker network rm "$CERT_NETWORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

[ -f docker-compose.yml ] || fail "run from repository root"
[ -f backend/requirements-test.txt ] || fail "backend/requirements-test.txt missing"
[ -f frontend/package-lock.json ] || fail "frontend/package-lock.json missing"
[ -f scripts/oci_smoke_test.sh ] || fail "scripts/oci_smoke_test.sh missing"
[ -f scripts/oci_seed_contract_validation.sh ] || fail "scripts/oci_seed_contract_validation.sh missing"
[ -f scripts/oci_lab_disposable_http_smoke.sh ] || fail "scripts/oci_lab_disposable_http_smoke.sh missing"
command -v git >/dev/null 2>&1 || fail "git is required"
command -v docker >/dev/null 2>&1 || fail "docker is required"

branch="$(git branch --show-current)"
[ "$branch" = "stable-15jun" ] || fail "branch must be stable-15jun, got $branch"
sha="$(git rev-parse HEAD)"
[ -z "$EXPECTED_SHA" ] || [ "$sha" = "$EXPECTED_SHA" ] || fail "HEAD $sha differs from expected $EXPECTED_SHA"
[ -z "$(git status --porcelain)" ] || fail "working tree must be clean"
ok "git baseline $sha on stable-15jun with clean tree"

printf '%s\n' "[oci-cert-quality] Building backend certification dependency image"
docker build --target deps -t "$BACKEND_CERT_IMAGE" ./backend
ok "backend certification image built"

docker network create "$CERT_NETWORK" >/dev/null
docker run -d --name "$CERT_DB" --network "$CERT_NETWORK" \
  -e POSTGRES_DB=sgi_ci \
  -e POSTGRES_USER=sgi \
  -e POSTGRES_PASSWORD=sgi \
  "$POSTGRES_IMAGE" >/dev/null

attempt=0
until docker exec "$CERT_DB" pg_isready -U sgi -d sgi_ci >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -lt 31 ] || fail "temporary PostgreSQL did not become ready"
  sleep 2
done
ok "temporary PostgreSQL ready"

printf '%s\n' "[oci-cert-quality] Running backend quality gates"
docker run --rm --network "$CERT_NETWORK" \
  -e DATABASE_URL=postgresql://sgi:sgi@sgi-v2-cert-db:5432/sgi_ci \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$(pwd)/backend:/app" \
  -w /app \
  "$BACKEND_CERT_IMAGE" sh -ec '
    pip install --disable-pip-version-check -q -r requirements-test.txt pip-audit
    flake8 app --max-line-length=120 --extend-ignore=E501,E221 --per-file-ignores="app/models/*.py:F821,F401"
    mypy app
    python -m compileall -q app tests
    python -c "import app.main; print(\"app.main OK\")"
    alembic upgrade head
    alembic current
    python -m app.governance.alembic_drift_gate
    pytest -qq -x --tb=line --disable-warnings
    pip-audit --ignore-vuln GHSA-xgmm-8j9v-c9wx
  '
ok "backend lint, typecheck, compile/import, fresh migration gate, pytest and pip-audit passed"

printf '%s\n' "[oci-cert-quality] Running frontend quality gates"
docker run --rm \
  -v "$(pwd)/frontend:/src:ro" \
  "$NODE_IMAGE" sh -ec '
    cp -a /src /tmp/frontend
    cd /tmp/frontend
    npm ci
    npm run lint
    npm run typecheck
    npm test -- --run --maxWorkers=1 --testTimeout=30000
    npm run build
    npx audit-ci
  '
ok "frontend install, lint, typecheck, tests, build and npm audit passed"

sh scripts/oci_smoke_test.sh
ok "OCI stack smoke passed"

sh scripts/oci_seed_contract_validation.sh
ok "seed/bootstrap contracts passed without real seed execution"

sh scripts/oci_lab_disposable_http_smoke.sh
ok "disposable HTTP smoke passed and readiness stayed closed"

[ -z "$(git status --porcelain)" ] || fail "certification commands dirtied the working tree"
ok "working tree remained clean"

printf '%s\n' "[oci-cert-quality] CERT-01A application quality gate passed for $sha"
printf '%s\n' "[oci-cert-quality] Run CERT-01B repository/image security scanners separately before TEST-GO"
