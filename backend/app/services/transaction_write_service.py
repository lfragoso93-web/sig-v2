"""Canonical transaction write service shared by HTTP, CSV and certification callers."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.models.asset import Asset
from app.models.asset_alias import AssetAlias
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
    as_of_date: date | None = None,
    exclude_tx_id: int | None = None,
) -> float:
    stmt = select(
        Transaction.operation,
        Transaction.quantity,
        Transaction.date,
    ).where(
        Transaction.portfolio_id == portfolio_id,
        func.lower(Transaction.ticker) == ticker.lower(),
        Transaction.asset_type == asset_type,
    )
    if exclude_tx_id is not None:
        stmt = stmt.where(Transaction.id != exclude_tx_id)
    if as_of_date is not None:
        stmt = stmt.where(Transaction.date <= as_of_date)
    stmt = stmt.order_by(Transaction.date.asc(), Transaction.id.asc())

    result = await db.execute(stmt)
    rows = result.all()
    if not rows:
        return 0.0

    actions = ()
    if asset_type in {"ACAO", "FII", "BDR", "ETF"}:
        try:
            from app.services.corporate_action_position_reader import (
                load_global_corporate_actions_by_ticker,
            )
            actions_by_ticker = await load_global_corporate_actions_by_ticker(
                db,
                [ticker.strip().upper()],
            )
            actions = actions_by_ticker.get(ticker.strip().upper(), ())
        except Exception:
            actions = ()

    if actions:
        from decimal import Decimal
        from app.services.position_timeline_projection import (
            PositionMovement,
            PositionMovementKind,
            project_position_timeline,
        )
        movements: list[PositionMovement] = []
        for row in rows:
            op_raw = row[0]
            op_val = op_raw.value if isinstance(op_raw, OperationType) else str(op_raw).lower()
            qty = Decimal(str(row[1]))
            tx_date = row[2] if len(row) > 2 and isinstance(row[2], date) else (as_of_date or date.min)
            kind = PositionMovementKind.BUY if op_val == OperationType.buy.value else PositionMovementKind.SELL
            movements.append(
                PositionMovement(
                    movement_date=tx_date,
                    kind=kind,
                    quantity=qty,
                    unit_price=Decimal('0'),
                )
            )
        timeline = project_position_timeline(
            movements=movements,
            actions=actions,
            through_date=as_of_date,
        )
        return max(float(timeline.quantity), 0.0)

    quantity = 0.0
    for row in rows:
        op_raw = row[0]
        op = op_raw.value if isinstance(op_raw, OperationType) else str(op_raw)
        val = float(row[1])
        if op == OperationType.buy.value:
            quantity += val
        elif op == OperationType.sell.value:
            quantity -= val
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

    from app.services.asset_provider_verification_service import verify_market_asset_exists
    exists, official_name = await verify_market_asset_exists(ticker, asset_type)
    if not exists:
        raise TransactionWriteError(
            f"Ativo '{ticker}' ({asset_type}) não existe no catálogo e não foi encontrado nos provedores de mercado."
        )

    db.add(
        Asset(
            ticker=ticker,
            name=official_name or ticker,
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
    else:
        alias_stmt = (
            select(Asset.ticker)
            .join(AssetAlias, AssetAlias.asset_id == Asset.id)
            .where(
                func.upper(AssetAlias.alias_ticker) == ticker,
                AssetAlias.asset_type == asset_type,
            )
        )
        alias_result = await db.execute(alias_stmt)
        resolved_alias = alias_result.scalar_one_or_none()
        if isinstance(resolved_alias, str) and resolved_alias.strip():
            ticker = resolved_alias.strip().upper()
    try:
        operation = OperationType(payload.operation)
    except ValueError as exc:
        raise TransactionWriteError(
            f"operation invalida: '{payload.operation}'. Use 'buy' ou 'sell'."
        ) from exc

    currency = payload.currency or "BRL"
    if asset_type == "CRIPTO":
        try:
            crypto_asset = await require_catalog_crypto_asset(db, ticker)
            ticker = crypto_asset.ticker.upper()
        except CryptoTransactionEligibilityError:
            from app.services.asset_provider_verification_service import verify_market_asset_exists
            from app.services.crypto_transaction_eligibility_service import _CRYPTO_NAME_TO_TICKER
            resolved_ticker = _CRYPTO_NAME_TO_TICKER.get(ticker, ticker)
            exists, official_name = await verify_market_asset_exists(resolved_ticker, "CRIPTO")
            if not exists:
                raise TransactionWriteError(
                    f"Criptomoeda '{ticker}' não existe no catálogo e não foi encontrada nos provedores de mercado."
                )
            ticker = resolved_ticker
            db.add(
                Asset(
                    ticker=ticker,
                    name=official_name or ticker,
                    asset_type="CRIPTO",
                    currency=currency,
                )
            )
            if flush:
                await db.flush()

    if operation == OperationType.sell:
        current_qty = await _current_quantity(
            db,
            portfolio_id,
            ticker,
            asset_type,
            as_of_date=payload.date,
        )
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
