"""Gates para decisões de consolidação de configuração e IRPF."""

from __future__ import annotations

from pathlib import Path

from app.governance.alembic_metadata_drift_policy import (
    CONFIG_CONSOLIDATION_RULES,
    IRPF_CONSOLIDATION_RULES,
)

_MODELS = Path(__file__).resolve().parents[1] / "app" / "models"


def test_config_duplicate_requires_consumer_evidence_before_migration() -> None:
    assert "system_configs_is_current_migrated_contract" in CONFIG_CONSOLIDATION_RULES
    assert (
        "app_config_requires_exclusive_consumer_evidence_before_migration"
        in CONFIG_CONSOLIDATION_RULES
    )
    assert "prefer_consumer_migration_over_duplicate_table_creation" in (
        CONFIG_CONSOLIDATION_RULES
    )


def test_irpf_annual_report_cannot_replace_monthly_contracts_implicitly() -> None:
    assert (
        "irpf_reports_is_not_an_automatic_replacement_for_monthly_tables"
        in IRPF_CONSOLIDATION_RULES
    )
    assert "coordinate_irpf_schema_decisions_with_issue_56" in IRPF_CONSOLIDATION_RULES
    assert "preserve_monthly_loss_and_market_granularity_until_migrated" in (
        IRPF_CONSOLIDATION_RULES
    )


def test_portfolio_type_checking_uses_the_real_goal_module() -> None:
    source = (_MODELS / "portfolio.py").read_text(encoding="utf-8")

    assert "from app.models.goal import Goal" in source
    assert "from app.models.goals import Goal" not in source
