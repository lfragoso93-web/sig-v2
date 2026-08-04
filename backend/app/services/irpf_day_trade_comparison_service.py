"""Orquestra comparação read-only de Day Trade canônico e legado."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.irpf_day_trade_legacy_comparison import (
    DayTradeMonthComparison,
    LegacyDayTradeMonth,
    compare_day_trade_months,
)
from app.services.irpf_day_trade_monthly_projection import (
    DayTradeMonthlyProjection,
    project_day_trades_by_month,
)
from app.services.irpf_day_trade_transaction_adapter import adapt_ordered_transactions
from app.services.irpf_tax_service import calc_ganhos_capital


@dataclass(frozen=True)
class DayTradeAnnualComparison:
    portfolio_id: int
    year: int
    monthly: tuple[DayTradeMonthComparison, ...]

    @property
    def has_divergences(self) -> bool:
        return any(not item.is_match for item in self.monthly)


def build_legacy_day_trade_months(legacy_months: list) -> tuple[LegacyDayTradeMonth, ...]:
    """Extrai a visão quantitativa mensal da saída fiscal legada."""

    result: list[LegacyDayTradeMonth] = []
    for month in legacy_months:
        quantity = sum(
            Decimal(str(sale.quantidade))
            for sale in month.vendas
            if sale.is_day_trade
        )
        if quantity == 0 and Decimal(str(month.lucro_day_trade)) == 0:
            continue
        result.append(
            LegacyDayTradeMonth(
                competence_month=month.mes,
                matched_quantity=quantity,
                day_trade_result_brl=Decimal(str(month.lucro_day_trade)),
            )
        )
    return tuple(result)


async def load_day_trade_projection(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> tuple[DayTradeMonthlyProjection, ...]:
    """Carrega transações do ano e produz a projeção quantitativa canônica."""

    rows = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date >= f"{year}-01-01",
            Transaction.date <= f"{year}-12-31",
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    operations = adapt_ordered_transactions(rows.scalars().all())
    return project_day_trades_by_month(operations)


async def compare_annual_day_trade_with_legacy(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> DayTradeAnnualComparison:
    """Executa ambos os caminhos e devolve somente a comparação mensal."""

    canonical = await load_day_trade_projection(db, portfolio_id, year)
    legacy = build_legacy_day_trade_months(
        await calc_ganhos_capital(db, portfolio_id, year)
    )
    return DayTradeAnnualComparison(
        portfolio_id=portfolio_id,
        year=year,
        monthly=compare_day_trade_months(canonical, legacy),
    )
