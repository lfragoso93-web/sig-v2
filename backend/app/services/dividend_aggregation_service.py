"""Agregação canônica de proventos monetários efetivamente recebidos.

A regra financeira é única para Resumo e demais consumidores:
- somente status RECEBIDO;
- somente eventos monetários;
- competência pela data de pagamento;
- valor líquido quando disponível, com fallback para campos legados.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dividend import Dividend, DividendStatus

_NON_CASH_TYPES = {"BONIFICACAO", "SUBSCRICAO"}
_ZERO = Decimal("0")


def _decimal(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


def received_dividend_value(dividend: Dividend) -> Decimal:
    """Retorna o valor monetário canônico do registro recebido."""
    for field in ("net_value", "total_received", "total_value"):
        value = getattr(dividend, field, None)
        if value is not None:
            return _decimal(value)
    return _ZERO


def received_dividend_date(dividend: Dividend) -> date | None:
    return getattr(dividend, "payment_date", None) or getattr(dividend, "date_pagamento", None)


def is_received_cash_dividend(dividend: Dividend) -> bool:
    status = getattr(getattr(dividend, "status", None), "value", getattr(dividend, "status", None))
    dividend_type = str(getattr(dividend, "dividend_type", "") or "").upper()
    return (
        str(status or "").upper() == DividendStatus.RECEBIDO.value
        and dividend_type not in _NON_CASH_TYPES
        and received_dividend_date(dividend) is not None
        and received_dividend_value(dividend) > 0
    )


def aggregate_received_dividends(
    dividends: Iterable[Dividend],
    *,
    cutoff: date | None = None,
    as_of: date | None = None,
) -> Decimal:
    total = _ZERO
    for dividend in dividends:
        if not is_received_cash_dividend(dividend):
            continue
        payment_date = received_dividend_date(dividend)
        if payment_date is None:
            continue
        if cutoff is not None and payment_date < cutoff:
            continue
        if as_of is not None and payment_date > as_of:
            continue
        total += received_dividend_value(dividend)
    return total.quantize(Decimal("0.01"))


def _received_amount_expression():
    return func.coalesce(Dividend.net_value, Dividend.total_received, Dividend.total_value, 0)


def _received_payment_date_expression():
    return func.coalesce(Dividend.payment_date, Dividend.date_pagamento)


def _received_cash_filters(portfolio_id: int):
    payment_date = _received_payment_date_expression()
    return (
        Dividend.portfolio_id == portfolio_id,
        Dividend.status == DividendStatus.RECEBIDO,
        payment_date.is_not(None),
        func.upper(func.coalesce(Dividend.dividend_type, "")).notin_(_NON_CASH_TYPES),
    )


async def sum_received_dividends(
    db: AsyncSession,
    portfolio_id: int,
    *,
    cutoff: date | None = None,
    as_of: date | None = None,
    tickers: list[str] | None = None,
) -> float:
    payment_date = _received_payment_date_expression()
    query = select(func.sum(_received_amount_expression())).where(
        *_received_cash_filters(portfolio_id)
    )
    if cutoff is not None:
        query = query.where(payment_date >= cutoff)
    if as_of is not None:
        query = query.where(payment_date <= as_of)
    if tickers:
        query = query.where(Dividend.ticker.in_([ticker.upper() for ticker in tickers]))
    value = (await db.execute(query)).scalar_one_or_none()
    return float(_decimal(value).quantize(Decimal("0.01")))


async def sum_received_dividends_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
    tickers: list[str],
    *,
    as_of: date | None = None,
) -> dict[str, float]:
    """Retorna proventos líquidos recebidos agrupados por ticker."""
    normalized = sorted({ticker.upper() for ticker in tickers if ticker})
    if not normalized:
        return {}

    payment_date = _received_payment_date_expression()
    query = (
        select(
            func.upper(Dividend.ticker).label("ticker"),
            func.sum(_received_amount_expression()).label("total"),
        )
        .where(
            *_received_cash_filters(portfolio_id),
            func.upper(Dividend.ticker).in_(normalized),
        )
        .group_by(func.upper(Dividend.ticker))
    )
    if as_of is not None:
        query = query.where(payment_date <= as_of)

    rows = (await db.execute(query)).all()
    return {
        row.ticker: float(_decimal(row.total).quantize(Decimal("0.01")))
        for row in rows
    }
