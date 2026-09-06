"""Idempotent synthetic transaction seeding for certification issue #303."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_asset_policy import build_synthetic_asset_plan
from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.models.asset import Asset
from app.models.asset_universe_membership import AssetUniverseMembership
from app.models.transaction import OperationType, Transaction
from app.schemas.transaction import TransactionCreate
from app.services.asset_universe_membership_service import (
    CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
    CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE,
)
from app.services.transaction_write_service import create_transaction_record

SYNTHETIC_CDB_TICKER = "CERT303-CDB-SYN-CDI-2028"
LEGACY_SYNTHETIC_CDB_NOTES = "synthetic fixed income CDI"


@dataclass(frozen=True)
class SyntheticTransactionSeedResult:
    created: int
    reused: int
    crypto_membership_created: int
    crypto_membership_reused: int


def _identity_tuple(*, portfolio_id: int, row: dict[str, str], ticker: str) -> tuple:
    return (
        portfolio_id,
        ticker,
        row["asset_type"],
        row["operation"],
        float(row["quantity"]),
        float(row["price"]),
        date.fromisoformat(row["date"]),
        float(row.get("fees", "0") or 0),
        row.get("currency", "BRL"),
    )


def _persisted_identity_tuple(transaction: Transaction) -> tuple:
    operation = transaction.operation
    if isinstance(operation, OperationType):
        operation = operation.value
    return (
        transaction.portfolio_id,
        transaction.ticker,
        transaction.asset_type,
        str(operation),
        float(transaction.quantity),
        float(transaction.price),
        transaction.date,
        float(transaction.fees or 0),
        transaction.currency,
    )


async def _assert_existing_transactions_are_expected(
    db: AsyncSession,
    *,
    portfolio_id: int,
    fixture: dict,
    plan: dict,
) -> None:
    expected = Counter(
        _identity_tuple(
            portfolio_id=portfolio_id,
            row=row,
            ticker=plan[row["ticker"]].ticker,
        )
        for row in fixture["transactions"]
    )
    result = await db.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    )
    existing = list(result.scalars().all())
    actual = Counter(_persisted_identity_tuple(transaction) for transaction in existing)

    unexpected = actual - expected
    if unexpected:
        identity, count = next(iter(unexpected.items()))
        raise SyntheticSeedContractError(
            "synthetic portfolio contains unexpected transaction state; "
            f"ticker={identity[1]} excess_count={count}"
        )


async def _find_existing_transaction(
    db: AsyncSession,
    *,
    portfolio_id: int,
    row: dict[str, str],
    ticker: str,
) -> Transaction | None:
    _, _, asset_type, operation, quantity, price, tx_date, fees, currency = _identity_tuple(
        portfolio_id=portfolio_id,
        row=row,
        ticker=ticker,
    )
    result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
            Transaction.asset_type == asset_type,
            Transaction.operation == OperationType(operation),
            Transaction.quantity == quantity,
            Transaction.price == price,
            Transaction.date == tx_date,
            Transaction.fees == fees,
            Transaction.currency == currency,
        )
    )
    return result.scalar_one_or_none()


async def _reconcile_existing_certification_notes(
    db: AsyncSession,
    *,
    transaction: Transaction,
    row: dict[str, str],
    ticker: str,
) -> None:
    """Upgrade only the known legacy CDB note to the source-qualified contract."""
    if ticker != SYNTHETIC_CDB_TICKER:
        return

    expected_notes = row.get("notes")
    current_notes = transaction.notes
    if current_notes == expected_notes:
        return
    if (
        current_notes == LEGACY_SYNTHETIC_CDB_NOTES
        and expected_notes
        and "Benchmark Source: synthetic-certification" in expected_notes
    ):
        transaction.notes = expected_notes
        await db.commit()
        return

    raise SyntheticSeedContractError(
        "synthetic CDB note collision; persisted benchmark provenance is not canonical"
    )


async def _require_owned_asset(
    db: AsyncSession,
    *,
    ticker: str,
    asset_type: str,
    expected_name: str,
    expected_provider: str,
    expected_provider_symbol: str,
    expected_provider_status: str,
) -> Asset:
    result = await db.execute(
        select(Asset).where(
            Asset.ticker == ticker,
            Asset.asset_type == asset_type,
        )
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = Asset(
            ticker=ticker,
            name=expected_name,
            asset_type=asset_type,
            currency="BRL",
            provider=expected_provider,
            provider_symbol=expected_provider_symbol,
            provider_status=expected_provider_status,
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        return asset

    actual = (
        asset.name,
        asset.provider,
        asset.provider_symbol,
        asset.provider_status,
    )
    expected = (
        expected_name,
        expected_provider,
        expected_provider_symbol,
        expected_provider_status,
    )
    if actual != expected:
        raise SyntheticSeedContractError(
            f"synthetic asset collision for {ticker}; ownership is ambiguous"
        )
    return asset


async def _require_synthetic_crypto_membership(
    db: AsyncSession,
    *,
    asset: Asset,
) -> tuple[int, int]:
    result = await db.execute(
        select(AssetUniverseMembership).where(
            AssetUniverseMembership.asset_id == asset.id,
            AssetUniverseMembership.universe_key
            == CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        db.add(
            AssetUniverseMembership(
                asset_id=asset.id,
                universe_key=CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
                rank=None,
                source=CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE,
                refreshed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        return 1, 0

    if membership.source != CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE:
        raise SyntheticSeedContractError(
            f"synthetic crypto membership collision for {asset.ticker}; "
            "ownership is ambiguous"
        )
    return 0, 1


async def seed_transactions(
    db: AsyncSession,
    *,
    portfolio_id: int,
) -> SyntheticTransactionSeedResult:
    """Seed the complete synthetic transaction fixture through canonical writes."""
    fixture = load_portfolio_synthetic_certification_fixture()
    plan = build_synthetic_asset_plan(fixture)
    await _assert_existing_transactions_are_expected(
        db,
        portfolio_id=portfolio_id,
        fixture=fixture,
        plan=plan,
    )

    created = 0
    reused = 0
    membership_created = 0
    membership_reused = 0

    for row in fixture["transactions"]:
        identity = plan[row["ticker"]]
        asset = await _require_owned_asset(
            db,
            ticker=identity.ticker,
            asset_type=identity.asset_type,
            expected_name=identity.name,
            expected_provider=identity.provider,
            expected_provider_symbol=identity.provider_symbol,
            expected_provider_status=identity.provider_status,
        )

        if identity.asset_type == "CRIPTO":
            added, reused_membership = await _require_synthetic_crypto_membership(
                db,
                asset=asset,
            )
            membership_created += added
            membership_reused += reused_membership

        existing = await _find_existing_transaction(
            db,
            portfolio_id=portfolio_id,
            row=row,
            ticker=identity.ticker,
        )
        if existing is not None:
            await _reconcile_existing_certification_notes(
                db,
                transaction=existing,
                row=row,
                ticker=identity.ticker,
            )
            reused += 1
            continue

        await create_transaction_record(
            db,
            portfolio_id=portfolio_id,
            payload=TransactionCreate(
                ticker=identity.ticker,
                asset_type=identity.asset_type,
                operation=row["operation"],
                quantity=float(row["quantity"]),
                price=float(row["price"]),
                fees=float(row.get("fees", "0") or 0),
                date=date.fromisoformat(row["date"]),
                currency=row.get("currency", "BRL"),
                notes=row.get("notes"),
            ),
        )
        created += 1

    return SyntheticTransactionSeedResult(
        created=created,
        reused=reused,
        crypto_membership_created=membership_created,
        crypto_membership_reused=membership_reused,
    )
