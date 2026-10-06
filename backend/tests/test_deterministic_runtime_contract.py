"""Behavioral contracts for Clock, startup config and query diagnostics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.clock import FrozenClock
from app.core.config import Settings
from app.models.dividend_enums import DividendStatus
from app.services.canonical_dividend_entitlement import (
    DividendEntitlement,
    DividendEvent,
    EntitlementReason,
)
from app.services.canonical_dividend_entitlement_reader import (
    PortfolioDividendEntitlement,
)
from app.services.proventos_service import list_items
from tests.query_budget import QueryBudgetExceeded, assert_max_queries

ROOT = Path(__file__).resolve().parents[2]
FROZEN_NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


def _production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "ENVIRONMENT": "production",
        "APP_BRANCH": "stable-15jun",
        "APP_COMMIT_SHA": "a" * 40,
        "REAL_DATASET_REFERENCE": "pre-prod-backup.v3:sha256:" + "b" * 64,
        "SECRET_KEY": "s" * 32,
        "SUPERADMIN_PASSWORD": "Strong@1234",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_frozen_clock_requires_timezone_and_never_reads_machine_clock() -> None:
    clock = FrozenClock(FROZEN_NOW)

    assert clock.now() == FROZEN_NOW
    assert clock.today().isoformat() == "2026-10-06"
    with pytest.raises(ValueError, match="timezone-aware"):
        FrozenClock(datetime(2026, 10, 6, 12))


@pytest.mark.asyncio
async def test_proventos_status_is_deterministic_across_payment_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment_date = FROZEN_NOW.date()
    item = PortfolioDividendEntitlement(
        ticker="ABCD3",
        asset_type="ACAO",
        event=DividendEvent(
            event_id=1,
            record_date=payment_date - timedelta(days=2),
            ex_date=payment_date - timedelta(days=1),
            payment_date=payment_date,
            event_type="DIVIDENDO",
            value_per_unit=Decimal("1"),
            currency="BRL",
        ),
        entitlement=DividendEntitlement(
            event_id=1,
            reason=EntitlementReason.ELIGIBLE,
            entitlement_date=payment_date - timedelta(days=2),
            eligible_quantity=Decimal("1"),
            gross_amount=Decimal("1"),
            withholding_tax=Decimal("0"),
            net_amount=Decimal("1"),
            currency="BRL",
        ),
        approved_on=None,
        gross_value_per_unit=None,
        factor=None,
        complete_factor=None,
        isin_code=None,
        asset_issued=None,
        related_to=None,
        remarks=None,
    )

    async def load(*_args, **_kwargs):
        return [item]

    monkeypatch.setattr(
        "app.services.proventos_service.load_portfolio_dividend_entitlements",
        load,
    )
    before = FrozenClock(FROZEN_NOW - timedelta(days=1))
    on_payment_date = FrozenClock(FROZEN_NOW)

    pending = await list_items(object(), 1, clock=before)
    received = await list_items(object(), 1, clock=on_payment_date)

    assert pending["items"][0]["status"] is DividendStatus.A_RECEBER
    assert received["items"][0]["status"] is DividendStatus.RECEBIDO


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"APP_BRANCH": "main"}, "APP_BRANCH"),
        ({"APP_COMMIT_SHA": "short"}, "APP_COMMIT_SHA"),
        ({"REAL_DATASET_REFERENCE": "free-form"}, "REAL_DATASET_REFERENCE"),
        ({"REDIS_PORT": 0}, "REDIS_PORT"),
        ({"ASYNC_DATABASE_URL": "sqlite:///tmp.db"}, "ASYNC_DATABASE_URL"),
    ],
)
def test_critical_startup_configuration_fails_early_without_values(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError) as raised:
        _production_settings(**overrides)

    assert message in str(raised.value)
    assert all(str(value) not in str(raised.value) for value in overrides.values())


def test_oci_and_local_examples_declare_runtime_identity_contract() -> None:
    for relative_path in (".env.example", ".env.oci.example"):
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "APP_BRANCH=" in content
        assert "REAL_DATASET_REFERENCE=" in content
    production_compose = (ROOT / "docker-compose.prod.yml").read_text(
        encoding="utf-8"
    )
    assert "ENVIRONMENT: production" in production_compose
    assert "APP_ENV" not in production_compose


@pytest.mark.asyncio
async def test_query_budget_detects_regression() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        with pytest.raises(QueryBudgetExceeded, match="actual=2, maximum=1"):
            with assert_max_queries(engine, 1):
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
                    await connection.execute(text("SELECT 2"))
    finally:
        await engine.dispose()


def test_canonical_proventos_reader_has_fixed_two_query_plan() -> None:
    source = (
        ROOT
        / "backend"
        / "app"
        / "services"
        / "canonical_dividend_entitlement_reader.py"
    ).read_text(encoding="utf-8")

    assert source.count("await db.execute(") == 2
    assert "for asset_dividend, asset in event_rows:" in source
