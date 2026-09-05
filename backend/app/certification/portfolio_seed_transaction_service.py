"""Idempotent synthetic transaction seeding for certification issue #303."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_asset_policy import build_synthetic_asset_plan
from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.models.asset import Asset
from app.models.transaction import OperationType, Transaction
from app.schemas.transaction import TransactionCreate
from app.services.transaction_write_service import create_transaction_record


@dataclass(frozen=True)
class SyntheticTransactionSeedResult:
    created: int
    reused: int
    blocked_crypto: int


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


async def seed_non_crypto_transactions(
    db: AsyncSession,
    *,
    portfolio_id: int,
) -> SyntheticTransactionSeedResult:
    """Seed every non-CRIPTO fixture transaction using the canonical write service.

    CRIPTO remains explicitly blocked by issue #317 until a synthetic eligibility
    contract can satisfy the canonical lifecycle without falsifying provider state.
    """
    fixture = load_portfolio_synthetic_certification_fixture()
    plan = build_synthetic_asset_plan(fixture)

    created = 0
    reused = 0
    blocked_crypto = 0

    for row in fixture["transactions"]:
        identity = plan[row["ticker"]]
        if identity.asset_type == "CRIPTO":
            blocked_crypto += 1
            continue

        await _require_owned_asset(
            db,
            ticker=identity.ticker,
            asset_type=identity.asset_type,
            expected_name=identity.name,
            expected_provider=identity.provider,
            expected_provider_symbol=identity.provider_symbol,
            expected_provider_status=identity.provider_status,
        )

        existing = await _find_existing_transaction(
            db,
            portfolio_id=portfolio_id,
            row=row,
            ticker=identity.ticker,
        )
        if existing is not None:
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
        blocked_crypto=blocked_crypto,
    )
