#!/usr/bin/env sh
set -eu

EXPECTED_SHA="${SGI_CERT_EXPECTED_SHA:-}"

fail() {
  printf '%s\n' "[oci-cert-test-go] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-cert-test-go] OK: $1"
}

[ -f docker-compose.yml ] || fail "run from repository root"
[ -f scripts/oci_seed_contract_validation.sh ] || fail "seed/bootstrap contract wrapper missing"
[ -f scripts/oci_lab_disposable_http_smoke.sh ] || fail "disposable HTTP smoke wrapper missing"
command -v git >/dev/null 2>&1 || fail "git is required"

branch="$(git branch --show-current)"
[ "$branch" = "stable-15jun" ] || fail "branch must be stable-15jun, got $branch"
sha="$(git rev-parse HEAD)"
[ -z "$EXPECTED_SHA" ] || [ "$sha" = "$EXPECTED_SHA" ] || fail "HEAD $sha differs from expected $EXPECTED_SHA"
[ -z "$(git status --porcelain)" ] || fail "working tree must be clean"
ok "git baseline $sha on stable-15jun with clean tree"

printf '%s\n' "[oci-cert-test-go] Revalidating system-bootstrap.v4 and seed contracts without real execution"
sh scripts/oci_seed_contract_validation.sh
ok "system bootstrap and seed contracts passed without real seed execution"

printf '%s\n' "[oci-cert-test-go] Revalidating disposable HTTP journey and closed real-data readiness"
sh scripts/oci_lab_disposable_http_smoke.sh
ok "disposable HTTP journey passed with real-data gate closed"

[ -z "$(git status --porcelain)" ] || fail "CERT-03 dirtied working tree"
ok "working tree remained clean"

printf '%s\n' "TEST-GO-DISPOSABLE:PASS sha=$sha"
printf '%s\n' "REAL-DATA-GATE:CLOSED"
printf '%s\n' "[oci-cert-test-go] CERT-03 passed: SGI v2 is cleared for integrated testing with fictitious/disposable data only"
printf '%s\n' "[oci-cert-test-go] This does not authorize real users, real portfolios, CSV import, real seeds, snapshots, or ready_for_real_data=true"
