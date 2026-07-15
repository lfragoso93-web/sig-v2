from decimal import Decimal

import pytest

from app.services import portfolio_canonical_valuation_service as service


@pytest.mark.asyncio
async def test_canonical_totals_substitui_proxy_de_renda_fixa(monkeypatch):
    async def fake_legacy(*_args, **_kwargs):
        return {
            "market_value": Decimal("1000.00"),
            "cost_basis": Decimal("1000.00"),
            "invested_total": Decimal("1000.00"),
            "realized_pnl": Decimal("0.00"),
            "unrealized_pnl": Decimal("0.00"),
            "total_pnl": Decimal("0.00"),
            "return_pct": Decimal("0.0000"),
        }

    async def fake_fixed_income(*_args, **_kwargs):
        return {
            "invested_amount": Decimal("400.00"),
            "current_value": Decimal("460.00"),
            "income_amount": Decimal("60.00"),
        }

    monkeypatch.setattr(service, "_legacy_calc_totals", fake_legacy)
    monkeypatch.setattr(service, "_fixed_income_totals_at_date", fake_fixed_income)

    result = await service.calculate_canonical_portfolio_totals(None, 1, None)

    assert result["market_value"] == Decimal("1060.00")
    assert result["unrealized_pnl"] == Decimal("60.00")
    assert result["total_pnl"] == Decimal("60.00")
    assert result["return_pct"] == Decimal("6.0000")
    assert result["fixed_income_current"] == Decimal("460.00")


@pytest.mark.asyncio
async def test_canonical_totals_sem_renda_fixa_preserva_legado(monkeypatch):
    legacy = {
        "market_value": Decimal("850.00"),
        "cost_basis": Decimal("800.00"),
        "invested_total": Decimal("800.00"),
        "realized_pnl": Decimal("0.00"),
        "unrealized_pnl": Decimal("50.00"),
        "total_pnl": Decimal("50.00"),
        "return_pct": Decimal("6.2500"),
    }

    async def fake_legacy(*_args, **_kwargs):
        return dict(legacy)

    async def fake_fixed_income(*_args, **_kwargs):
        return {
            "invested_amount": Decimal("0.00"),
            "current_value": Decimal("0.00"),
            "income_amount": Decimal("0.00"),
        }

    monkeypatch.setattr(service, "_legacy_calc_totals", fake_legacy)
    monkeypatch.setattr(service, "_fixed_income_totals_at_date", fake_fixed_income)

    result = await service.calculate_canonical_portfolio_totals(None, 1, None)

    assert result["market_value"] == legacy["market_value"]
    assert result["unrealized_pnl"] == legacy["unrealized_pnl"]
    assert result["total_pnl"] == legacy["total_pnl"]
    assert result["return_pct"] == legacy["return_pct"]
