from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.access_context import PortfolioAccessContext
from app.core.clock import FrozenClock
from app.services.portfolio_corporate_rights_service import (
    load_portfolio_corporate_rights,
)

_READ_PERMISSION = "portfolio:corporate-lifecycle:read"


@pytest.mark.asyncio
async def test_rights_report_issuer_cost_and_component_result_without_confirming_cash():
    access = PortfolioAccessContext.for_user(
        user_id=5,
        portfolio_id=17,
        permissions=frozenset({_READ_PERMISSION}),
    )
    transaction = SimpleNamespace(ticker="KLBN11", date=date(2025, 12, 1))
    event = SimpleNamespace(
        id=81,
        ticker="KLBN11",
        event_type="BONIFICACAO",
        record_date=date(2025, 12, 17),
        payment_date=date(2026, 2, 24),
        effective_date=date(2025, 12, 18),
        source_provider="b3",
        source_event_id="klbn-bonus-2025",
        brapi_event_id=None,
        raw_data=None,
        raw_metadata={
            "fractional_component_settlement": {
                "model": "COMPONENT_BONUS_FRACTIONS_V1",
                "evidence_reference": "issuer:klbn:bonus-and-auction:2025",
                "bonus_factor": "0.01",
                "bonus_cost_per_share_brl": "12.94564988922",
                "cash_treatment": "PRO_RATA_AUCTION_RIGHT",
                "requires_unit_grouping": True,
                "unit_composition": {"ON": "1", "PN": "4"},
                "components": [
                    {
                        "component": "ON",
                        "ticker": "KLBN3",
                        "asset_type": "ACAO",
                        "isin_code": "US0378331005",
                        "units_per_position": "1",
                        "settlement_price_brl": "3.942352337",
                    },
                    {
                        "component": "PN",
                        "ticker": "KLBN4",
                        "asset_type": "ACAO",
                        "isin_code": "US5949181045",
                        "units_per_position": "4",
                        "settlement_price_brl": "3.942611212",
                    },
                ],
            }
        },
    )
    evidence = SimpleNamespace(
        decision="MATCHED",
        evidence_type="OFFICIAL_ISSUER_DOCUMENT",
        evidence_reference="issuer:klbn:bonus-and-auction:2025",
    )
    ownership = MagicMock()
    ownership.scalar_one_or_none.return_value = SimpleNamespace(id=17, user_id=5)
    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [transaction]
    event_result = MagicMock()
    event_result.all.return_value = [(event, evidence)]
    db = AsyncMock()
    db.execute.side_effect = [ownership, tx_result, event_result]
    projected_position = SimpleNamespace(quantity=Decimal("10"))

    with (
        patch(
            "app.services.portfolio_corporate_rights_service."
            "load_global_corporate_actions_by_ticker",
            new=AsyncMock(return_value={"KLBN11": ()}),
        ),
        patch(
            "app.services.portfolio_corporate_rights_service."
            "project_transaction_timelines",
            return_value={"KLBN11": (projected_position, "ACAO", False)},
        ),
    ):
        rights = await load_portfolio_corporate_rights(
            db,
            access=access,
            clock=FrozenClock(datetime(2026, 3, 1, tzinfo=timezone.utc)),
        )

    assert len(rights) == 1
    right = rights[0]
    assert right["base_position"] == Decimal("10")
    assert right["gross_amount_brl"] == Decimal("1.97127971850")
    assert right["attributed_bonus_cost_brl"] == Decimal("6.472824944610")
    assert right["fractional_cost_basis_brl"] == Decimal("6.472824944610")
    assert right["estimated_fractional_result_brl"] == Decimal(
        "-4.501545226110"
    )
    assert right["cash_status"] == "CALCULATED_NOT_CONFIRMED"
    assert right["components"][0]["attributed_cost_brl"] == Decimal(
        "1.2945649889220"
    )
