"""Regras fiscais mensais e rendimentos do IRPF.

Este módulo não projeta Bens e Direitos. Posição e custo em 31/12 pertencem ao
serviço canônico ``irpf_bens_direitos_service``.
"""

import logging
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.schemas.irpf import (
    GanhoCapitalMensal,
    JCPItem,
    RendimentoIsento,
    VendaMensal,
)
from app.services.canonical_dividend_entitlement import EntitlementReason
from app.services.canonical_dividend_entitlement_reader import (
    load_portfolio_dividend_entitlements,
)

logger = logging.getLogger(__name__)

ALIQ_SWING = 0.15
ALIQ_DAY_TRADE = 0.20
ISENCAO_ACOES_MENSAL = 20_000.0

_ACAO_TYPES = {"ACAO", "STOCK", "BDR"}
_INTL_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


def _detect_day_trades(txs: list) -> set[tuple[date, str]]:
    """Retorna pares ``(data, ticker)`` com compra e venda no mesmo dia."""

    by_day: dict[tuple[date, str], set[str]] = defaultdict(set)
    for tx in txs:
        operation = (
            tx.operation.value
            if isinstance(tx.operation, OperationType)
            else str(tx.operation)
        )
        by_day[(tx.date, tx.ticker)].add(operation)
    return {
        key
        for key, operations in by_day.items()
        if "buy" in operations and "sell" in operations
    }


async def _get_usd_brl_rate(tx_date: date) -> float:
    """Obtém USD/BRL na data da transação, preservando o fallback vigente."""

    try:
        from app.models.asset import AssetType
        from app.services.price_history_service import get_price_at_date

        rate = await get_price_at_date(
            None,
            "USDBRL=X",
            AssetType.ETF_INTERNACIONAL,
            str(tx_date),
        )
        if rate and rate > 0:
            return rate
    except Exception as exc:  # noqa: BLE001 - fallback fiscal legado preservado
        logger.warning("[IRPF] falha ao buscar USD/BRL em %s: %s", tx_date, exc)
    logger.warning("[IRPF] usando taxa USD/BRL=1.0 para %s", tx_date)
    return 1.0


