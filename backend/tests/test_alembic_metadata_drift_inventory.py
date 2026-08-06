"""Gates de governança para a deriva global entre Alembic e MetaData."""

from __future__ import annotations

from app.governance.alembic_metadata_drift_policy import (
    DRIFT_POLICY_RULES,
    HIGH_RISK_SCHEMA_OBJECTS,
)


def test_policy_blocks_monolithic_autogenerate() -> None:
    assert "do_not_generate_monolithic_autogenerate" in DRIFT_POLICY_RULES
    assert "do_not_remove_tables_only_because_absent_from_metadata" in DRIFT_POLICY_RULES
    assert "one_domain_or_contract_per_commit" in DRIFT_POLICY_RULES
    assert "destructive_changes_require_synthetic_fixture" in DRIFT_POLICY_RULES


def test_policy_tracks_high_risk_schema_objects() -> None:
    assert HIGH_RISK_SCHEMA_OBJECTS == (
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


def test_policy_keeps_global_drift_separate_from_corporate_bootstrap() -> None:
    assert "keep_issue_129_separate_from_issue_241" in DRIFT_POLICY_RULES
