from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate
from app.services import transaction_write_service as sut


@pytest.mark.asyncio
async def test_create_transaction_record_persists_and_resolves_non_crypto_asset() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    asset_result = MagicMock()
    asset_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=asset_result)
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

    result = await sut.create_transaction_record(
        db,
        portfolio_id=303,
        payload=payload,
    )

    assert result.ticker == "PETR4"
    assert result.portfolio_id == 303
    added_objects = [call.args[0] for call in db.add.call_args_list]
    assert any(isinstance(obj, Asset) and obj.ticker == "PETR4" for obj in added_objects)
    assert result in added_objects
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_add_transaction_record_preserves_caller_transaction_boundary() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    asset_result = MagicMock()
    asset_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=asset_result)
    payload = TransactionCreate(
        ticker="VALE3",
        asset_type="ACAO",
        operation="buy",
        quantity=5,
        price=70,
        fees=0,
        date="2026-01-03",
        currency="BRL",
    )

    result = await sut.add_transaction_record(
        db,
        portfolio_id=303,
        payload=payload,
        flush=True,
    )

    assert isinstance(result, Transaction)
    assert result.ticker == "VALE3"
    assert result.portfolio_id == 303
    assert db.add.call_count == 2
    db.flush.assert_awaited()
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()


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
async def test_sell_quantity_lookup_is_scoped_by_asset_type() -> None:
    db = AsyncMock(spec=AsyncSession)
    rows = MagicMock()
    rows.all.return_value = []
    db.execute = AsyncMock(return_value=rows)
    payload = TransactionCreate(
        ticker="SAME",
        asset_type="ACAO",
        operation="sell",
        quantity=1,
        price=10,
        fees=0,
        date="2026-01-03",
        currency="BRL",
    )

    with pytest.raises(sut.TransactionWriteError, match="Quantidade insuficiente"):
        await sut.add_transaction_record(db, portfolio_id=303, payload=payload)

    statement = db.execute.await_args.args[0]
    assert "transactions.asset_type" in str(statement)
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_treasury_sell_normalizes_human_title_before_quantity_lookup() -> None:
    db = AsyncMock(spec=AsyncSession)
    quantity_rows = MagicMock()
    quantity_rows.all.return_value = [("buy", 1.5)]
    asset_result = MagicMock()
    asset_result.scalar_one_or_none.return_value = object()
    db.execute = AsyncMock(side_effect=[quantity_rows, asset_result])
    db.add = MagicMock()
    payload = TransactionCreate(
        ticker="Tesouro Selic 2029",
        asset_type="TESOURO_DIRETO",
        operation="sell",
        quantity=1,
        price=14000,
        fees=0,
        date="2026-01-03",
        currency="BRL",
    )

    with patch(
        "app.services.transaction_write_service.resolve_treasury_symbol",
        new_callable=AsyncMock,
        return_value="tesouro-selic-01032029",
    ) as resolve_symbol:
        result = await sut.add_transaction_record(
            db,
            portfolio_id=303,
            payload=payload,
        )

    assert result.ticker == "TESOURO-SELIC-01032029"
    resolve_symbol.assert_awaited_once_with(db, "Tesouro Selic 2029")
    quantity_statement = str(
        db.execute.await_args_list[0].args[0].compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    assert "TESOURO-SELIC-01032029" in quantity_statement
    assert result in [call.args[0] for call in db.add.call_args_list]


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
