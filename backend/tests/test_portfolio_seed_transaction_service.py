from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_seed_transaction_service import (
    LEGACY_SYNTHETIC_CDB_NOTES,
    SYNTHETIC_CDB_TICKER,
    _reconcile_existing_certification_notes,
    seed_transactions,
)


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
CANONICAL_CDB_NOTES = (
    "synthetic fixed income | Indexador: CDI | Taxa: 100% | "
    "Benchmark Source: synthetic-certification"
)


def _owned_asset(source_ticker: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=303,
        ticker=f"CERT303-{source_ticker}",
        name=f"SGI certification #303 synthetic asset [{source_ticker}]",
        provider="synthetic-certification",
        provider_symbol=source_ticker,
        provider_status="synthetic-owned",
    )


def _preflight_result(transactions: list[SimpleNamespace] | None = None) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = transactions or []
    return result


@pytest.mark.asyncio
async def test_seed_creates_full_fixture_and_crypto_membership() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    execute_results = [_preflight_result()]
    for source_ticker in FIXTURE_ORDER:
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = _owned_asset(source_ticker)
        execute_results.append(asset_result)

        if source_ticker == "BTC":
            membership_result = MagicMock()
            membership_result.scalar_one_or_none.return_value = None
            execute_results.append(membership_result)

        transaction_result = MagicMock()
        transaction_result.scalar_one_or_none.return_value = None
        execute_results.append(transaction_result)
    db.execute = AsyncMock(side_effect=execute_results)

    created_tx = SimpleNamespace(id=1)
    with patch(
        "app.certification.portfolio_seed_transaction_service.create_transaction_record",
        new_callable=AsyncMock,
        return_value=created_tx,
    ) as create_record:
        result = await seed_transactions(db, portfolio_id=303)

    assert result.created == 11
    assert result.reused == 0
    assert result.crypto_membership_created == 1
    assert result.crypto_membership_reused == 0
    assert create_record.await_count == 11
    assert db.add.call_count == 1
    assert db.commit.await_count == 1

    tickers = [call.kwargs["payload"].ticker for call in create_record.await_args_list]
    assert "CERT303-BTC" in tickers
    assert "CERT303-PETR4" in tickers
    assert "CERT303-MXRF11" in tickers
    assert "CERT303-TESOURO-SELIC-2029" in tickers
    assert "CERT303-CDB-SYN-CDI-2028" in tickers

    cdb_payload = next(
        call.kwargs["payload"]
        for call in create_record.await_args_list
        if call.kwargs["payload"].ticker == SYNTHETIC_CDB_TICKER
    )
    assert cdb_payload.notes == CANONICAL_CDB_NOTES


@pytest.mark.asyncio
async def test_seed_replay_reuses_full_fixture_and_crypto_membership() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    execute_results = [_preflight_result()]
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
        notes = CANONICAL_CDB_NOTES if source_ticker == "CDB-SYN-CDI-2028" else None
        transaction_result.scalar_one_or_none.return_value = SimpleNamespace(notes=notes)
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
async def test_reconcile_upgrades_only_exact_legacy_cdb_note() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    transaction = SimpleNamespace(notes=LEGACY_SYNTHETIC_CDB_NOTES)

    await _reconcile_existing_certification_notes(
        db,
        transaction=transaction,
        row={"notes": CANONICAL_CDB_NOTES},
        ticker=SYNTHETIC_CDB_TICKER,
    )

    assert transaction.notes == CANONICAL_CDB_NOTES
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconcile_fails_closed_on_unknown_cdb_note() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    transaction = SimpleNamespace(notes="unexpected CDB provenance")

    with pytest.raises(SyntheticSeedContractError, match="note collision"):
        await _reconcile_existing_certification_notes(
            db,
            transaction=transaction,
            row={"notes": CANONICAL_CDB_NOTES},
            ticker=SYNTHETIC_CDB_TICKER,
        )

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_fails_closed_on_unexpected_existing_transaction() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    unexpected = SimpleNamespace(
        portfolio_id=303,
        ticker="CERT303-UNEXPECTED",
        asset_type="ACAO",
        operation="buy",
        quantity=1.0,
        price=1.0,
        date=date(2026, 1, 1),
        fees=0.0,
        currency="BRL",
    )
    db.execute = AsyncMock(side_effect=[_preflight_result([unexpected])])

    with patch(
        "app.certification.portfolio_seed_transaction_service.create_transaction_record",
        new_callable=AsyncMock,
    ) as create_record:
        with pytest.raises(
            SyntheticSeedContractError,
            match="unexpected transaction state; ticker=CERT303-UNEXPECTED",
        ):
            await seed_transactions(db, portfolio_id=303)

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
    db.execute = AsyncMock(side_effect=[_preflight_result(), collision])

    with pytest.raises(SyntheticSeedContractError, match="ownership is ambiguous"):
        await seed_transactions(db, portfolio_id=303)


@pytest.mark.asyncio
async def test_seed_fails_closed_on_crypto_membership_source_collision() -> None:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    execute_results = [_preflight_result()]
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
        transaction_result.scalar_one_or_none.return_value = SimpleNamespace(notes=None)
        execute_results.append(transaction_result)
    db.execute = AsyncMock(side_effect=execute_results)

    with pytest.raises(
        SyntheticSeedContractError,
        match="synthetic crypto membership collision for CERT303-BTC",
    ):
        await seed_transactions(db, portfolio_id=303)
