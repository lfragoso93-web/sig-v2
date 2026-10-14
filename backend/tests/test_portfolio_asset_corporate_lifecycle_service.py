from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.clock import FrozenClock
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.portfolio_asset_corporate_lifecycle_service import (
    load_portfolio_asset_corporate_lifecycle,
)
from app.services.position_timeline_projection import (
    CanonicalCorporateActionCashFlow,
)


@pytest.mark.asyncio
async def test_lifecycle_reports_fraction_sale_without_creating_transaction():
    transaction = SimpleNamespace(ticker="NIKE34")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [transaction]
    db = AsyncMock()
    db.execute.return_value = result
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
            portfolio_id=15,
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
    db.execute.return_value = result
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
            portfolio_id=15,
            ticker="NIKE34",
        )

    assert lifecycle == []
