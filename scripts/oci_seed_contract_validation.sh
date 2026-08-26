#!/usr/bin/env sh
set -eu

IMAGE="${SGI_BACKEND_TEST_IMAGE:-sgi-v2-backend}"
ENV_FILE="${SGI_ENV_FILE:-.env}"

fail() {
  printf '%s\n' "[oci-seed-contract-validation] ERROR: $1" >&2
  exit 1
}

ok() {
  printf '%s\n' "[oci-seed-contract-validation] OK: $1"
}

run_pytest() {
  label="$1"
  shift
  printf '%s\n' "[oci-seed-contract-validation] Running $label"
  docker run --rm \
    --env-file "$ENV_FILE" \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$(pwd)/backend:/app:ro" \
    -w /app \
    "$IMAGE" \
    pytest -q -p no:cacheprovider "$@"
  ok "$label passed"
}

[ -f docker-compose.yml ] || fail "run from repository root"
[ -d backend/tests ] || fail "backend tests directory missing"
[ -f "$ENV_FILE" ] || fail "$ENV_FILE missing"
command -v docker >/dev/null 2>&1 || fail "docker is required"

run_pytest "FX, macro and Treasury seed contracts" \
  tests/unit/test_pre_prod_fx_seed_contract.py \
  tests/unit/test_pre_prod_fx_seed_cli.py \
  tests/unit/test_pre_prod_fx_seed_service.py \
  tests/unit/test_pre_prod_fx_seed_inspection.py \
  tests/unit/test_pre_prod_fx_seed_preparation.py \
  tests/unit/test_pre_prod_macro_seed_contract.py \
  tests/unit/test_pre_prod_macro_seed_cli.py \
  tests/unit/test_pre_prod_macro_seed_service.py \
  tests/unit/test_pre_prod_macro_seed_inspection.py \
  tests/unit/test_pre_prod_macro_seed_compare.py \
  tests/unit/test_compare_pre_prod_macro_seed_wrapper.py \
  tests/unit/test_pre_prod_treasury_seed_contract.py \
  tests/unit/test_pre_prod_treasury_seed_cli.py \
  tests/unit/test_pre_prod_treasury_seed_service.py \
  tests/unit/test_pre_prod_treasury_seed_inspection.py \
  tests/unit/test_pre_prod_treasury_seed_idempotency_cli.py

run_pytest "B3, asset bootstrap and system bootstrap contracts" \
  tests/test_pre_prod_b3_seed.py \
  tests/test_asset_bootstrap_plan_cli.py \
  tests/test_asset_bootstrap_planner.py \
  tests/test_asset_bootstrap_coordinator.py \
  tests/test_asset_bootstrap_stage_states.py \
  tests/test_asset_bootstrap_plan_envelope.py \
  tests/test_asset_bootstrap_configuration_validator.py \
  tests/test_asset_bootstrap_dependency_policy.py \
  tests/test_asset_bootstrap_execution_identity.py \
  tests/test_asset_bootstrap_full_fixture_pipeline.py \
  tests/test_asset_bootstrap_fixture_catalog.py \
  tests/test_asset_bootstrap_focused_runner.py \
  tests/test_asset_bootstrap_report_diff_cli.py \
  tests/test_asset_bootstrap_report_diff_service.py \
  tests/test_asset_bootstrap_synthetic_idempotency.py \
  tests/test_asset_seed_crypto_adapter_boundary.py \
  tests/test_asset_seed_proventos_classes.py \
  tests/test_system_bootstrap_contract.py \
  tests/test_system_bootstrap_execution_context.py \
  tests/test_system_bootstrap_fx_stage.py \
  tests/test_system_bootstrap_dividends_stage.py \
  tests/test_system_bootstrap_corporate_events_stage.py \
  tests/test_system_bootstrap_trigger_service.py \
  tests/test_admin_system_bootstrap_surface.py \
  tests/test_admin_bootstrap_single_surface.py \
  tests/test_main_uses_system_bootstrap.py

run_pytest "Dividends seed contracts" \
  tests/unit/test_pre_prod_dividends_seed_contract.py \
  tests/unit/test_pre_prod_dividends_seed_cli.py \
  tests/unit/test_pre_prod_dividends_seed_idempotency.py \
  tests/unit/test_pre_prod_dividends_seed_idempotency_cli.py \
  tests/unit/test_pre_prod_dividends_seed_service.py \
  tests/unit/test_pre_prod_dividends_seed_persistence.py \
  tests/unit/test_pre_prod_dividends_seed_inspection.py \
  tests/unit/test_pre_prod_dividends_seed_collector.py \
  tests/unit/test_pre_prod_dividends_seed_providers.py \
  tests/unit/test_pre_prod_dividends_seed_source_semantics.py \
  tests/unit/test_pre_prod_dividends_seed_no_materialization.py \
  tests/unit/test_pre_prod_dividends_idempotency_wrapper.py

ok "all seed/bootstrap contract suites passed without real seed execution"
