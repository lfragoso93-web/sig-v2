from decimal import Decimal
from datetime import date

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
            "market_value_by_class": {
                "ACAO": Decimal("600.00"),
                "RENDA_FIXA": Decimal("400.00"),
            },
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
        "market_value_by_class": {"ACAO": Decimal("850.00")},
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
    assert result["market_value_by_class"] == base["market_value_by_class"]


@pytest.mark.asyncio
async def test_canonical_totals_reconciles_cent_class_rounding(monkeypatch):
    async def fake_base(*_args, **_kwargs):
        return {
            "market_value": Decimal("19750.93"),
            "cost_basis": Decimal("19750.93"),
            "invested_total": Decimal("19750.93"),
            "realized_pnl": Decimal("0.00"),
            "unrealized_pnl": Decimal("0.00"),
            "total_pnl": Decimal("0.00"),
            "return_pct": Decimal("0.0000"),
            "market_value_by_class": {
                "ACAO": Decimal("10000.00"),
                "CRIPTO": Decimal("9750.91"),
            },
        }

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

    assert result["market_value"] == Decimal("19750.93")
    assert sum(result["market_value_by_class"].values(), Decimal("0")) == Decimal("19750.93")
    assert result["market_value_by_class"]["ACAO"] == Decimal("10000.02")


@pytest.mark.asyncio
async def test_canonical_totals_rejects_material_class_divergence(monkeypatch):
    async def fake_base(*_args, **_kwargs):
        return {
            "market_value": Decimal("19750.93"),
            "cost_basis": Decimal("19750.93"),
            "invested_total": Decimal("19750.93"),
            "realized_pnl": Decimal("0.00"),
            "unrealized_pnl": Decimal("0.00"),
            "total_pnl": Decimal("0.00"),
            "return_pct": Decimal("0.0000"),
            "market_value_by_class": {
                "ACAO": Decimal("10000.00"),
                "CRIPTO": Decimal("9750.90"),
            },
        }

    async def fake_fixed_income(*_args, **_kwargs):
        return {
            "invested_amount": Decimal("0.00"),
            "current_value": Decimal("0.00"),
            "income_amount": Decimal("0.00"),
        }

    monkeypatch.setattr(service, "_base_totals_without_dedicated_lookup", fake_base)
    monkeypatch.setattr(service, "_fixed_income_totals_at_date", fake_fixed_income)
    monkeypatch.setattr(service, "_treasury_correction_at_date", _treasury_without_correction)

    with pytest.raises(RuntimeError, match="classes=19750.90 total=19750.93"):
        await service.calculate_canonical_portfolio_totals(None, 1, None)


@pytest.mark.asyncio
async def test_canonical_totals_reuses_preloaded_transactions_for_fixed_income(
    monkeypatch,
):
    transactions = [object()]
    captured = {}

    async def fake_base(*_args, **_kwargs):
        return {
            "market_value": Decimal("1000.00"),
            "cost_basis": Decimal("1000.00"),
            "invested_total": Decimal("1000.00"),
            "realized_pnl": Decimal("0.00"),
            "unrealized_pnl": Decimal("0.00"),
            "total_pnl": Decimal("0.00"),
            "return_pct": Decimal("0.0000"),
            "market_value_by_class": {
                "RENDA_FIXA": Decimal("1000.00"),
            },
        }

    async def fake_fixed_income(*_args, **kwargs):
        captured["transactions"] = kwargs.get("transactions")
        return {
            "invested_amount": Decimal("1000.00"),
            "current_value": Decimal("1010.00"),
            "income_amount": Decimal("10.00"),
        }

    monkeypatch.setattr(service, "_base_totals_without_dedicated_lookup", fake_base)
    monkeypatch.setattr(service, "_fixed_income_totals_at_date", fake_fixed_income)
    monkeypatch.setattr(service, "_treasury_correction_at_date", _treasury_without_correction)

    result = await service.calculate_canonical_portfolio_totals(
        None,
        1,
        date(2026, 1, 2),
        transactions=transactions,
    )

    assert captured["transactions"] is transactions
    assert result["market_value"] == Decimal("1010.00")
