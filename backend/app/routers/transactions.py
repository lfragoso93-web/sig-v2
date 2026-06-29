from datetime import date as DateType
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.models.fixed_income import FixedIncomeInvestment, IndexerType, FixedIncomeType
from app.schemas.transaction import TransactionCreate, TransactionOut, PagedTransactions
from app.schemas.asset import AssetCreate
from app.services.asset_service import get_or_create_asset
from app.services.dividend_backfill_service import backfill_dividends
from app.services.asset_onboarding_service import run_onboarding
from app.services.transaction_service import list_transactions_paginated

router = APIRouter()

# Mapeamento dos valores enviados pelo modal -> IndexerType do modelo
_INDEXER_MAP: dict[str, IndexerType] = {
    "CDI":       IndexerType.CDI,
    "IPCA":      IndexerType.IPCA_PLUS,
    "IPCA+":     IndexerType.IPCA_PLUS,
    "SELIC":     IndexerType.SELIC,
    "Prefixado": IndexerType.PREFIXADO,
    "IGP-M":     IndexerType.IGPM_PLUS,
    "Outro":     IndexerType.CDI,  # fallback conservador
}


def _parse_indexer(value: Optional[str]) -> Optional[IndexerType]:
    """Converte string do modal para IndexerType. Retorna None se não reconhecido."""
    if not value:
        return None
    return _INDEXER_MAP.get(value.strip())


def _parse_rf_meta_from_notes(notes: Optional[str]) -> dict:
    """
    Extrai metadados RF do campo notes enriquecido pelo modal.
    Formato esperado: "Nome - Indexador: CDI | 110% do CDI | Vencimento: 2027-12-01 | Emissor: Banco XP"
    Retorna dict com: indexer_str, rate, maturity, issuer, daily_liquidity.
    """
    import re
    result = {
        "indexer_str": None,
        "rate": 0.0,
        "maturity": None,
        "issuer": "",
        "daily_liquidity": False,
    }
    if not notes:
        return result

    m = re.search(r"Indexador:\s*([^|\-]+)", notes)
    if m:
        result["indexer_str"] = m.group(1).strip()

    # % do indexador (ex: "110% do CDI")
    m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*%\s*do\s+", notes, re.IGNORECASE)
    if m:
        result["rate"] = float(m.group(1).replace(",", "."))

    # Taxa a.a. (ex: "Taxa: 5.82% a.a.")
    m = re.search(r"Taxa:\s*([0-9]+(?:[.,][0-9]+)?)\s*%", notes, re.IGNORECASE)
    if m:
        result["rate"] = float(m.group(1).replace(",", "."))

    m = re.search(r"Vencimento:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", notes)
    if m:
        from datetime import date
        result["maturity"] = date.fromisoformat(m.group(1))

    m = re.search(r"Emissor:\s*([^|\-]+)", notes)
    if m:
        result["issuer"] = m.group(1).strip()

    if re.search(r"Liquidez:\s*Di", notes, re.IGNORECASE):
        result["daily_liquidity"] = True
        result["maturity"] = None

    return result


async def _upsert_fixed_income(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    tx_date: DateType,
    invested_amount: float,
    notes: Optional[str],
) -> None:
    """
    Cria ou atualiza o registro em fixed_income_investments para o ticker RF.
    Usa o ticker como chave de lookup dentro da carteira.
    """
    meta = _parse_rf_meta_from_notes(notes)
    indexer = _parse_indexer(meta["indexer_str"])
    if indexer is None:
        # Sem indexador reconhecível — não persiste para não corromper dados
        return

    result = await db.execute(
        select(FixedIncomeInvestment).where(
            FixedIncomeInvestment.portfolio_id == portfolio_id,
            FixedIncomeInvestment.name == ticker,
        )
    )
    fi = result.scalar_one_or_none()

    if fi is None:
        fi = FixedIncomeInvestment(
            portfolio_id=portfolio_id,
            name=ticker,
            institution=meta["issuer"] or "",
            fixed_income_type=FixedIncomeType.OUTROS,
            indexer=indexer,
            rate=Decimal(str(meta["rate"])),
            invested_amount=Decimal(str(invested_amount)),
            date_start=tx_date,
            daily_liquidity=meta["daily_liquidity"],
            date_maturity=meta["maturity"],
            is_active=True,
        )
        db.add(fi)
    else:
        fi.indexer = indexer
        fi.rate = Decimal(str(meta["rate"]))
        fi.invested_amount = Decimal(str(invested_amount))
        fi.daily_liquidity = meta["daily_liquidity"]
        fi.date_maturity = meta["maturity"]
        if meta["issuer"]:
            fi.institution = meta["issuer"]


