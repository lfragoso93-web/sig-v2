from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_display_names import format_asset_display_name
from app.integrations.b3_cotahist import CotahistRecord
from app.models.asset import Asset, AssetType
from app.services import portfolio_service
from app.services.asset_seed_service import _upsert_asset
from app.services.b3_cotahist_catalog_service import upsert_b3_cotahist_catalog
from app.services.portfolio_service import get_portfolio_positions


def test_format_asset_display_name_resolves_all_classes() -> None:
    assert format_asset_display_name("MARCOPOLO S.A.", "POMO4", "ACAO") == "Marcopolo"
    assert format_asset_display_name("PETROLEO BRASILEIRO S.A. PETROBRAS", "PETR4", "ACAO") == "Petrobras"
    assert format_asset_display_name("MXRF11", "MXRF11", "FII") == "Maxi Renda FII"
    assert format_asset_display_name("XPML11", "XPML11", "FII") == "XP Malls FII"
    assert format_asset_display_name("BOVA11", "BOVA11", "ETF_NACIONAL") == "iShares Ibovespa ETF"
    assert format_asset_display_name("IVV", "IVV", "ETF_INTERNACIONAL") == "iShares Core S&P 500 ETF"
    assert format_asset_display_name("NIKE34", "NIKE34", "BDR") == "Nike"
    assert format_asset_display_name("NVDA", "NVDA", "STOCK") == "NVIDIA"
    assert format_asset_display_name("BTC", "BTC", "CRIPTO") == "Bitcoin"
    assert (
        format_asset_display_name("TESOURO-RENDA-MAIS-2065", "TESOURO-RENDA-MAIS-2065", "TESOURO_DIRETO")
        == "Tesouro Renda+ 2065"
    )
    assert (
        format_asset_display_name(None, "tesouro-renda-mais-15122079", "TESOURO_DIRETO")
        == "Tesouro Renda+ 2060"
    )
    assert (
        format_asset_display_name(None, "tesouro-educa-15122030", "TESOURO_DIRETO")
        == "Tesouro Educa+ 2026"
    )


def test_format_asset_display_name_preserves_mixed_case_and_cleans_all_caps() -> None:
    assert format_asset_display_name("Petrobras PN", "PETR4", "ACAO") == "Petrobras PN"
    assert (
        format_asset_display_name(
            "Tesouro Selic 2028", "tesouro-selic-01032028", "TESOURO_DIRETO"
        )
        == "Tesouro Selic 2028"
    )
    assert (
        format_asset_display_name("CIA ENERGETICA DO CEARA S.A.", "COCE5", "ACAO")
        == "Companhia Energetica do Ceara"
    )
    assert (
        format_asset_display_name(None, "UNKN3", "ACAO", fallback_label="Ações")
        == "Ações"
    )


