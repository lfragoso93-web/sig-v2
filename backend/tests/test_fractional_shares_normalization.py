from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import normalize_b3_equity_ticker
from app.models.asset import Asset
from app.models.transaction import OperationType, Transaction
from app.routers.assets import _find_catalog_asset
from app.services.asset_catalog_query_service import suggest_assets_from_catalog
from app.services.asset_provider_verification_service import verify_market_asset_exists
from app.services.snapshot_position_projection import project_transaction_timelines
from app.services.transaction_service import list_transactions_paginated


def test_normalize_b3_equity_ticker_unit_cases():
    assert normalize_b3_equity_ticker("PETR4F") == "PETR4"
    assert normalize_b3_equity_ticker("VALE3F") == "VALE3"
    assert normalize_b3_equity_ticker("B3SA3F") == "B3SA3"
    assert normalize_b3_equity_ticker("BOVA11F") == "BOVA11"
    assert normalize_b3_equity_ticker("MRSA3BF") == "MRSA3B"
    assert normalize_b3_equity_ticker("MXRF11F") == "MXRF11"

    # Standard lot remains unchanged
    assert normalize_b3_equity_ticker("PETR4") == "PETR4"
    assert normalize_b3_equity_ticker("VALE3") == "VALE3"

    # US stocks and cryptos remain untouched
    assert normalize_b3_equity_ticker("AAPL", "STOCK") == "AAPL"
    assert normalize_b3_equity_ticker("F", "STOCK") == "F"
    assert normalize_b3_equity_ticker("BTC", "CRIPTO") == "BTC"
    assert normalize_b3_equity_ticker("ETH", "CRIPTO") == "ETH"


@pytest.mark.asyncio
async def test_find_catalog_asset_resolves_fractional_query_to_standard_asset():
    db = AsyncMock(spec=AsyncSession)
    mock_asset = Asset(id=1, ticker="PETR4", name="Petrobras PN", asset_type="ACAO")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_asset
    db.execute = AsyncMock(return_value=mock_result)

    result = await _find_catalog_asset(db, "PETR4F", "ACAO")
    assert result is not None
    assert result.ticker == "PETR4"

    call_args = db.execute.call_args[0][0]
    compiled_stmt = str(call_args)
    assert "assets" in compiled_stmt.lower()


@pytest.mark.asyncio
async def test_suggest_assets_includes_base_equity_for_fractional_input():
    db = AsyncMock(spec=AsyncSession)
    mock_asset = Asset(id=2, ticker="VALE3", name="Vale S.A.", asset_type="ACAO")
    mock_result = MagicMock()
    mock_result.all.return_value = [(mock_asset, None)]
    db.execute = AsyncMock(return_value=mock_result)

    suggestions = await suggest_assets_from_catalog(db, "VALE3F")
    assert len(suggestions) == 1
    assert suggestions[0].ticker == "VALE3"


@pytest.mark.asyncio
async def test_verify_market_asset_exists_normalizes_fractional_ticker(monkeypatch):
    async def mock_fetch_info(ticker: str):
        if ticker == "PETR4":
            return {"symbol": "PETR4", "longName": "Petróleo Brasileiro S.A."}
        return None

    monkeypatch.setattr("app.integrations.brapi.fetch_asset_info", mock_fetch_info)

    exists, name = await verify_market_asset_exists("PETR4F", "ACAO")
    assert exists is True
    assert name == "Petróleo Brasileiro S.A."


@pytest.mark.asyncio
async def test_list_transactions_paginated_matches_base_and_fractional_ticker():
    db = AsyncMock(spec=AsyncSession)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 2

    mock_tx1 = Transaction(id=10, portfolio_id=1, ticker="PETR4", asset_type="ACAO", quantity=100, price=30.0)
    mock_tx2 = Transaction(id=11, portfolio_id=1, ticker="PETR4", asset_type="ACAO", quantity=25, price=31.0)
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [mock_tx1, mock_tx2]

    db.execute = AsyncMock(side_effect=[count_result, items_result])

    res = await list_transactions_paginated(db, portfolio_id=1, ticker="PETR4F")
    assert res["total"] == 2
    assert len(res["items"]) == 2
    assert all(tx.ticker == "PETR4" for tx in res["items"])


def test_project_transaction_timelines_unifies_fractional_and_standard_ticker():
    tx1 = Transaction(
        id=1,
        portfolio_id=1,
        ticker="PETR4F",
        asset_type="ACAO",
        operation=OperationType.buy,
        quantity=Decimal("100"),
        price=Decimal("30.00"),
        fees=Decimal("0"),
        date=date(2026, 1, 10),
    )
    tx2 = Transaction(
        id=2,
        portfolio_id=1,
        ticker="PETR4",
        asset_type="ACAO",
        operation=OperationType.sell,
        quantity=Decimal("50"),
        price=Decimal("35.00"),
        fees=Decimal("0"),
        date=date(2026, 1, 15),
    )

    timelines = project_transaction_timelines(
        transactions=[tx1, tx2],
        actions_by_ticker={},
        target_date=date(2026, 1, 20),
    )

    assert "PETR4" in timelines
    assert "PETR4F" not in timelines
    proj, asset_type, is_usd = timelines["PETR4"]
    assert proj.quantity == Decimal("50")
    assert proj.average_price == Decimal("30.00")
