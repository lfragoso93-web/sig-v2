"""Leitura canônica de Bens e Direitos do IRPF em uma data de corte."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.schemas.irpf import BemDireito
from app.services.historical_position_projection_reader import (
    load_open_positions_as_of,
)
from app.services.portfolio_service import normalize_type

_RENDA_FIXA_TYPE = "RENDA_FIXA"

_CODIGO_IRPF: dict[str, tuple[str, str]] = {
    "ACAO": ("31", "03 - Participacoes Societarias"),
    "FII": ("73", "07 - Fundos"),
    "ETF": ("74", "07 - Fundos"),
    "ETF_INTERNACIONAL": ("74", "07 - Fundos"),
    "STOCK": ("31", "03 - Participacoes Societarias"),
    "BDR": ("35", "03 - Participacoes Societarias"),
    "CRIPTO": ("08", "08 - Criptoativos"),
    "TESOURO_DIRETO": ("45", "04 - Aplicacoes e Investimentos"),
    "RENDA_FIXA": ("45", "04 - Aplicacoes e Investimentos"),
}


def _codigo_irpf(asset_type: str) -> tuple[str, str]:
    return _CODIGO_IRPF.get(asset_type.upper(), ("99", "09 - Outros"))


async def _load_fixed_income_bens(
    db: AsyncSession,
    portfolio_id: int,
    cutoff: date,
) -> list[BemDireito]:
    """Preserva temporariamente o contrato legado de Renda Fixa.

    Renda Fixa não pertence ao projetor genérico de posições. Esta adaptação
    permanece isolada até o leitor histórico dedicado da classe ser composto.
    """

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= cutoff,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    positions: dict[str, tuple[float, float, str]] = {}
    for tx in result.scalars().all():
        if normalize_type(tx.asset_type) != _RENDA_FIXA_TYPE:
            continue
        ticker = str(tx.ticker).strip().upper()
        quantity, total_cost, currency = positions.get(ticker, (0.0, 0.0, "BRL"))
        tx_quantity = float(tx.quantity or 0)
        tx_price = float(tx.price or 0)
        tx_fees = float(tx.fees or 0)
        if tx.operation == OperationType.buy:
            quantity += tx_quantity
            total_cost += tx_quantity * tx_price + tx_fees
        elif tx.operation == OperationType.sell and quantity > 0:
            sold = min(tx_quantity, quantity)
            average_price = total_cost / quantity
            quantity -= sold
            total_cost = quantity * average_price
        positions[ticker] = (
            quantity,
            total_cost,
            str(getattr(tx, "currency", "BRL") or currency),
        )

    codigo, grupo = _codigo_irpf(_RENDA_FIXA_TYPE)
    return [
        BemDireito(
            ticker=ticker,
            nome=ticker,
            asset_type=_RENDA_FIXA_TYPE,
            codigo_irpf=codigo,
            grupo_irpf=grupo,
            quantidade=round(quantity, 6),
            custo_medio=round(total_cost / quantity, 2),
            custo_total=round(total_cost, 2),
            moeda=currency,
        )
        for ticker, (quantity, total_cost, currency) in positions.items()
        if quantity > 0
    ]


async def calc_bens_direitos(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> list[BemDireito]:
    """Projeta posições abertas em 31/12 usando leitores canônicos."""

    cutoff = date(year, 12, 31)
    projected = await load_open_positions_as_of(db, portfolio_id, cutoff)
    bens: list[BemDireito] = []
    for ticker, (position, asset_type, is_usd) in projected.items():
        codigo, grupo = _codigo_irpf(asset_type)
        bens.append(
            BemDireito(
                ticker=ticker,
                nome=ticker,
                asset_type=asset_type,
                codigo_irpf=codigo,
                grupo_irpf=grupo,
                quantidade=round(float(position.quantity), 6),
                custo_medio=round(float(position.average_price), 2),
                custo_total=round(float(position.total_cost), 2),
                moeda="USD" if is_usd else "BRL",
            )
        )

    bens.extend(await _load_fixed_income_bens(db, portfolio_id, cutoff))
    return sorted(bens, key=lambda item: (item.grupo_irpf, item.ticker))
