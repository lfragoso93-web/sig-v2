"""Política executável para tratar deriva entre Alembic e MetaData com segurança."""

from __future__ import annotations

HIGH_RISK_SCHEMA_OBJECTS = (
    "app_config",
    "irpf_reports",
    "fx_rates",
    "irpf_records",
    "irpf_losses",
    "goal_allocations",
    "assets",
    "asset_dividends",
    "corporate_events",
    "transactions",
)

LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION = (
    "fx_rates",
    "irpf_records",
    "irpf_losses",
    "goal_allocations",
)

DRIFT_POLICY_RULES = (
    "do_not_generate_monolithic_autogenerate",
    "do_not_remove_tables_only_because_absent_from_metadata",
    "one_domain_or_contract_per_commit",
    "destructive_changes_require_synthetic_fixture",
    "keep_issue_129_separate_from_issue_241",
)

LOCAL_TEST_DB_RESET_RULES = (
    "explicit_authorization_required",
    "local_test_database_only",
    "docker_compose_down_v_allowed_only_for_disposable_local_db",
    "use_alembic_console_command",
    "block_seed_rebuild_real_import_and_production",
)
