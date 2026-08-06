"""Gates para decisões de consolidação de configuração e IRPF."""

from __future__ import annotations

from pathlib import Path

from app.governance.alembic_metadata_drift_policy import (
    CONFIG_CONSOLIDATION_RULES,
    IRPF_CONSOLIDATION_RULES,
)

_MODELS = Path(__file__).resolve().parents[1] / "app" / "models"
_MODELS_INIT = _MODELS / "__init__.py"
_APP_CONFIG_MODEL = _MODELS / "config.py"
_SYSTEM_CONFIG_MODEL = _MODELS / "system_config.py"


def test_system_config_is_the_only_current_config_model() -> None:
    assert "system_configs_is_current_migrated_contract" in CONFIG_CONSOLIDATION_RULES
    assert "app_config_model_must_not_exist" in CONFIG_CONSOLIDATION_RULES
    assert "prefer_consumer_migration_over_duplicate_table_creation" in (
        CONFIG_CONSOLIDATION_RULES
    )

    models_source = _MODELS_INIT.read_text(encoding="utf-8")
    system_config_source = _SYSTEM_CONFIG_MODEL.read_text(encoding="utf-8")

    assert not _APP_CONFIG_MODEL.exists()
    assert "from app.models.config import AppConfig" not in models_source
    assert '"AppConfig"' not in models_source
    assert "from app.models.system_config import SystemConfig" in models_source
    assert '"SystemConfig"' in models_source
    assert '__tablename__ = "system_configs"' in system_config_source


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
