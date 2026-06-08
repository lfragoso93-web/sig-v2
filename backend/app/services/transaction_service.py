from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.transaction import Transaction, TransactionType
from app.models.portfolio_position import PortfolioPosition
from app.models.asset import Asset
from app.schemas.transaction import TransactionCreate
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


async def _get_or_create_position(
    db: AsyncSession, portfolio_id: int, asset_id: int
) -> PortfolioPosition:
    result = await db.execute(
        select(PortfolioPosition).where(
            PortfolioPosition.portfolio_id == portfolio_id,
            PortfolioPosition.asset_id == asset_id,
        )
    )
    position = result.scalar_one_or_none()
    if not position:
        position = PortfolioPosition(
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            quantity=Decimal("0"),
            average_price=Decimal("0"),
            total_invested=Decimal("0"),
            realized_profit=Decimal("0"),
        )
        db.add(position)
        await db.flush()
    return position


def _recalculate_average_price(
    current_qty: Decimal,
    current_avg: Decimal,
    new_qty: Decimal,
    new_price: Decimal,
    fees: Decimal,
) -> Decimal:
    """
    Preço médio ponderado (PM):
      PM = (qtd_atual * pm_atual + qtd_nova * preco_unit + taxas) / (qtd_atual + qtd_nova)
    """
    total_cost = (current_qty * current_avg) + (new_qty * new_price) + fees
    total_qty = current_qty + new_qty
    if total_qty == 0:
        return Decimal("0")
    return (total_cost / total_qty).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


