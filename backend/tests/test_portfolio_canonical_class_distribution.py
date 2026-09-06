from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.asset import AssetType
from app.services import portfolio_canonical_valuation_service as service


@pytest.mark.asyncio
async def test_canonical_distribution_applies_fixed_income_and_treasury_corrections(monkeypatch):
    base = {
        "market_value": Decimal("38960.00"),
        "cost_basis": Decimal("37629.30"),
        "invested_total": Decimal("37173.50"),
        "realized_pnl": Decimal("450.80"),
        "unrealized_pnl": Decimal("1330.70"),
        "total_pnl": Decimal("1781.50"),
        "return_pct": Decimal("4.6783"),
        "pre_listing_assets": 0,
        "real_price_gaps": 0,
        "market_value_by_class": {
            AssetType.ACAO.value: Decimal("2160.00"),
            AssetType.FII.value: Decimal("2100.00"),
            AssetType.ETF_NACIONAL.value: Decimal("560.00"),
            AssetType.BDR.value: Decimal("1140.00"),
            AssetType.CRIPTO.value: Decimal("21000.00"),
            AssetType.TESOURO_DIRETO.value: Decimal("7000.00"),
            AssetType.RENDA_FIXA.value: Decimal("5000.00"),
        },
    }
    monkeypatch.setattr(
        service,
        "_base_totals_without_dedicated_lookup",
        AsyncMock(return_value=base),
    )
    monkeypatch.setattr(
        service,
        "_fixed_income_totals_at_date",
        AsyncMock(
            return_value={
                "invested_amount": Decimal("5000.00"),
                "current_value": Decimal("5050.00"),
                "income_amount": Decimal("50.00"),
            }
        ),
    )
    monkeypatch.setattr(
        service,
        "_treasury_correction_at_date",
        AsyncMock(return_value={"correction": Decimal("-50.00"), "matched": 1, "unresolved": 0}),
    )

    totals = await service.calculate_canonical_portfolio_totals(None, 13, date(2026, 2, 28))

    assert totals["market_value_by_class"] == {
        "ACAO": Decimal("2160.00"),
        "FII": Decimal("2100.00"),
        "ETF_NACIONAL": Decimal("560.00"),
        "BDR": Decimal("1140.00"),
        "CRIPTO": Decimal("21000.00"),
        "TESOURO_DIRETO": Decimal("6950.00"),
        "RENDA_FIXA": Decimal("5050.00"),
    }
    assert sum(totals["market_value_by_class"].values(), Decimal("0")) == totals["market_value"]
