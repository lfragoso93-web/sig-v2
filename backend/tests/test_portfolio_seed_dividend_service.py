from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_seed_dividend_service import seed_synthetic_dividends
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType
from app.services.canonical_dividend_entitlement import (
    DividendEvent,
    EntitlementReason,
    PositionMovement,
    calculate_dividend_entitlement,
)


def _owned_mxrf11() -> SimpleNamespace:
    return SimpleNamespace(
        id=303,
        ticker="CERT303-MXRF11",
        asset_type="FII",
        name="SGI certification #303 synthetic asset [MXRF11]",
        provider="synthetic-certification",
        provider_symbol="MXRF11",
        provider_status="synthetic-owned",
    )


def _execute_result(*, scalar=None, scalars=None) -> MagicMock:
    result = MagicMock()
    if scalar is not None:
        result.scalar_one_or_none.return_value = scalar
    if scalars is not None:
        result.scalars.return_value.all.return_value = scalars
    return result


def _canonical_dividend() -> SimpleNamespace:
    return SimpleNamespace(
        asset_id=303,
        record_date=date(2026, 2, 5),
        ex_date=date(2026, 2, 6),
        payment_date=date(2026, 2, 14),
        dividend_type=DividendType.RENDIMENTO,
        value_per_unit=Decimal("0.10"),
        source="synthetic-certification",
        approved_on=None,
        gross_value_per_unit=None,
        factor=None,
        complete_factor=None,
        isin_code=None,
        asset_issued=None,
        related_to=None,
        remarks=None,
        raw_payload=None,
    )


@pytest.mark.asyncio
async def test_seed_creates_one_global_synthetic_dividend() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=_owned_mxrf11()),
            _execute_result(scalars=[]),
        ]
    )

    result = await seed_synthetic_dividends(db)

    assert result.created == 1
    assert result.reused == 0
    db.add.assert_called_once()
    db.commit.assert_awaited_once()

    added = db.add.call_args.args[0]
    assert isinstance(added, AssetDividend)
    assert added.asset_id == 303
    assert added.record_date == date(2026, 2, 5)
    assert added.ex_date == date(2026, 2, 6)
    assert added.payment_date == date(2026, 2, 14)
    assert added.dividend_type is DividendType.RENDIMENTO
    assert added.value_per_unit == Decimal("0.10")
    assert added.source == "synthetic-certification"


@pytest.mark.asyncio
async def test_seed_replay_reuses_exact_global_dividend() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=_owned_mxrf11()),
            _execute_result(scalars=[_canonical_dividend()]),
        ]
    )

    result = await seed_synthetic_dividends(db)

    assert result.created == 0
    assert result.reused == 1
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_fails_closed_on_existing_dividend_contamination() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    contaminated = _canonical_dividend()
    contaminated.source = "brapi"
    db.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=_owned_mxrf11()),
            _execute_result(scalars=[contaminated]),
        ]
    )

    with pytest.raises(
        SyntheticSeedContractError,
        match="synthetic dividend collision for CERT303-MXRF11",
    ):
        await seed_synthetic_dividends(db)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


def test_fixture_dividend_projects_exact_expected_entitlement() -> None:
    fixture = load_portfolio_synthetic_certification_fixture()
    raw = fixture["income_events"][0]

    entitlement = calculate_dividend_entitlement(
        DividendEvent(
            event_id=303,
            record_date=date.fromisoformat(raw["record_date"]),
            ex_date=date.fromisoformat(raw["ex_date"]),
            payment_date=date.fromisoformat(raw["payment_date"]),
            event_type=raw["dividend_type"],
            value_per_unit=Decimal(raw["value_per_unit"]),
            currency="BRL",
        ),
        [
            PositionMovement(
                transaction_date=date(2026, 1, 5),
                operation="buy",
                quantity=Decimal("200"),
            )
        ],
    )

    assert entitlement.reason is EntitlementReason.ELIGIBLE
    assert entitlement.entitlement_date == date(2026, 2, 5)
    assert entitlement.eligible_quantity == Decimal(raw["quantity"])
    assert entitlement.gross_amount == Decimal(raw["gross_amount"])
    assert entitlement.net_amount == Decimal("20.00")
