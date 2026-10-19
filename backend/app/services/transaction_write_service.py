"""Canonical transaction write service shared by HTTP, CSV and certification callers."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.models.asset import Asset
from app.models.transaction import OperationType, Transaction
from app.schemas.fixed_income_contract import FixedIncomeContractCreate
from app.schemas.transaction import TransactionCreate
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
    require_catalog_crypto_asset,
)
from app.services.fixed_income_contract_service import (
    FixedIncomeContractNotFound,
    WRITE_FIXED_INCOME_CONTRACTS,
    create_fixed_income_contract,
    require_fixed_income_contract,
)
from app.services.treasury_catalog_service import resolve_treasury_symbol


class TransactionWriteError(ValueError):
    """Raised when a transaction violates canonical write rules."""


async def resolve_fixed_income_contract_for_write(
    db: AsyncSession,
    *,
    portfolio_id: int,
    asset_type: str,
    contract_id: int | None,
    contract_payload: FixedIncomeContractCreate | None,
) -> int | None:
    if contract_id is not None and contract_payload is not None:
        raise TransactionWriteError(
            "Informe um contrato existente ou novos metadados, nao ambos"
        )
    if (contract_id is not None or contract_payload is not None) and asset_type != "RENDA_FIXA":
        raise TransactionWriteError(
            "Contrato de Renda Fixa so pode ser associado a transacao RENDA_FIXA"
        )
    if contract_payload is not None:
        access = PortfolioAccessContext.for_system(
            portfolio_id=portfolio_id,
            permissions=frozenset({WRITE_FIXED_INCOME_CONTRACTS}),
            purpose="canonical_transaction_write",
        )
        contract = await create_fixed_income_contract(db, access, contract_payload)
        return contract.id
    if contract_id is not None:
        try:
            await require_fixed_income_contract(
                db,
                portfolio_id=portfolio_id,
                contract_id=contract_id,
            )
        except FixedIncomeContractNotFound as exc:
            raise TransactionWriteError(str(exc)) from exc
    return contract_id


async def _current_quantity(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_type: str,
) -> float:
    result = await db.execute(
        select(Transaction.operation, Transaction.quantity).where(
            Transaction.portfolio_id == portfolio_id,
            func.lower(Transaction.ticker) == ticker.lower(),
            Transaction.asset_type == asset_type,
        )
    )
    quantity = 0.0
    for operation, value in result.all():
        op = operation.value if isinstance(operation, OperationType) else str(operation)
        if op == OperationType.buy.value:
            quantity += float(value)
        elif op == OperationType.sell.value:
            quantity -= float(value)
    return max(quantity, 0.0)


async def _add_catalog_asset_if_missing(
    db: AsyncSession,
    *,
    ticker: str,
    asset_type: str,
    currency: str,
    flush: bool,
) -> None:
    result = await db.execute(
        select(Asset).where(
            Asset.ticker.ilike(ticker),
            Asset.asset_type == asset_type,
        )
    )
    if result.scalar_one_or_none() is not None:
        return

    db.add(
        Asset(
            ticker=ticker,
            name=ticker,
            asset_type=asset_type,
            currency=currency,
        )
    )
    if flush:
        await db.flush()


async def add_transaction_record(
    db: AsyncSession,
    *,
    portfolio_id: int,
    payload: TransactionCreate,
    flush: bool = False,
) -> Transaction:
    """Add one transaction using the canonical domain write path.

    This function deliberately does not commit, refresh, or schedule snapshots/cache
    invalidation; callers own transaction boundaries and post-commit orchestration.
    """
    ticker = payload.ticker.strip().upper()
    asset_type = payload.asset_type
    fixed_income_contract_id = payload.fixed_income_contract_id
    if payload.fixed_income_contract is not None and fixed_income_contract_id is not None:
        raise TransactionWriteError(
            "Informe um contrato existente ou novos metadados, nao ambos"
        )
    if (payload.fixed_income_contract is not None or fixed_income_contract_id is not None) and asset_type != "RENDA_FIXA":
        raise TransactionWriteError(
            "Contrato de Renda Fixa so pode ser associado a transacao RENDA_FIXA"
        )
    if fixed_income_contract_id is not None:
        fixed_income_contract_id = await resolve_fixed_income_contract_for_write(
            db,
            portfolio_id=portfolio_id,
            asset_type=asset_type,
            contract_id=fixed_income_contract_id,
            contract_payload=None,
        )
    if asset_type == "TESOURO_DIRETO":
        canonical_ticker = await resolve_treasury_symbol(db, payload.ticker)
        if canonical_ticker:
            ticker = canonical_ticker.strip().upper()
    try:
        operation = OperationType(payload.operation)
    except ValueError as exc:
        raise TransactionWriteError(
            f"operation invalida: '{payload.operation}'. Use 'buy' ou 'sell'."
        ) from exc

    if asset_type == "CRIPTO":
        try:
            await require_catalog_crypto_asset(db, ticker)
        except CryptoTransactionEligibilityError as exc:
            raise TransactionWriteError(str(exc)) from exc

    if operation == OperationType.sell:
        current_qty = await _current_quantity(db, portfolio_id, ticker, asset_type)
        if payload.quantity > current_qty:
            raise TransactionWriteError(
                f"Quantidade insuficiente para venda de {ticker}. "
                f"Posicao atual: {current_qty:.4f} | Tentativa: {payload.quantity:.4f}"
            )

    if payload.fixed_income_contract is not None:
        fixed_income_contract_id = await resolve_fixed_income_contract_for_write(
            db,
            portfolio_id=portfolio_id,
            asset_type=asset_type,
            contract_id=None,
            contract_payload=payload.fixed_income_contract,
        )

    currency = payload.currency or "BRL"
    if asset_type != "CRIPTO":
        await _add_catalog_asset_if_missing(
            db,
            ticker=ticker,
            asset_type=asset_type,
            currency=currency,
            flush=flush,
        )

    transaction = Transaction(
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=asset_type,
        operation=operation,
        quantity=payload.quantity,
        price=payload.price,
        fees=payload.fees or 0.0,
        date=payload.date,
        currency=currency,
        notes=payload.notes,
        fixed_income_contract_id=fixed_income_contract_id,
    )
    db.add(transaction)

    if flush:
        await db.flush()

    return transaction


async def create_transaction_record(
    db: AsyncSession,
    *,
    portfolio_id: int,
    payload: TransactionCreate,
) -> Transaction:
    """Persist one transaction using the canonical domain write path.

    This function deliberately does not schedule snapshots/cache invalidation;
    callers own post-commit orchestration appropriate to their surface.
    """
    transaction = await add_transaction_record(
        db,
        portfolio_id=portfolio_id,
        payload=payload,
    )
    await db.commit()
    await db.refresh(transaction)
    return transaction