@pytest.mark.asyncio
async def test_get_portfolio_positions_uses_company_display_name_in_asset_label(monkeypatch) -> None:
    db = AsyncMock(spec=AsyncSession)
    enriched_positions = [
        {
            "ticker": "POMO4",
            "asset_type": "ACAO",
            "quantity": 100.0,
            "avg_price": 7.0,
            "avg_price_usd": None,
            "total_invested": 700.0,
            "current_price": 8.5,
            "current_price_usd": None,
            "current_value": 850.0,
            "result_abs": 150.0,
            "result_pct": 21.4286,
            "is_usd": False,
        },
        {
            "ticker": "MXRF11",
            "asset_type": "FII",
            "quantity": 50.0,
            "avg_price": 10.0,
            "avg_price_usd": None,
            "total_invested": 500.0,
            "current_price": 10.2,
            "current_price_usd": None,
            "current_value": 510.0,
            "result_abs": 10.0,
            "result_pct": 2.0,
            "is_usd": False,
        },
    ]

    monkeypatch.setattr(portfolio_service, "cache_get", AsyncMock(return_value=None))
    monkeypatch.setattr(portfolio_service, "cache_set", AsyncMock())
    monkeypatch.setattr(portfolio_service, "get_portfolio", AsyncMock(return_value=SimpleNamespace(id=1)))
    monkeypatch.setattr(portfolio_service, "_non_fixed_income_enriched", AsyncMock(return_value=enriched_positions))
    monkeypatch.setattr(portfolio_service, "get_targets_map", AsyncMock(return_value={}))
    monkeypatch.setattr(portfolio_service, "_fetch_previous_prices_batch", AsyncMock(return_value=({}, None)))
    monkeypatch.setattr(portfolio_service, "_fetch_logos_batch", AsyncMock(return_value={}))
    monkeypatch.setattr(
        portfolio_service,
        "_fetch_asset_names_batch",
        AsyncMock(
            return_value={
                ("POMO4", "ACAO"): "MARCOPOLO S.A.",
                ("MXRF11", "FII"): "MXRF11",
            }
        ),
    )
    monkeypatch.setattr(portfolio_service, "sum_dividends_by_ticker", AsyncMock(return_value={}))
    monkeypatch.setattr(
        portfolio_service,
        "get_fixed_income_valuations_with_coverage_fallback",
        AsyncMock(return_value=([], None)),
    )

    groups = await get_portfolio_positions(db, portfolio_id=1, user_id=1)
    by_type = {g["asset_type"]: g for g in groups}

    assert by_type["ACAO"]["label"] == "Ações"
    assert by_type["ACAO"]["positions"][0]["ticker"] == "POMO4"
    assert by_type["ACAO"]["positions"][0]["asset_label"] == "Marcopolo"

    assert by_type["FII"]["label"] == "FIIs"
    assert by_type["FII"]["positions"][0]["ticker"] == "MXRF11"
    assert by_type["FII"]["positions"][0]["asset_label"] == "Maxi Renda FII"


@pytest.mark.asyncio
async def test_catalog_services_overwrite_placeholder_ticker_names(db: AsyncSession) -> None:
    db.add_all([
        Asset(ticker="MXRF11", name="MXRF11", asset_type=AssetType.FII.value, currency="BRL"),
        Asset(ticker="BTC", name="BTC", asset_type=AssetType.CRIPTO.value, currency="BRL"),
    ])
    await db.commit()

    cotahist_res = await upsert_b3_cotahist_catalog(
        db,
        [
            CotahistRecord(
                timestamp=datetime(2026, 8, 28, tzinfo=timezone.utc),
                ticker="MXRF11",
                market_type="010",
                short_name="FII MAXI RENDA",
                specification="CI",
                currency="R$",
                open=Decimal("10.00"),
                high=Decimal("10.10"),
                low=Decimal("9.90"),
                close=Decimal("10.05"),
                volume=Decimal("100000.00"),
                quotation_factor=1,
                isin="BRMXRFCTF008",
            )
        ],
    )
    seed_status = await _upsert_asset(db, "BTC", "Bitcoin", AssetType.CRIPTO, None)
    await db.commit()

    mxrf = (await db.execute(select(Asset).where(Asset.ticker == "MXRF11"))).scalar_one()
    btc = (await db.execute(select(Asset).where(Asset.ticker == "BTC"))).scalar_one()

    assert cotahist_res.updated == 1
    assert mxrf.name == "FII MAXI RENDA"
    assert seed_status == "updated"
    assert btc.name == "Bitcoin"


@pytest.mark.asyncio
async def test_fetch_asset_names_batch_keys_by_ticker_and_asset_type(db: AsyncSession) -> None:
    db.add_all([
        Asset(ticker="DIA", name="DIA Crypto", asset_type=AssetType.CRIPTO.value, currency="BRL"),
        Asset(
            ticker="DIA",
            name="SPDR Dow Jones Industrial Average ETF",
            asset_type=AssetType.ETF_INTERNACIONAL.value,
            currency="USD",
        ),
    ])
    await db.commit()

    names = await portfolio_service._fetch_asset_names_batch(db, ["DIA"])
    assert names[("DIA", "CRIPTO")] == "DIA Crypto"
    assert names[("DIA", "ETF_INTERNACIONAL")] == "SPDR Dow Jones Industrial Average ETF"

