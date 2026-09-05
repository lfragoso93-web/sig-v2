from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_seed_transaction_service import (
    seed_non_crypto_transactions,
)


@pytest.mark.asyncio
async def test_seed_creates_ten_non_crypto_transactions_and_blocks_crypto() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    asset_results = []
    transaction_results = []
    for _ in range(10):
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = None
        asset_results.append(asset_result)

        transaction_result = MagicMock()
        transaction_result.scalar_one_or_none.return_value = None
        transaction_results.append(transaction_result)

    execute_results = []
    for asset_result, transaction_result in zip(asset_results, transaction_results):
        execute_results.extend([asset_result, transaction_result])
    db.execute = AsyncMock(side_effect=execute_results)

    created_tx = SimpleNamespace(id=1)
    with patch(
        "app.certification.portfolio_seed_transaction_service.create_transaction_record",
        new_callable=AsyncMock,
        return_value=created_tx,
    ) as create_record:
        result = await seed_non_crypto_transactions(db, portfolio_id=303)

    assert result.created == 10
    assert result.reused == 0
    assert result.blocked_crypto == 1
    assert create_record.await_count == 10
    assert db.add.call_count == 10
    assert db.commit.await_count == 10
    assert db.refresh.await_count == 10

    tickers = [call.kwargs["payload"].ticker for call in create_record.await_args_list]
    assert "CERT303-BTC" not in tickers
    assert "CERT303-PETR4" in tickers
    assert "CERT303-MXRF11" in tickers
    assert "CERT303-TESOURO-SELIC-2029" in tickers
    assert "CERT303-CDB-SYN-CDI-2028" in tickers


@pytest.mark.asyncio
async def test_seed_replay_reuses_all_non_crypto_transactions_without_writes() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    execute_results = []
    for index in range(10):
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = SimpleNamespace(
            name=(
                "SGI certification #303 synthetic asset [PETR4]"
                if index < 3
                else None
            ),
            provider="synthetic-certification",
            provider_symbol=None,
            provider_status="synthetic-owned",
        )
        execute_results.append(asset_result)

        transaction_result = MagicMock()
        transaction_result.scalar_one_or_none.return_value = object()
        execute_results.append(transaction_result)

    fixture_order = [
        "PETR4",
        "PETR4",
        "PETR4",
        "MXRF11",
        "BOVA11",
        "AAPL34",
        "TESOURO-SELIC-2029",
        "CDB-SYN-CDI-2028",
        "BOVA11",
        "BOVA11",
    ]
    asset_cursor = 0
    adjusted_results = []
    for source_ticker in fixture_order:
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = SimpleNamespace(
            name=f"SGI certification #303 synthetic asset [{source_ticker}]",
            provider="synthetic-certification",
            provider_symbol=source_ticker,
            provider_status="synthetic-owned",
        )
        transaction_result = MagicMock()
        transaction_result.scalar_one_or_none.return_value = object()
        adjusted_results.extend([asset_result, transaction_result])
        asset_cursor += 1
    db.execute = AsyncMock(side_effect=adjusted_results)

    with patch(
        "app.certification.portfolio_seed_transaction_service.create_transaction_record",
        new_callable=AsyncMock,
    ) as create_record:
        result = await seed_non_crypto_transactions(db, portfolio_id=303)

    assert result.created == 0
    assert result.reused == 10
    assert result.blocked_crypto == 1
    create_record.assert_not_awaited()
    db.add.assert_not_called()
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_fails_closed_on_asset_namespace_collision() -> None:
    db = AsyncMock(spec=AsyncSession)
    collision = MagicMock()
    collision.scalar_one_or_none.return_value = SimpleNamespace(
        name="real asset accidentally using reserved namespace",
        provider="brapi",
        provider_symbol="PETR4",
        provider_status="READY",
    )
    db.execute = AsyncMock(return_value=collision)

    with pytest.raises(SyntheticSeedContractError, match="ownership is ambiguous"):
        await seed_non_crypto_transactions(db, portfolio_id=303)
