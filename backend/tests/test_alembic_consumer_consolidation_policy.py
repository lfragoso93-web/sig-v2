"""Gates para decisões de consolidação de configuração e IRPF."""

from __future__ import annotations

from pathlib import Path

from app.governance.alembic_metadata_drift_policy import (
    CONFIG_CONSOLIDATION_RULES,
    IRPF_CONSOLIDATION_RULES,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MODELS = _BACKEND_ROOT / "app" / "models"
_MODELS_INIT = _MODELS / "__init__.py"
_APP_CONFIG_MODEL = _MODELS / "config.py"
_SYSTEM_CONFIG_MODEL = _MODELS / "system_config.py"
_CONFIG_SERVICE = _BACKEND_ROOT / "app" / "services" / "config_service.py"
_IRPF_REPORT_MODEL = _MODELS / "irpf.py"
_PORTFOLIO_MODEL = _MODELS / "portfolio.py"
_IRPF_ROUTER = _BACKEND_ROOT / "app" / "routers" / "irpf.py"


def test_system_config_is_the_only_current_config_model() -> None:
    assert "system_configs_is_current_migrated_contract" in CONFIG_CONSOLIDATION_RULES
    assert "app_config_model_must_not_exist" in CONFIG_CONSOLIDATION_RULES
    assert "prefer_consumer_migration_over_duplicate_table_creation" in (
        CONFIG_CONSOLIDATION_RULES
    )

    models_source = _MODELS_INIT.read_text(encoding="utf-8")
    system_config_source = _SYSTEM_CONFIG_MODEL.read_text(encoding="utf-8")
    service_source = _CONFIG_SERVICE.read_text(encoding="utf-8")

    assert not _APP_CONFIG_MODEL.exists()
    assert "from app.models.config import AppConfig" not in models_source
    assert '"AppConfig"' not in models_source
    assert "from app.models.system_config import SystemConfig" in models_source
    assert '"SystemConfig"' in models_source
    assert '__tablename__ = "system_configs"' in system_config_source
    assert "from app.models.system_config import SystemConfig" in service_source
    assert "app.models.config" not in service_source
    assert "AppConfig" not in service_source


def test_irpf_report_model_is_removed_without_dropping_monthly_contracts() -> None:
    assert "irpf_reports_model_must_not_exist" in IRPF_CONSOLIDATION_RULES
    assert "irpf_reports_table_must_not_be_created" in IRPF_CONSOLIDATION_RULES
    assert "coordinate_irpf_schema_decisions_with_issue_56" in IRPF_CONSOLIDATION_RULES
    assert "preserve_monthly_loss_and_market_granularity_until_migrated" in (
        IRPF_CONSOLIDATION_RULES
    )

    models_source = _MODELS_INIT.read_text(encoding="utf-8")
    portfolio_source = _PORTFOLIO_MODEL.read_text(encoding="utf-8")
    router_source = _IRPF_ROUTER.read_text(encoding="utf-8")

    assert not _IRPF_REPORT_MODEL.exists()
    assert "from app.models.irpf import IRPFReport" not in models_source
    assert '"IRPFReport"' not in models_source
    assert "IRPFReport" not in portfolio_source
    assert "irpf_reports" not in portfolio_source
    assert "app.models.irpf" not in router_source
    assert "from app.models.irpf import IRPFReport" not in router_source
    assert "select(IRPFReport)" not in router_source
    assert "IRPFReportOut" in router_source
    assert "generate_irpf_report" in router_source
    assert "nao existe cache persistido" in router_source


def test_portfolio_type_checking_uses_the_real_goal_module() -> None:
    source = _PORTFOLIO_MODEL.read_text(encoding="utf-8")

    assert "from app.models.goal import Goal" in source
    assert "from app.models.goals import Goal" not in source
