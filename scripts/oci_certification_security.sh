#!/usr/bin/env sh
set -eu

EXPECTED_SHA="${SGI_CERT_EXPECTED_SHA:-}"
TRIVY_IMAGE="aquasec/trivy:0.66.0"
GITLEAKS_IMAGE="zricethezav/gitleaks:v8.28.0"
HADOLINT_IMAGE="hadolint/hadolint:v2.14.0-alpine"
BACKEND_IMAGE="sgi-v2-backend-cert-security"
FRONTEND_IMAGE="sgi-v2-frontend-cert-security"

fail() {
  printf '%s\n' "[oci-cert-security] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-cert-security] OK: $1"
}

[ -f docker-compose.yml ] || fail "run from repository root"
[ -f backend/Dockerfile ] || fail "backend/Dockerfile missing"
[ -f frontend/Dockerfile ] || fail "frontend/Dockerfile missing"
command -v git >/dev/null 2>&1 || fail "git is required"
command -v docker >/dev/null 2>&1 || fail "docker is required"

branch="$(git branch --show-current)"
[ "$branch" = "stable-15jun" ] || fail "branch must be stable-15jun, got $branch"
sha="$(git rev-parse HEAD)"
[ -z "$EXPECTED_SHA" ] || [ "$sha" = "$EXPECTED_SHA" ] || fail "HEAD $sha differs from expected $EXPECTED_SHA"
[ -z "$(git status --porcelain)" ] || fail "working tree must be clean"
ok "git baseline $sha on stable-15jun with clean tree"

printf '%s\n' "[oci-cert-security] Running Gitleaks against full Git history"
docker run --rm -v "$(pwd):/repo" -w /repo "$GITLEAKS_IMAGE" git --no-banner --redact --exit-code 1
ok "Gitleaks found no blocking secret leak"

printf '%s\n' "[oci-cert-security] Running Trivy filesystem HIGH/CRITICAL gate"
docker run --rm -v "$(pwd):/repo" -w /repo "$TRIVY_IMAGE" fs \
  --scanners vuln,secret,misconfig \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --ignorefile .trivyignore \
  --exit-code 1 .
ok "Trivy filesystem HIGH/CRITICAL gate passed"

printf '%s\n' "[oci-cert-security] Running Hadolint gates"
docker run --rm -i "$HADOLINT_IMAGE" hadolint --ignore DL3008 --ignore DL3009 - < backend/Dockerfile
docker run --rm -i "$HADOLINT_IMAGE" hadolint --ignore DL3016 --ignore DL3018 - < frontend/Dockerfile
ok "Hadolint backend/frontend gates passed"

printf '%s\n' "[oci-cert-security] Building runtime images with certified revision label"
docker build --target runtime --build-arg APP_COMMIT_SHA="$sha" -t "$BACKEND_IMAGE:$sha" ./backend
docker build --target runtime -t "$FRONTEND_IMAGE:$sha" ./frontend
ok "runtime images built"

printf '%s\n' "[oci-cert-security] Running Trivy backend runtime image HIGH/CRITICAL gate"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$TRIVY_IMAGE" image \
  --severity HIGH,CRITICAL --ignore-unfixed --ignorefile /dev/null --exit-code 1 "$BACKEND_IMAGE:$sha"
ok "backend runtime image scan passed"

printf '%s\n' "[oci-cert-security] Running Trivy frontend runtime image HIGH/CRITICAL gate"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$TRIVY_IMAGE" image \
  --severity HIGH,CRITICAL --ignore-unfixed --ignorefile /dev/null --exit-code 1 "$FRONTEND_IMAGE:$sha"
ok "frontend runtime image scan passed"

[ -z "$(git status --porcelain)" ] || fail "security certification commands dirtied the working tree"
ok "working tree remained clean"

printf '%s\n' "[oci-cert-security] CERT-01B local security gate passed for $sha"
printf '%s\n' "[oci-cert-security] Reconcile GitHub CodeQL/Code Scanning, Dependabot Security Alerts and Secret Scanning separately before TEST-GO"
