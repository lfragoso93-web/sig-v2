"""Gates para consumidores de câmbio e metas na deriva Alembic/ORM."""

from __future__ import annotations

from pathlib import Path

from app.governance.alembic_metadata_drift_policy import (
    FX_CONSUMER_RULES,
    GOAL_CONSUMER_RULES,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_FX_ROUTER = _BACKEND_ROOT / "app" / "routers" / "fx.py"
_FX_INTEGRATION = _BACKEND_ROOT / "app" / "integrations" / "fx_rate.py"
_GOALS_ROUTER = _BACKEND_ROOT / "app" / "routers" / "goals.py"
_GOALS_SERVICE = _BACKEND_ROOT / "app" / "services" / "goals_service.py"


def test_fx_policy_requires_db_first_and_forbids_fixed_fallback() -> None:
    assert "fx_rates_is_persisted_contract_not_disposable_orphan" in FX_CONSUMER_RULES
    assert "usd_brl_reads_must_be_db_first" in FX_CONSUMER_RULES
    assert "routers_must_not_call_fx_provider_directly" in FX_CONSUMER_RULES
    assert "missing_persisted_fx_rate_must_be_explicit" in FX_CONSUMER_RULES
    assert "fixed_financial_fallback_rates_are_forbidden" in FX_CONSUMER_RULES


def test_current_fx_deviation_remains_visible_until_migrated() -> None:
    router_source = _FX_ROUTER.read_text(encoding="utf-8")
    integration_source = _FX_INTEGRATION.read_text(encoding="utf-8")

    assert "get_usd_brl" in router_source
    assert "FALLBACK_RATE" in integration_source
    assert "BRAPI" in integration_source


def test_goal_policy_keeps_goals_canonical_and_goal_allocations_protected() -> None:
    assert "goals_is_current_portfolio_scoped_contract" in GOAL_CONSUMER_RULES
    assert "goal_allocations_has_no_runtime_consumer_evidence" in GOAL_CONSUMER_RULES
    assert "goal_allocations_requires_data_fixture_before_removal" in GOAL_CONSUMER_RULES
    assert "do_not_reintroduce_goal_allocations_orm_only_for_alembic_check" in (
        GOAL_CONSUMER_RULES
    )


def test_runtime_goal_flow_uses_goals_contract_only() -> None:
    router_source = _GOALS_ROUTER.read_text(encoding="utf-8")
    service_source = _GOALS_SERVICE.read_text(encoding="utf-8")

    assert "app.services.goals_service" in router_source
    assert "from app.models.goal import Goal" in service_source
    assert "goal_allocations" not in router_source.lower()
    assert "goal_allocations" not in service_source.lower()
