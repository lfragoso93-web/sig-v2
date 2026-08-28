#!/usr/bin/env sh
set -eu

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml"
COMMIT_SHA="${SGI_PREPROD_COMMIT_SHA:-}"
CONFIRMATION="${SGI_PREPROD_CONFIRMATION:-}"
START_DATE="${SGI_PREPROD_START_DATE:-}"
END_DATE="${SGI_PREPROD_END_DATE:-}"
ARTIFACT_ROOT="${SGI_PREPROD_ARTIFACT_ROOT:-artifacts/pre-prod-rebuild}"

fail() {
  printf '%s\n' "[oci-pre-prod-dividends] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-pre-prod-dividends] OK: $1"
}

is_iso_date() {
  printf '%s' "$1" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
}

[ -f docker-compose.oci.yml ] || fail "run from repository root"
command -v git >/dev/null 2>&1 || fail "git required"
command -v docker >/dev/null 2>&1 || fail "docker required"
command -v sort >/dev/null 2>&1 || fail "sort required"

printf '%s' "$COMMIT_SHA" | grep -Eq '^[0-9a-fA-F]{40}$' || fail "SGI_PREPROD_COMMIT_SHA must be a full 40-char SHA"
COMMIT_SHA="$(printf '%s' "$COMMIT_SHA" | tr 'A-F' 'a-f')"
EXPECTED_CONFIRMATION="EXECUTE-DIVIDENDS-IDEMPOTENCY:$COMMIT_SHA"
[ "$CONFIRMATION" = "$EXPECTED_CONFIRMATION" ] || fail "SGI_PREPROD_CONFIRMATION must be exactly $EXPECTED_CONFIRMATION"
is_iso_date "$START_DATE" || fail "SGI_PREPROD_START_DATE must be YYYY-MM-DD"
is_iso_date "$END_DATE" || fail "SGI_PREPROD_END_DATE must be YYYY-MM-DD"
earlier_date="$(printf '%s\n%s\n' "$START_DATE" "$END_DATE" | sort | head -n1)"
[ "$earlier_date" = "$START_DATE" ] || fail "start date must not be later than end date"

branch="$(git branch --show-current)"
[ "$branch" = "stable-15jun" ] || fail "branch must be stable-15jun, got $branch"
head="$(git rev-parse HEAD | tr 'A-F' 'a-f')"
[ "$head" = "$COMMIT_SHA" ] || fail "HEAD $head differs from requested $COMMIT_SHA"
[ -z "$(git status --porcelain)" ] || fail "working tree must be clean"

runtime_sha="$($COMPOSE exec -T backend printenv APP_COMMIT_SHA | tr -d '\r\n' | tr 'A-F' 'a-f')"
[ "$runtime_sha" = "$COMMIT_SHA" ] || fail "backend APP_COMMIT_SHA $runtime_sha differs from requested $COMMIT_SHA"

case "$ARTIFACT_ROOT" in
  artifacts|artifacts/*) ;;
  *) fail "SGI_PREPROD_ARTIFACT_ROOT must stay under repository artifacts/" ;;
esac

[ -d artifacts ] || fail "artifacts directory is missing on host"
[ -w artifacts ] || fail "artifacts directory is not writable by host operator; align ownership/permissions without chmod 777"

if [ -e "$ARTIFACT_ROOT" ]; then
  [ -d "$ARTIFACT_ROOT" ] || fail "$ARTIFACT_ROOT exists but is not a directory"
  [ -w "$ARTIFACT_ROOT" ] || fail "$ARTIFACT_ROOT is not writable by host operator"
else
  mkdir -p "$ARTIFACT_ROOT" || fail "unable to create $ARTIFACT_ROOT; align host artifacts ownership first"
fi

runtime_uid="$($COMPOSE exec -T backend id -u | tr -d '\r\n')"
runtime_artifact_uid="$($COMPOSE exec -T backend sh -c 'stat -c %u /app/artifacts 2>/dev/null || stat -f %u /app/artifacts' | tr -d '\r\n')"
[ "$runtime_artifact_uid" = "$runtime_uid" ] || fail "bind-mounted /app/artifacts owner uid=$runtime_artifact_uid differs from backend uid=$runtime_uid; align host artifacts ownership before real execution"

operation_id="$(date -u +%Y%m%d-%H%M%S)"
operation_dir="$ARTIFACT_ROOT/dividends-idempotency-$operation_id"
mkdir -p "$operation_dir"

new_run_id() {
  previous="${1:-}"
  while :; do
    candidate="$(date -u +%Y%m%d-%H%M%S)"
    [ "$candidate" != "$previous" ] && { printf '%s\n' "$candidate"; return 0; }
    sleep 1
  done
}

run_seed() {
  run_id="$1"
  evidence_host="$2"
  tmp="$evidence_host.tmp"
  [ ! -e "$evidence_host" ] || fail "evidence already exists: $evidence_host"
  [ ! -e "$tmp" ] || fail "temporary evidence already exists: $tmp"

  set +e
  $COMPOSE exec -T \
    -e PRE_PROD_BRANCH=stable-15jun \
    -e PRE_PROD_COMMIT_SHA="$COMMIT_SHA" \
    backend \
    python -m app.cli.pre_prod_dividends_seed \
      --run-id "$run_id" \
      --branch stable-15jun \
      --commit-sha "$COMMIT_SHA" \
      --start-date "$START_DATE" \
      --end-date "$END_DATE" \
      >"$tmp" 2>&1
  rc=$?
  set -e
  cat "$tmp"
  mv "$tmp" "$evidence_host"
  [ "$rc" -eq 0 ] || fail "dividends seed failed with exit code $rc; evidence preserved at $evidence_host"
}

ok "preflight passed for $COMMIT_SHA; real execution is explicitly confirmed"
first_run_id="$(new_run_id '')"
first_host="$operation_dir/first.json"
run_seed "$first_run_id" "$first_host"

second_run_id="$(new_run_id "$first_run_id")"
second_host="$operation_dir/second.json"
run_seed "$second_run_id" "$second_host"

first_container="/app/$first_host"
second_container="/app/$second_host"
report_host="$operation_dir/idempotency.json"
report_tmp="$report_host.tmp"

set +e
$COMPOSE exec -T backend \
  python -m app.cli.pre_prod_dividends_seed_idempotency \
    --first "$first_container" \
    --second "$second_container" \
    >"$report_tmp" 2>&1
compare_rc=$?
set -e
cat "$report_tmp"
mv "$report_tmp" "$report_host"

printf '%s\n' "operation_id=$operation_id"
printf '%s\n' "branch=stable-15jun"
printf '%s\n' "commit_sha=$COMMIT_SHA"
printf '%s\n' "start_date=$START_DATE"
printf '%s\n' "end_date=$END_DATE"
printf '%s\n' "first_run_id=$first_run_id"
printf '%s\n' "second_run_id=$second_run_id"
printf '%s\n' "first_evidence=$first_host"
printf '%s\n' "second_evidence=$second_host"
printf '%s\n' "idempotency_report=$report_host"
printf '%s\n' "exit_code=$compare_rc"

[ "$compare_rc" -eq 0 ] || fail "idempotency comparison failed; evidence preserved under $operation_dir"
[ -z "$(git status --porcelain)" ] || fail "execution dirtied working tree outside expected artifacts handling"
ok "two real dividends seed runs completed and idempotency comparison passed"