def _to_operation(value: str) -> OperationType:
    try:
        return OperationType(value)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"operation inválida: '{value}'. Use 'buy' ou 'sell'.",
        )


async def _get_portfolio(portfolio_id: int, user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Carteira não encontrada.")
    return p


async def _calc_current_quantity(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    exclude_tx_id: int | None = None,
) -> float:
    stmt = select(Transaction.operation, Transaction.quantity).where(
        Transaction.portfolio_id == portfolio_id,
        Transaction.ticker == ticker,
    )
    if exclude_tx_id is not None:
        stmt = stmt.where(Transaction.id != exclude_tx_id)

    result = await db.execute(stmt)
    rows = result.all()

    qty = 0.0
    for op, q in rows:
        op_val = op.value if isinstance(op, OperationType) else str(op)
        if op_val == "buy":
            qty += float(q)
        elif op_val == "sell":
            qty -= float(q)
    return max(qty, 0.0)


async def _validate_sell(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    quantity: float,
    exclude_tx_id: int | None = None,
) -> None:
    current_qty = await _calc_current_quantity(db, portfolio_id, ticker, exclude_tx_id)
    if quantity > current_qty:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Quantidade insuficiente para venda de {ticker}. "
                f"Posição atual: {current_qty:.4f} | Tentativa: {quantity:.4f}"
            ),
        )


