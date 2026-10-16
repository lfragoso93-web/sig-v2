from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.core.clock import FrozenClock
from app.routers import transactions as transactions_router
from app.schemas.transaction import CorporateLifecycleEventOut
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.portfolio_asset_corporate_lifecycle_service import (
    READ_PORTFOLIO_CORPORATE_LIFECYCLE,
    load_portfolio_asset_corporate_lifecycle,
    load_portfolio_pending_corporate_fractions,
)
from app.services.position_timeline_projection import (
    CanonicalCorporateActionCashFlow,
)


def _access(
    *,
    user_id: int = 3,
    portfolio_id: int = 15,
) -> PortfolioAccessContext:
    return PortfolioAccessContext.for_user(
        user_id=user_id,
        portfolio_id=portfolio_id,
        permissions=frozenset({READ_PORTFOLIO_CORPORATE_LIFECYCLE}),
    )


@pytest.mark.asyncio
async def test_lifecycle_reports_fraction_sale_without_creating_transaction():
    transaction = SimpleNamespace(ticker="NIKE34")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [transaction]
    db = AsyncMock()
    ownership = MagicMock()
    ownership.scalar_one_or_none.return_value = SimpleNamespace(id=15, user_id=3)
    db.execute.side_effect = [ownership, result]
    action = NormalizedCorporateAction(
        source="official",
        source_event_id="nike34-grouping",
        ticker="NIKE34",
        event_date=datetime(2026, 10, 13, tzinfo=timezone.utc).date(),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
    )
    cash_flow = CanonicalCorporateActionCashFlow(
        source_event_id=action.source_event_id,
        event_date=action.event_date,
        fractional_quantity=Decimal("0.2"),
        unit_settlement_price_brl=Decimal("80"),
        gross_amount_brl=Decimal("16"),
        cash_treatment="AUCTION_SETTLEMENT",
        cost_basis_brl=Decimal("29.40833333333333333333333333"),
        realized_pnl_brl=Decimal("-13.40833333333333333333333333"),
    )
    projection = SimpleNamespace(
        applied_event_ids=(action.source_event_id,),
        corporate_action_cash_flows=(cash_flow,),
        pending_corporate_action_fractions=(),
    )

    with (
        patch(
            "app.services.portfolio_asset_corporate_lifecycle_service."
            "load_global_corporate_actions_by_ticker",
            new=AsyncMock(return_value={"NIKE34": (action,)}),
        ),
        patch(
            "app.services.portfolio_asset_corporate_lifecycle_service."
            "project_transaction_timelines",
            return_value={"NIKE34": (projection, "BDR", False)},
        ) as projector,
    ):
        lifecycle = await load_portfolio_asset_corporate_lifecycle(
            db,
            access=_access(),
            ticker=" nike34 ",
            clock=FrozenClock(datetime(2026, 10, 14, tzinfo=timezone.utc)),
        )

    assert lifecycle == [
        {
            "source_event_id": "nike34-grouping",
            "ticker": "NIKE34",
            "event_date": action.event_date,
            "event_type": "GRUPAMENTO",
            "quantity_factor": Decimal("0.2"),
            "fractional_quantity": Decimal("0.2"),
            "settlement_status": "SETTLED",
            "unit_settlement_price_brl": Decimal("80"),
            "gross_amount_brl": Decimal("16"),
            "cost_basis_brl": Decimal("29.40833333333333333333333333"),
            "realized_pnl_brl": Decimal("-13.40833333333333333333333333"),
            "cash_treatment": "AUCTION_SETTLEMENT",
            "message": "Fração vendida e valor creditado ao usuário.",
        }
    ]
    projector.assert_called_once()
    assert projector.call_args.kwargs["transactions"] == [transaction]


