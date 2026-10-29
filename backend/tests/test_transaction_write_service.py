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
    assert "lower(transactions.ticker)" in quantity_statement
    assert "tesouro-selic-01032029" in quantity_statement
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
        "app.services.transaction_write_service.require_catalog_crypto_asset",
        new_callable=AsyncMock,
        side_effect=Exception("unexpected"),
    ):
        with pytest.raises(Exception, match="unexpected"):
            await sut.create_transaction_record(db, portfolio_id=303, payload=payload)


@pytest.mark.asyncio
async def test_create_transaction_rejects_non_existent_asset() -> None:
    db = AsyncMock(spec=AsyncSession)
    asset_result = MagicMock()
    asset_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=asset_result)

    payload = TransactionCreate(
        ticker="INVENTADO123",
        asset_type="ACAO",
        operation="buy",
        quantity=10,
        price=15,
        fees=0,
        date="2026-01-02",
        currency="BRL",
    )

    with patch(
        "app.services.asset_provider_verification_service.verify_market_asset_exists",
        new_callable=AsyncMock,
        return_value=(False, None),
    ):
        with pytest.raises(sut.TransactionWriteError, match="não existe no catálogo e não foi encontrado nos provedores"):
            await sut.create_transaction_record(db, portfolio_id=303, payload=payload)


@pytest.mark.asyncio
async def test_create_crypto_transaction_by_name_resolves_and_saves_ticker() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    payload = TransactionCreate(
        ticker="Bitcoin",
        asset_type="CRIPTO",
        operation="buy",
        quantity=0.5,
        price=350000,
        fees=10,
        date="2026-01-02",
        currency="BRL",
    )

    fake_crypto_asset = MagicMock(spec=Asset)
    fake_crypto_asset.ticker = "BTC"

    with patch(
        "app.services.transaction_write_service.require_catalog_crypto_asset",
        new_callable=AsyncMock,
        return_value=fake_crypto_asset,
    ):
        result = await sut.create_transaction_record(db, portfolio_id=303, payload=payload)

    assert result.ticker == "BTC"
    assert result.asset_type == "CRIPTO"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_crypto_rejects_non_existent_crypto() -> None:
    from app.services.crypto_transaction_eligibility_service import CryptoTransactionEligibilityError
    db = AsyncMock(spec=AsyncSession)

    payload = TransactionCreate(
        ticker="FAKECOIN999",
        asset_type="CRIPTO",
        operation="buy",
        quantity=10,
        price=1,
        fees=0,
        date="2026-01-02",
        currency="BRL",
    )

    with patch(
        "app.services.transaction_write_service.require_catalog_crypto_asset",
        new_callable=AsyncMock,
        side_effect=CryptoTransactionEligibilityError(ticker="FAKECOIN999", reason="nao existe"),
    ):
        with patch(
            "app.services.asset_provider_verification_service.verify_market_asset_exists",
            new_callable=AsyncMock,
            return_value=(False, None),
        ):
            with pytest.raises(sut.TransactionWriteError, match="não existe no catálogo e não foi encontrada nos provedores"):
                await sut.create_transaction_record(db, portfolio_id=303, payload=payload)


@pytest.mark.asyncio
async def test_sell_quantity_respects_corporate_action_splits() -> None:
    from datetime import date
    from decimal import Decimal
    from app.services.corporate_action_engine import NormalizedCorporateAction, CorporateActionKind

    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # Mock asset check in catalog
    asset_result = MagicMock()
    asset_result.scalar_one_or_none.return_value = object()

    # Buy 100 on 2026-01-01
    tx_rows = MagicMock()
    tx_rows.all.return_value = [("buy", 100.0, date(2026, 1, 1))]

    split_action = NormalizedCorporateAction(
        source="test",
        source_event_id="evt-split-1",
        ticker="PETR4",
        event_date=date(2026, 1, 10),
        kind=CorporateActionKind.SPLIT,
        quantity_factor=Decimal("2.0"),
        raw_payload={},
    )

    alias_result = MagicMock()
    alias_result.scalar_one_or_none.return_value = None

    db.execute = AsyncMock(side_effect=[alias_result, tx_rows, asset_result])

    with patch(
        "app.services.corporate_action_position_reader.load_global_corporate_actions_by_ticker",
        new_callable=AsyncMock,
        return_value={"PETR4": (split_action,)},
    ):
        # Selling 150 after 1:2 split (original 100 becomes 200) must succeed
        payload_150 = TransactionCreate(
            ticker="PETR4",
            asset_type="ACAO",
            operation="sell",
            quantity=150,
            price=30,
            fees=0,
            date="2026-01-15",
            currency="BRL",
        )
        tx = await sut.create_transaction_record(db, portfolio_id=303, payload=payload_150)
        assert tx.quantity == 150
        assert tx.ticker == "PETR4"

    # Selling 250 when available is 200 must fail
    db.execute = AsyncMock(side_effect=[alias_result, tx_rows, asset_result])
    with patch(
        "app.services.corporate_action_position_reader.load_global_corporate_actions_by_ticker",
        new_callable=AsyncMock,
        return_value={"PETR4": (split_action,)},
    ):
        payload_250 = TransactionCreate(
            ticker="PETR4",
            asset_type="ACAO",
            operation="sell",
            quantity=250,
            price=30,
            fees=0,
            date="2026-01-15",
            currency="BRL",
        )
        with pytest.raises(sut.TransactionWriteError, match="Quantidade insuficiente para venda de PETR4. Posicao atual: 200.0000 | Tentativa: 250.0000"):
            await sut.create_transaction_record(db, portfolio_id=303, payload=payload_250)