async def create_transaction(
    db: AsyncSession,
    portfolio_id: int,
    data: TransactionCreate,
) -> Transaction:
    # Verifica se o ativo existe
    asset_result = await db.execute(select(Asset).where(Asset.id == data.asset_id))
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    total_cost = (data.quantity * data.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    transaction = Transaction(
        portfolio_id=portfolio_id,
        asset_id=data.asset_id,
        transaction_type=data.transaction_type,
        date=data.date,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total_cost=total_cost,
        fees=data.fees,
        broker=data.broker,
        notes=data.notes,
        is_day_trade=data.is_day_trade,
    )
    db.add(transaction)

    # Atualiza posição
    position = await _get_or_create_position(db, portfolio_id, data.asset_id)
    tt = data.transaction_type

    if tt == TransactionType.COMPRA:
        position.average_price = _recalculate_average_price(
            position.quantity, position.average_price,
            data.quantity, data.unit_price, data.fees
        )
        position.quantity += data.quantity
        position.total_invested += total_cost + data.fees

    elif tt == TransactionType.VENDA:
        if position.quantity < data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quantidade insuficiente. Posição atual: {position.quantity}",
            )
        # Lucro/perda realizado na venda
        sale_value = data.quantity * data.unit_price - data.fees
        cost_basis = data.quantity * position.average_price
        profit = sale_value - cost_basis
        position.realized_profit += profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        position.quantity -= data.quantity
        position.total_invested -= (data.quantity * position.average_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if position.quantity == 0:
            position.average_price = Decimal("0")
            position.total_invested = Decimal("0")

    elif tt == TransactionType.DESDOBRAMENTO:
        # Split: multiplica quantidade, divide preço médio pelo ratio
        # unit_price aqui é o ratio (ex: 2 para desdobramento 1:2)
        ratio = data.unit_price
        position.quantity *= ratio
        if ratio > 0:
            position.average_price = (position.average_price / ratio).quantize(
                Decimal("0.00000001"), rounding=ROUND_HALF_UP
            )

    elif tt == TransactionType.GRUPAMENTO:
        # Inplit: divide quantidade, multiplica preço médio pelo ratio
        ratio = data.unit_price
        if ratio > 0:
            position.quantity = (position.quantity / ratio).quantize(
                Decimal("0.00000001"), rounding=ROUND_HALF_UP
            )
            position.average_price = (position.average_price * ratio).quantize(
                Decimal("0.00000001"), rounding=ROUND_HALF_UP
            )

    elif tt == TransactionType.BONIFICACAO:
        # Bonificação: novas ações sem custo, recalcula preço médio
        position.average_price = _recalculate_average_price(
            position.quantity, position.average_price,
            data.quantity, Decimal("0"), Decimal("0")
        )
        position.quantity += data.quantity

    elif tt in (TransactionType.TRANSFERENCIA_ENTRADA,):
        position.average_price = _recalculate_average_price(
            position.quantity, position.average_price,
            data.quantity, data.unit_price, data.fees
        )
        position.quantity += data.quantity
        position.total_invested += total_cost

    elif tt == TransactionType.TRANSFERENCIA_SAIDA:
        position.quantity -= data.quantity
        position.total_invested -= (data.quantity * position.average_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    await db.flush()
    await db.refresh(transaction)
    return transaction


async def list_transactions(
    db: AsyncSession,
    portfolio_id: int,
    asset_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Transaction], int]:
    from sqlalchemy import func
    stmt = select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    count_stmt = select(func.count()).select_from(Transaction).where(
        Transaction.portfolio_id == portfolio_id
    )
    if asset_id:
        stmt = stmt.where(Transaction.asset_id == asset_id)
        count_stmt = count_stmt.where(Transaction.asset_id == asset_id)
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Transaction.date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def delete_transaction(
    db: AsyncSession, transaction_id: int, portfolio_id: int
) -> None:
    """
    Remove uma transação e recalcula a posição do ativo do zero.
    """
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.portfolio_id == portfolio_id,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    asset_id = transaction.asset_id
    await db.delete(transaction)
    await db.flush()

    # Recalcula posição do zero para o ativo
    await _rebuild_position(db, portfolio_id, asset_id)


async def _rebuild_position(
    db: AsyncSession, portfolio_id: int, asset_id: int
) -> None:
    """Reconstrói a posição de um ativo relendo todas as suas transações em ordem cronológica."""
    # Zera a posição atual
    result = await db.execute(
        select(PortfolioPosition).where(
            PortfolioPosition.portfolio_id == portfolio_id,
            PortfolioPosition.asset_id == asset_id,
        )
    )
    position = result.scalar_one_or_none()
    if not position:
        return

    position.quantity = Decimal("0")
    position.average_price = Decimal("0")
    position.total_invested = Decimal("0")
    position.realized_profit = Decimal("0")

    # Relê todas as transações em ordem
    txs_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_id == asset_id,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = txs_result.scalars().all()

    for tx in transactions:
        tt = tx.transaction_type
        if tt == TransactionType.COMPRA:
            position.average_price = _recalculate_average_price(
                position.quantity, position.average_price, tx.quantity, tx.unit_price, tx.fees
            )
            position.quantity += tx.quantity
            position.total_invested += tx.total_cost + tx.fees
        elif tt == TransactionType.VENDA:
            sale_value = tx.quantity * tx.unit_price - tx.fees
            cost_basis = tx.quantity * position.average_price
            position.realized_profit += (sale_value - cost_basis).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            position.quantity -= tx.quantity
            position.total_invested -= (tx.quantity * position.average_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if position.quantity <= 0:
                position.quantity = Decimal("0")
                position.average_price = Decimal("0")
                position.total_invested = Decimal("0")
        elif tt == TransactionType.DESDOBRAMENTO:
            ratio = tx.unit_price
            position.quantity *= ratio
            if ratio > 0:
                position.average_price = (position.average_price / ratio).quantize(
                    Decimal("0.00000001"), rounding=ROUND_HALF_UP
                )
        elif tt == TransactionType.GRUPAMENTO:
            ratio = tx.unit_price
            if ratio > 0:
                position.quantity = (position.quantity / ratio).quantize(
                    Decimal("0.00000001"), rounding=ROUND_HALF_UP
                )
                position.average_price = (position.average_price * ratio).quantize(
                    Decimal("0.00000001"), rounding=ROUND_HALF_UP
                )
        elif tt == TransactionType.BONIFICACAO:
            position.average_price = _recalculate_average_price(
                position.quantity, position.average_price, tx.quantity, Decimal("0"), Decimal("0")
            )
            position.quantity += tx.quantity

    await db.flush()
