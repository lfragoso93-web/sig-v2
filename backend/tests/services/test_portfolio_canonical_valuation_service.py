from decimal import Decimal

import pytest

from app.services import portfolio_canonical_valuation_service as service


async def _treasury_without_correction(*_args, **_kwargs):
    return {
        "correction": Decimal("0.00"),
        "matched": 0,
        "unresolved": 0,
    }


@pytest.mark.asyncio
async def test_canonical_totals_substitui_proxy_de_renda_fixa(monkeypatch):
    async def fake_base(*_args, **_kwargs):
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

    monkeypatch.setattr(service, "_base_totals_without_dedicated_lookup", fake_base)
    monkeypatch.setattr(service, "_fixed_income_totals_at_date", fake_fixed_income)
    monkeypatch.setattr(service, "_treasury_correction_at_date", _treasury_without_correction)

    result = await service.calculate_canonical_portfolio_totals(None, 1, None)

    assert result["market_value"] == Decimal("1060.00")
    assert result["unrealized_pnl"] == Decimal("60.00")
    assert result["total_pnl"] == Decimal("60.00")
    assert result["return_pct"] == Decimal("6.0000")
    assert result["fixed_income_current"] == Decimal("460.00")


@pytest.mark.asyncio
async def test_canonical_totals_sem_renda_fixa_preserva_base(monkeypatch):
    base = {
        "market_value": Decimal("850.00"),
        "cost_basis": Decimal("800.00"),
        "invested_total": Decimal("800.00"),
        "realized_pnl": Decimal("0.00"),
        "unrealized_pnl": Decimal("50.00"),
        "total_pnl": Decimal("50.00"),
        "return_pct": Decimal("6.2500"),
    }

    async def fake_base(*_args, **_kwargs):
        return dict(base)

    async def fake_fixed_income(*_args, **_kwargs):
        return {
            "invested_amount": Decimal("0.00"),
            "current_value": Decimal("0.00"),
            "income_amount": Decimal("0.00"),
        }

    monkeypatch.setattr(service, "_base_totals_without_dedicated_lookup", fake_base)
    monkeypatch.setattr(service, "_fixed_income_totals_at_date", fake_fixed_income)
    monkeypatch.setattr(service, "_treasury_correction_at_date", _treasury_without_correction)

    result = await service.calculate_canonical_portfolio_totals(None, 1, None)

    assert result["market_value"] == base["market_value"]
    assert result["unrealized_pnl"] == base["unrealized_pnl"]
    assert result["total_pnl"] == base["total_pnl"]
    assert result["return_pct"] == base["return_pct"]