async def calc_ganhos_capital(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> list[GanhoCapitalMensal]:
    """Calcula ganhos e perdas mensais preservando as regras fiscais vigentes."""

    start = date(year, 1, 1)
    end = date(year, 12, 31)

    all_tx_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .order_by(Transaction.date.asc())
    )
    all_txs = all_tx_result.scalars().all()
    day_trade_keys = _detect_day_trades(all_txs)

    previous_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date < start,
        )
        .order_by(Transaction.date.asc())
    )
    previous_txs = previous_result.scalars().all()

    average_costs: dict[str, dict] = {}
    for tx in previous_txs:
        ticker = tx.ticker
        operation = (
            tx.operation.value
            if isinstance(tx.operation, OperationType)
            else str(tx.operation)
        )
        asset_type = (tx.asset_type or "").upper()
        currency = getattr(tx, "currency", "BRL") or "BRL"
        price_brl = tx.price
        if currency != "BRL" and asset_type in _INTL_TYPES:
            price_brl = tx.price * await _get_usd_brl_rate(tx.date)
        fees = getattr(tx, "fees", 0.0) or 0.0
        cost = price_brl * tx.quantity + fees
        position = average_costs.setdefault(
            ticker,
            {"qty": 0.0, "cost": 0.0, "asset_type": asset_type},
        )
        if operation == "buy":
            position["qty"] += tx.quantity
            position["cost"] += cost
        elif operation == "sell" and position["qty"] > 0:
            average = position["cost"] / position["qty"]
            position["qty"] = max(0.0, position["qty"] - tx.quantity)
            position["cost"] = position["qty"] * average

    sales_by_month: dict[str, list] = defaultdict(list)
    for tx in all_txs:
        ticker = tx.ticker
        asset_type = (tx.asset_type or "").upper()
        operation = (
            tx.operation.value
            if isinstance(tx.operation, OperationType)
            else str(tx.operation)
        )
        currency = getattr(tx, "currency", "BRL") or "BRL"
        price_brl = tx.price
        if currency != "BRL" and asset_type in _INTL_TYPES:
            price_brl = tx.price * await _get_usd_brl_rate(tx.date)
        fees = getattr(tx, "fees", 0.0) or 0.0
        cost = price_brl * tx.quantity + fees

        position = average_costs.setdefault(
            ticker,
            {"qty": 0.0, "cost": 0.0, "asset_type": asset_type},
        )
        if operation == "buy":
            position["qty"] += tx.quantity
            position["cost"] += cost
        elif operation == "sell" and position["qty"] > 0:
            average = position["cost"] / position["qty"]
            acquisition_cost = average * tx.quantity
            profit = price_brl * tx.quantity - acquisition_cost - fees
            month = tx.date.strftime("%Y-%m")
            sales_by_month[month].append(
                {
                    "ticker": ticker,
                    "asset_type": asset_type,
                    "data": str(tx.date),
                    "quantidade": tx.quantity,
                    "preco_venda": round(price_brl, 2),
                    "custo_aquisicao": round(average, 2),
                    "lucro_bruto": round(profit, 2),
                    "is_day_trade": (tx.date, ticker) in day_trade_keys,
                    "total_venda_brl": round(price_brl * tx.quantity, 2),
                }
            )
            position["qty"] = max(0.0, position["qty"] - tx.quantity)
            position["cost"] = position["qty"] * average

    accumulated_loss = 0.0
    result: list[GanhoCapitalMensal] = []
    for month in sorted(sales_by_month):
        sales = sales_by_month[month]
        swing_stocks = [
            sale
            for sale in sales
            if not sale["is_day_trade"] and sale["asset_type"] in _ACAO_TYPES
        ]
        swing_others = [
            sale
            for sale in sales
            if not sale["is_day_trade"] and sale["asset_type"] not in _ACAO_TYPES
        ]
        day_trades = [sale for sale in sales if sale["is_day_trade"]]

        total_stock_sales = sum(sale["total_venda_brl"] for sale in swing_stocks)
        exemption = (
            total_stock_sales
            if total_stock_sales <= ISENCAO_ACOES_MENSAL
            else 0.0
        )
        swing_profit = sum(sale["lucro_bruto"] for sale in swing_stocks + swing_others)
        day_trade_profit = sum(sale["lucro_bruto"] for sale in day_trades)
        swing_base = max(0.0, swing_profit - exemption)

        if swing_base > 0 and accumulated_loss < 0:
            compensation = min(swing_base, abs(accumulated_loss))
            swing_base -= compensation
            accumulated_loss += compensation
        if swing_base < 0:
            accumulated_loss += swing_base
            swing_base = 0.0

        day_trade_base = max(0.0, day_trade_profit)
        swing_tax = round(swing_base * ALIQ_SWING, 2)
        day_trade_tax = round(day_trade_base * ALIQ_DAY_TRADE, 2)
        total_sales = sum(sale["total_venda_brl"] for sale in sales)
        total_cost = sum(
            sale["custo_aquisicao"] * sale["quantidade"] for sale in sales
        )

        output_sales = [
            VendaMensal(
                ticker=sale["ticker"],
                asset_type=sale["asset_type"],
                data=sale["data"],
                quantidade=sale["quantidade"],
                preco_venda=sale["preco_venda"],
                custo_aquisicao=sale["custo_aquisicao"],
                lucro_bruto=sale["lucro_bruto"],
                is_day_trade=sale["is_day_trade"],
                is_isento=(
                    not sale["is_day_trade"]
                    and sale["asset_type"] in _ACAO_TYPES
                    and total_stock_sales <= ISENCAO_ACOES_MENSAL
                ),
                ir_retido=0.0,
            )
            for sale in sales
        ]

        result.append(
            GanhoCapitalMensal(
                mes=month,
                total_vendas=round(total_sales, 2),
                total_custo=round(total_cost, 2),
                lucro_bruto=round(swing_profit + day_trade_profit, 2),
                lucro_day_trade=round(day_trade_profit, 2),
                lucro_swing_trade=round(swing_profit, 2),
                isencao_aplicada=round(exemption, 2),
                base_calculo=round(swing_base + day_trade_base, 2),
                aliquota_swing=ALIQ_SWING,
                aliquota_day_trade=ALIQ_DAY_TRADE,
                ir_devido_swing=swing_tax,
                ir_devido_day_trade=day_trade_tax,
                ir_retido_fonte=0.0,
                ir_a_recolher=round(swing_tax + day_trade_tax, 2),
                vendas=output_sales,
            )
        )

    return result


async def calc_rendimentos(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> tuple[list[RendimentoIsento], list[JCPItem]]:
    """Retorna dividendos isentos e JCP a partir de direitos canônicos em BRL."""

    start = date(year, 1, 1)
    end = date(year, 12, 31)
    entitlements = await load_portfolio_dividend_entitlements(db, portfolio_id)
    dividends: dict[str, dict] = {}
    jcp: dict[str, dict] = {}

    for item in entitlements:
        payment_date = item.event.payment_date
        if (
            item.entitlement.reason is not EntitlementReason.ELIGIBLE
            or item.entitlement.currency != "BRL"
            or payment_date is None
            or not start <= payment_date <= end
        ):
            continue

        ticker = item.ticker
        if item.event.event_type.upper() == "JCP":
            values = jcp.setdefault(
                ticker,
                {"bruto": 0.0, "retido": 0.0, "liquido": 0.0},
            )
            values["bruto"] += float(item.entitlement.gross_amount)
            values["retido"] += float(item.entitlement.withholding_tax)
            values["liquido"] += float(item.entitlement.net_amount)
        else:
            values = dividends.setdefault(
                ticker,
                {"total": 0.0, "count": 0, "asset_type": item.asset_type},
            )
            values["total"] += float(item.entitlement.net_amount)
            values["count"] += 1

    dividend_items = [
        RendimentoIsento(
            ticker=ticker,
            asset_type=values.get("asset_type", ""),
            total_recebido=round(values["total"], 2),
            quantidade_pgtos=values["count"],
        )
        for ticker, values in sorted(dividends.items())
    ]
    jcp_items = [
        JCPItem(
            ticker=ticker,
            total_bruto=round(values["bruto"], 2),
            ir_retido=round(values["retido"], 2),
            total_liquido=round(values["liquido"], 2),
        )
        for ticker, values in sorted(jcp.items())
    ]
    return dividend_items, jcp_items