@router.get("/{portfolio_id}/transactions", response_model=PagedTransactions)
async def list_transactions(
    portfolio_id: int,
    page: int = Query(1, ge=1, description="Número da página (inicia em 1)"),
    page_size: int = Query(50, ge=1, le=200, description="Itens por página (máx 200)"),
    ticker: Optional[str] = Query(None, description="Filtrar por ticker (ex: PETR4)"),
    operation: Optional[str] = Query(None, description="Filtrar por operação: buy | sell"),
    date_from: Optional[DateType] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    date_to: Optional[DateType] = Query(None, description="Data final (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista transações da carteira com paginação e filtros opcionais.
    Retorna envelope: { items, total, page, page_size, pages }
    """
    await _get_portfolio(portfolio_id, current_user, db)

    if operation and operation.lower() not in {"buy", "sell"}:
        raise HTTPException(
            status_code=422,
            detail=f"operation inválida: '{operation}'. Use 'buy' ou 'sell'.",
        )

    return await list_transactions_paginated(
        db=db,
        portfolio_id=portfolio_id,
        page=page,
        page_size=page_size,
        ticker=ticker,
        operation=operation,
        date_from=date_from,
        date_to=date_to,
    )


@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    portfolio_id: int,
    payload: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)

    ticker = payload.ticker.strip().upper()
    asset_type = payload.asset_type
    operation = _to_operation(payload.operation)

    if operation == OperationType.sell:
        await _validate_sell(db, portfolio_id, ticker, payload.quantity)

    tx = Transaction(
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=asset_type,
        operation=operation,
        quantity=payload.quantity,
        price=payload.price,
        fees=payload.fees or 0.0,
        date=payload.date,
        currency=payload.currency or "BRL",
        notes=payload.notes,
    )
    db.add(tx)

    # Para RENDA_FIXA: persiste dados estruturados em fixed_income_investments
    if str(asset_type).upper() == "RENDA_FIXA" and operation == OperationType.buy:
        # price = valor investido (qty=1 por convenção do modal)
        invested = payload.quantity * payload.price
        await _upsert_fixed_income(
            db, portfolio_id, ticker, payload.date, invested, payload.notes
        )

    await db.commit()
    await db.refresh(tx)

    asset_data = AssetCreate(
        ticker=ticker,
        name=ticker,
        asset_type=asset_type,
    )
    await get_or_create_asset(db, asset_data)

    background_tasks.add_task(run_onboarding, ticker, str(asset_type))
    background_tasks.add_task(
        _run_backfill,
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=str(asset_type),
    )
    background_tasks.add_task(
        _run_snapshot_backfill,
        portfolio_id=portfolio_id,
        tx_date=payload.date,
    )

    return tx


@router.patch(
    "/{portfolio_id}/transactions/{transaction_id}",
    response_model=TransactionOut,
)
async def update_transaction(
    portfolio_id: int,
    transaction_id: int,
    payload: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.portfolio_id == portfolio_id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada.")

    ticker = payload.ticker.strip().upper()
    asset_type = payload.asset_type
    operation = _to_operation(payload.operation)

    if operation == OperationType.sell:
        await _validate_sell(db, portfolio_id, ticker, payload.quantity, exclude_tx_id=transaction_id)

    invalidate_from = min(tx.date, payload.date)

    tx.ticker = ticker
    tx.asset_type = asset_type
    tx.operation = operation
    tx.quantity = payload.quantity
    tx.price = payload.price
    tx.fees = payload.fees or 0.0
    tx.date = payload.date
    tx.currency = payload.currency or "BRL"
    tx.notes = payload.notes

    # Para RENDA_FIXA: atualiza fixed_income_investments
    if str(asset_type).upper() == "RENDA_FIXA" and operation == OperationType.buy:
        invested = payload.quantity * payload.price
        await _upsert_fixed_income(
            db, portfolio_id, ticker, payload.date, invested, payload.notes
        )

    await db.commit()
    await db.refresh(tx)

    background_tasks.add_task(run_onboarding, ticker, str(asset_type))
    background_tasks.add_task(
        _run_backfill,
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=str(asset_type),
    )
    background_tasks.add_task(
        _run_snapshot_backfill,
        portfolio_id=portfolio_id,
        tx_date=invalidate_from,
    )

    return tx


@router.delete(
    "/{portfolio_id}/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.portfolio_id == portfolio_id,
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada.")

    ticker = tx.ticker
    asset_type = tx.asset_type
    tx_date = tx.date

    await db.delete(tx)
    await db.commit()

    background_tasks.add_task(
        _run_backfill,
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=str(asset_type),
    )
    background_tasks.add_task(
        _run_snapshot_backfill,
        portfolio_id=portfolio_id,
        tx_date=tx_date,
    )


async def _run_backfill(portfolio_id: int, ticker: str, asset_type: str) -> None:
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await backfill_dividends(
                db=db,
                portfolio_id=portfolio_id,
                ticker=ticker,
                asset_type=asset_type,
            )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "[backfill_dividends] erro para %s/%s: %s", ticker, portfolio_id, exc
        )


async def _run_snapshot_backfill(portfolio_id: int, tx_date: DateType) -> None:
    """
    1. Invalida todos os snapshots >= tx_date (remove do banco).
    2. Roda backfill_snapshots para recalcular as datas removidas.
    """
    import logging
    log = logging.getLogger(__name__)
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.portfolio_snapshot_service import (
            invalidate_snapshots_from,
            backfill_snapshots,
        )
        async with AsyncSessionLocal() as db:
            deleted = await invalidate_snapshots_from(db, portfolio_id, tx_date)
            log.info(
                "[snapshot_backfill] portfolio=%s invalida a partir de %s (%s removidos)",
                portfolio_id, tx_date, deleted,
            )
            count = await backfill_snapshots(db=db, portfolio_id=portfolio_id)
            log.info(
                "[snapshot_backfill] portfolio=%s — %s snapshots recalculados",
                portfolio_id, count,
            )
    except Exception as exc:
        log.error(
            "[snapshot_backfill] erro para portfolio %s: %s", portfolio_id, exc
        )
