from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.transaction import TransactionCreate
from app.services import transaction_write_service as sut


@pytest.mark.asyncio
async def test_create_transaction_record_persists_and_resolves_non_crypto_asset() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    payload = TransactionCreate(
        ticker=" petr4 ",
        asset_type="ACAO",
        operation="buy",
        quantity=10,
        price=20,
        fees=1,
        date="2026-01-02",
        currency="BRL",
        notes="test",
    )

    with patch(
        "app.services.transaction_write_service.get_or_create_asset",
        new_callable=AsyncMock,
        return_value=(SimpleNamespace(ticker="PETR4"), True),
    ) as get_or_create_asset:
        result = await sut.create_transaction_record(
            db,
            portfolio_id=303,
            payload=payload,
        )

    assert result.ticker == "PETR4"
    assert result.portfolio_id == 303
    db.add.assert_called_once_with(result)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(result)
    get_or_create_asset.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_transaction_record_rejects_sell_above_current_quantity() -> None:
    db = AsyncMock(spec=AsyncSession)
    rows = MagicMock()
    rows.all.return_value = [("buy", 5)]
    db.execute = AsyncMock(return_value=rows)
    payload = TransactionCreate(
        ticker="PETR4",
        asset_type="ACAO",
        operation="sell",
        quantity=6,
        price=25,
        fees=0,
        date="2026-01-03",
        currency="BRL",
    )

    with pytest.raises(sut.TransactionWriteError, match="Quantidade insuficiente"):
        await sut.create_transaction_record(db, portfolio_id=303, payload=payload)

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_transaction_record_requires_crypto_eligibility() -> None:
    db = AsyncMock(spec=AsyncSession)
    payload = TransactionCreate(
        ticker="CERT303-BTC",
        asset_type="CRIPTO",
        operation="buy",
        quantity=0.1,
        price=200000,
        fees=20,
        date="2026-01-08",
        currency="BRL",
    )

    with patch(
        "app.services.transaction_write_service.require_financially_certified_crypto_asset",
        new_callable=AsyncMock,
        side_effect=Exception("unexpected"),
    ):
        with pytest.raises(Exception, match="unexpected"):
            await sut.create_transaction_record(db, portfolio_id=303, payload=payload)