@pytest.mark.asyncio
async def test_lifecycle_omits_events_that_did_not_affect_position():
    transaction = SimpleNamespace(ticker="NIKE34")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [transaction]
    db = AsyncMock()
    ownership = MagicMock()
    ownership.scalar_one_or_none.return_value = SimpleNamespace(id=15, user_id=3)
    db.execute.side_effect = [ownership, result]
    action = NormalizedCorporateAction(
        source="yahoo",
        source_event_id="historical-before-position",
        ticker="NIKE34",
        event_date=datetime(2021, 2, 9, tzinfo=timezone.utc).date(),
        kind=CorporateActionKind.SPLIT,
        quantity_factor=Decimal("10"),
        raw_payload={},
    )
    projection = SimpleNamespace(
        applied_event_ids=(),
        corporate_action_cash_flows=(),
        pending_corporate_action_fractions=(),
    )

    with (
        patch(
            "app.services.portfolio_asset_corporate_lifecycle_service."
            "load_global_corporate_actions_by_ticker",
            new=AsyncMock(return_value={"NIKE34": (action,)}),
        ),
        patch(
            "app.services.portfolio_asset_corporate_lifecycle_service."
            "project_transaction_timelines",
            return_value={"NIKE34": (projection, "BDR", False)},
        ),
    ):
        lifecycle = await load_portfolio_asset_corporate_lifecycle(
            db,
            access=_access(),
            ticker="NIKE34",
        )

    assert lifecycle == []


@pytest.mark.asyncio
async def test_lifecycle_reports_pending_fraction_without_cash_amount():
    transaction = SimpleNamespace(ticker="TEST3")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [transaction]
    db = AsyncMock()
    ownership = MagicMock()
    ownership.scalar_one_or_none.return_value = SimpleNamespace(id=15, user_id=3)
    db.execute.side_effect = [ownership, result]
    action = NormalizedCorporateAction(
        source="b3",
        source_event_id="b3:test3-grouping",
        ticker="TEST3",
        event_date=datetime(2026, 10, 13, tzinfo=timezone.utc).date(),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
    )
    pending = SimpleNamespace(
        source_event_id=action.source_event_id,
        fractional_quantity=Decimal("0.2"),
    )
    projection = SimpleNamespace(
        applied_event_ids=(action.source_event_id,),
        corporate_action_cash_flows=(),
        pending_corporate_action_fractions=(pending,),
    )

    with (
        patch(
            "app.services.portfolio_asset_corporate_lifecycle_service."
            "load_global_corporate_actions_by_ticker",
            new=AsyncMock(return_value={"TEST3": (action,)}),
        ),
        patch(
            "app.services.portfolio_asset_corporate_lifecycle_service."
            "project_transaction_timelines",
            return_value={"TEST3": (projection, "ACAO", False)},
        ),
    ):
        lifecycle = await load_portfolio_asset_corporate_lifecycle(
            db,
            access=_access(),
            ticker="TEST3",
        )

    assert len(lifecycle) == 1
    assert lifecycle[0]["fractional_quantity"] == Decimal("0.2")
    assert lifecycle[0]["settlement_status"] == "PENDING_VALUE"
    assert lifecycle[0]["unit_settlement_price_brl"] is None
    assert lifecycle[0]["gross_amount_brl"] is None
    assert lifecycle[0]["realized_pnl_brl"] is None
    assert "valor ainda não confirmado" in lifecycle[0]["message"]


@pytest.mark.asyncio
async def test_portfolio_pending_fraction_list_is_scoped_and_has_no_value():
    transaction = SimpleNamespace(ticker="TEST3")
    transactions_result = MagicMock()
    transactions_result.scalars.return_value.all.return_value = [transaction]
    db = AsyncMock()
    ownership = MagicMock()
    ownership.scalar_one_or_none.return_value = SimpleNamespace(id=15, user_id=3)
    db.execute.side_effect = [ownership, transactions_result]
    action = NormalizedCorporateAction(
        source="b3",
        source_event_id="b3:test3-grouping",
        ticker="TEST3",
        event_date=datetime(2026, 10, 13, tzinfo=timezone.utc).date(),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
    )
    pending = SimpleNamespace(
        source_event_id=action.source_event_id,
        fractional_quantity=Decimal("0.2"),
    )
    projection = SimpleNamespace(
        applied_event_ids=(action.source_event_id,),
        corporate_action_cash_flows=(),
        pending_corporate_action_fractions=(pending,),
    )

    with (
        patch(
            "app.services.portfolio_asset_corporate_lifecycle_service."
            "load_global_corporate_actions_by_ticker",
            new=AsyncMock(return_value={"TEST3": (action,)}),
        ),
        patch(
            "app.services.portfolio_asset_corporate_lifecycle_service."
            "project_transaction_timelines",
            return_value={"TEST3": (projection, "BDR", False)},
        ) as projector,
    ):
        fractions = await load_portfolio_pending_corporate_fractions(
            db,
            access=_access(),
            clock=FrozenClock(datetime(2026, 10, 14, tzinfo=timezone.utc)),
        )

    assert len(fractions) == 1
    assert fractions[0]["ticker"] == "TEST3"
    assert fractions[0]["fractional_quantity"] == Decimal("0.2")
    assert fractions[0]["settlement_status"] == "PENDING_VALUE"
    assert fractions[0]["gross_amount_brl"] is None
    assert fractions[0]["realized_pnl_brl"] is None
    projector.assert_called_once_with(
        transactions=[transaction],
        actions_by_ticker={"TEST3": (action,)},
        target_date=date(2026, 10, 14),
    )


