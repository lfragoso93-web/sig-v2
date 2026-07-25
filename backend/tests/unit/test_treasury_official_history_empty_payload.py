from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import treasury_official_history_service as service


@pytest.mark.asyncio
async def test_empty_catalog_result_keeps_complete_history_contract(monkeypatch):
    db = SimpleNamespace(commit=AsyncMock())
    monkeypatch.setattr(
        service,
        "_canonical_assets",
        AsyncMock(return_value=({}, {}, ["titulo-sem-alias"])),
    )

    result = await service._rebuild_official_treasury_history(db, commit=False)

    assert result == {
        "official_symbols": 0,
        "matched_assets": 0,
        "imported": 0,
        "official_imported": 0,
        "fallback_imported": 0,
        "official_covered": 0,
        "fallback_symbols": 0,
        "empty_payloads": 0,
        "required_empty_payloads": 0,
        "expected_empty_payloads": 0,
        "required_empty_symbols": [],
        "expected_empty_symbols": [],
        "last_prices_refreshed": 0,
        "primary_source": "tesouro_transparente",
        "fallback_source": "brapi_treasury",
        "alias_groups": 0,
        "aliases": {},
        "unresolved_assets": ["titulo-sem-alias"],
        "history": {},
    }
    db.commit.assert_not_awaited()


def test_classify_empty_symbols_separates_matured_and_active_titles():
    required, expected = service._classify_empty_symbols(
        [
            "tesouro-prefixado-01012027",
            "tesouro-prefixado-01012023",
            "tesouro-renda-mais-2030",
            "titulo-sem-vencimento",
        ],
        today=date(2026, 7, 25),
    )

    assert required == [
        "tesouro-prefixado-01012027",
        "tesouro-renda-mais-2030",
        "titulo-sem-vencimento",
    ]
    assert expected == ["tesouro-prefixado-01012023"]


def test_maturity_date_from_symbol_supports_full_date_and_year_only():
    assert service._maturity_date_from_symbol("tesouro-prefixado-01012031") == date(
        2031,
        1,
        1,
    )
    assert service._maturity_date_from_symbol("tesouro-renda-mais-2045") == date(
        2045,
        12,
        31,
    )
    assert service._maturity_date_from_symbol("titulo-sem-vencimento") is None
