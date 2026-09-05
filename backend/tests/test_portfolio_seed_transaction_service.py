from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_seed_transaction_service import seed_transactions


FIXTURE_ORDER = [
    "PETR4",
    "PETR4",
    "PETR4",
    "MXRF11",
    "BOVA11",
    "AAPL34",
    "BTC",
    "TESOURO-SELIC-2029",
    "CDB-SYN-CDI-2028",
    "BOVA11",
    "BOVA11",
]


def _owned_asset(source_ticker: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=303,
        name=f"SGI certification #303 synthetic asset [{source_ticker}]",
        provider="synthetic-certification",
        provider_symbol=source_ticker,
        provider_status="synthetic-owned",
    )


@pytest.mark.asyncio
async def test_seed_creates_full_fixture_and_crypto_membership() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    execute_results = []
    for source_ticker in FIXTURE_ORDER:
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = None
        execute_results.append(asset_result)

        if source_ticker == "BTC":
            membership_result = MagicMock()
            membership_result.scalar_one_or_none.return_value = None
            execute_results.append(membership_result)

        transaction_result = MagicMock()
        transaction_result.scalar_one_or_none.return_value = None
        execute_results.append(transaction_result)
    db.execute = AsyncMock(side_effect=execute_results)

    async def refresh_with_id(asset):
        if getattr(asset, "ticker", None) == "CERT303-BTC":
            asset.id = 303

    db.refresh.side_effect = refresh_with_id

    with patch(
        "app.certification.portfolio_seed_transaction_service.create_transaction_record",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(id=1),
    ) as create_record:
        result = await seed_transactions(db, portfolio_id=303)

    assert result.created == 11
    assert result.reused == 0
    assert result.crypto_membership_created == 1
    assert result.crypto_membership_reused == 0
    assert create_record.await_count == 11
    assert "CERT303-BTC" in [
        call.kwargs["payload"].ticker for call in create_record.await_args_list
    ]


@pytest.mark.asyncio
async def test_seed_replay_reuses_full_fixture_and_crypto_membership() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    execute_results = []
    for source_ticker in FIXTURE_ORDER:
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = _owned_asset(source_ticker)
        execute_results.append(asset_result)

        if source_ticker == "BTC":
            membership_result = MagicMock()
            membership_result.scalar_one_or_none.return_value = SimpleNamespace(
                source="synthetic-certification"
            )
            execute_results.append(membership_result)

        transaction_result = MagicMock()
        transaction_result.scalar_one_or_none.return_value = object()
        execute_results.append(transaction_result)
    db.execute = AsyncMock(side_effect=execute_results)

    with patch(
        "app.certification.portfolio_seed_transaction_service.create_transaction_record",
        new_callable=AsyncMock,
    ) as create_record:
        result = await seed_transactions(db, portfolio_id=303)

    assert result.created == 0
    assert result.reused == 11
    assert result.crypto_membership_created == 0
    assert result.crypto_membership_reused == 1
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
        await seed_transactions(db, portfolio_id=303)


@pytest.mark.asyncio
async def test_seed_fails_closed_on_crypto_membership_source_collision() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    execute_results = []
    for source_ticker in FIXTURE_ORDER:
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = _owned_asset(source_ticker)
        execute_results.append(asset_result)

        if source_ticker == "BTC":
            membership_result = MagicMock()
            membership_result.scalar_one_or_none.return_value = SimpleNamespace(
                source="unexpected-source"
            )
            execute_results.append(membership_result)
            break

        transaction_result = MagicMock()
        transaction_result.scalar_one_or_none.return_value = object()
        execute_results.append(transaction_result)
    db.execute = AsyncMock(side_effect=execute_results)

    with pytest.raises(SyntheticSeedContractError, match="membership collision"):
        await seed_transactions(db, portfolio_id=303)