@pytest.mark.asyncio
async def test_lifecycle_denies_cross_user_before_reading_sensitive_data():
    db = AsyncMock()
    ownership = MagicMock()
    ownership.scalar_one_or_none.return_value = None
    db.execute.return_value = ownership

    with pytest.raises(
        PortfolioAccessDenied,
        match="Carteira nao encontrada ou sem permissao",
    ):
        await load_portfolio_asset_corporate_lifecycle(
            db,
            access=_access(user_id=9),
            ticker="NIKE34",
        )

    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_lifecycle_requires_explicit_permission_before_database_access():
    db = AsyncMock()
    access = PortfolioAccessContext.for_user(
        user_id=3,
        portfolio_id=15,
        permissions=frozenset({"portfolio:transactions:read"}),
    )

    with pytest.raises(PortfolioAccessDenied):
        await load_portfolio_asset_corporate_lifecycle(
            db,
            access=access,
            ticker="NIKE34",
        )

    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_lifecycle_controller_builds_scoped_user_context(monkeypatch):
    captured: list[PortfolioAccessContext] = []

    async def _load(_db, *, access, ticker):
        captured.append(access)
        assert ticker == "NIKE34"
        return []

    monkeypatch.setattr(
        transactions_router,
        "load_portfolio_asset_corporate_lifecycle",
        _load,
    )

    result = await transactions_router.list_asset_corporate_lifecycle(
        portfolio_id=15,
        ticker="NIKE34",
        db=AsyncMock(),
        current_user=SimpleNamespace(id=3),
    )

    assert result == []
    assert len(captured) == 1
    assert captured[0].user_id == 3
    assert captured[0].portfolio_id == 15
    assert captured[0].permissions == frozenset(
        {READ_PORTFOLIO_CORPORATE_LIFECYCLE}
    )


@pytest.mark.asyncio
async def test_pending_fraction_controller_builds_scoped_user_context(monkeypatch):
    captured: list[PortfolioAccessContext] = []

    async def _load(_db, *, access):
        captured.append(access)
        return []

    monkeypatch.setattr(
        transactions_router,
        "load_portfolio_pending_corporate_fractions",
        _load,
    )

    result = await transactions_router.list_portfolio_pending_corporate_fractions(
        portfolio_id=15,
        db=AsyncMock(),
        current_user=SimpleNamespace(id=3),
    )

    assert result == []
    assert len(captured) == 1
    assert captured[0].user_id == 3
    assert captured[0].portfolio_id == 15
    assert captured[0].permissions == frozenset(
        {READ_PORTFOLIO_CORPORATE_LIFECYCLE}
    )


def test_lifecycle_response_schema_preserves_pending_status():
    response = CorporateLifecycleEventOut.model_validate(
        {
            "source_event_id": "pending",
            "ticker": "TEST3",
            "event_date": "2026-10-13",
            "event_type": "GRUPAMENTO",
            "quantity_factor": "0.2",
            "fractional_quantity": "0.2",
            "settlement_status": "PENDING_VALUE",
            "gross_amount_brl": None,
        }
    )

    assert response.settlement_status == "PENDING_VALUE"


@pytest.mark.asyncio
async def test_lifecycle_controller_hides_cross_portfolio_denial(monkeypatch):
    async def _deny(_db, *, access, ticker):
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")

    monkeypatch.setattr(
        transactions_router,
        "load_portfolio_asset_corporate_lifecycle",
        _deny,
    )

    with pytest.raises(HTTPException) as exc_info:
        await transactions_router.list_asset_corporate_lifecycle(
            portfolio_id=99,
            ticker="NIKE34",
            db=AsyncMock(),
            current_user=SimpleNamespace(id=3),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Carteira nao encontrada ou sem permissao"
