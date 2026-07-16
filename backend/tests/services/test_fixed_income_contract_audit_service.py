from datetime import date
from types import SimpleNamespace

import pytest

from app.services.fixed_income_contract_audit_service import audit_fixed_income_contracts


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _Scalars(self._rows)


class _Db:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _statement):
        return _Result(self._rows)


def _tx(ticker, operation, notes):
    return SimpleNamespace(
        id=1,
        portfolio_id=44,
        ticker=ticker,
        asset_type="RENDA_FIXA",
        operation=operation,
        notes=notes,
        date=date(2026, 1, 1),
    )


@pytest.mark.asyncio
async def test_audit_reports_complete_and_incomplete_contracts():
    db = _Db([
        _tx("CDB CDI", "buy", "Indexador: CDI | 120% do CDI | Vencimento: 2027-12-31"),
        _tx("CDB IPCA", "buy", "Indexador: IPCA+ | Taxa: 6,5%"),
        _tx("PORQUINHO", "buy", None),
        _tx("CDB CDI", "sell", None),
    ])

    result = await audit_fixed_income_contracts(db)

    assert result["transactions"] == 4
    assert result["purchases"] == 3
    assert result["redemptions"] == 1
    assert result["contracts_complete"] == 2
    assert result["contracts_incomplete"] == 1
    assert result["coverage_pct"] == pytest.approx(66.67)
    assert result["missing_metadata_tickers"] == {"PORQUINHO": 1}
