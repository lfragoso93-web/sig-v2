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
    "irpf_records",
    "irpf_losses",
    "goal_allocations",
)

CURRENT_PERSISTED_SCHEMA_OBJECTS = (
    "fx_rates",
)

DRIFT_POLICY_RULES = (
    "do_not_generate_monolithic_autogenerate",
    "do_not_remove_tables_only_because_absent_from_metadata",
    "one_domain_or_contract_per_commit",
    "destructive_changes_require_synthetic_fixture",
    "keep_issue_129_separate_from_issue_241",
)

CONFIG_CONSOLIDATION_RULES = (
    "system_configs_is_current_migrated_contract",
    "app_config_requires_exclusive_consumer_evidence_before_migration",
    "prefer_consumer_migration_over_duplicate_table_creation",
)

IRPF_CONSOLIDATION_RULES = (
    "irpf_reports_is_not_an_automatic_replacement_for_monthly_tables",
    "coordinate_irpf_schema_decisions_with_issue_56",
    "preserve_monthly_loss_and_market_granularity_until_migrated",
)

LEGACY_CONTRACT_DECISION_RULES = (
    "fx_rates_is_current_persisted_contract",
    "goal_allocations_preserved_until_goal_consumers_are_inventory_complete",
    "do_not_reintroduce_orm_models_only_to_silence_alembic_check",
    "do_not_drop_legacy_tables_without_domain_decision_and_synthetic_fixture",
)

FX_CONSUMER_RULES = (
    "fx_rates_is_persisted_contract_not_disposable_orphan",
    "usd_brl_reads_must_be_db_first",
    "routers_must_not_call_fx_provider_directly",
    "missing_persisted_fx_rate_must_be_explicit",
    "fixed_financial_fallback_rates_are_forbidden",
)

GOAL_CONSUMER_RULES = (
    "goals_is_current_portfolio_scoped_contract",
    "goal_allocations_has_no_runtime_consumer_evidence",
    "goal_allocations_requires_data_fixture_before_removal",
    "do_not_reintroduce_goal_allocations_orm_only_for_alembic_check",
)

LOCAL_TEST_DB_RESET_RULES = (
    "explicit_authorization_required",
    "local_test_database_only",
    "docker_compose_down_v_allowed_only_for_disposable_local_db",
    "use_alembic_console_command",
    "block_seed_rebuild_real_import_and_production",
)
