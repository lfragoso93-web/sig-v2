"""Contrato canônico da tabela de posições da página Resumo.

A camada reaproveita o valuation intradiário existente, mas normaliza as métricas
por classe para evitar chamar retorno simples de rentabilidade:
- variação diária permanece separada e referenciada;
- resultado patrimonial é atual menos custo das posições abertas;
- proventos são apenas valores líquidos efetivamente recebidos;
- resultado total é resultado patrimonial mais proventos recebidos.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.canonical_dividend_aggregation_service import (
    load_received_entitlements_by_ticker,
)
from app.services.portfolio_service import get_portfolio_positions


def _percentage(value: float, base: float) -> float | None:
    if base <= 0:
        return None
    return round(value / base * 100, 4)


def build_canonical_group_metrics(
    *,
    total_value: float,
    total_invested: float,
    received_dividends: float,
) -> dict[str, float | None]:
    capital_result = round(total_value - total_invested, 2)
    total_result = round(capital_result + received_dividends, 2)
    return {
        "capital_result_value": capital_result,
        "capital_result_pct": _percentage(capital_result, total_invested),
        "received_dividends": round(received_dividends, 2),
        "total_result_value": total_result,
        "total_result_pct": _percentage(total_result, total_invested),
    }


async def get_canonical_portfolio_positions(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> list[dict]:
    legacy_groups = await get_portfolio_positions(db, portfolio_id, user_id)
    groups = deepcopy(legacy_groups)

    tickers = [
        str(position.get("ticker", "")).upper()
        for group in groups
        for position in group.get("positions", [])
        if position.get("ticker")
    ]
    dividends_by_ticker = await load_received_entitlements_by_ticker(
        db,
        portfolio_id,
        tickers,
        as_of=date.today(),
    )

    for group in groups:
        positions = group.get("positions", [])
        total_value = float(group.get("total_value") or 0)
        total_invested = float(group.get("total_invested") or 0)
        received_dividends = sum(
            dividends_by_ticker.get(str(position.get("ticker", "")).upper(), 0.0)
            for position in positions
        )

        group.update(
            build_canonical_group_metrics(
                total_value=total_value,
                total_invested=total_invested,
                received_dividends=received_dividends,
            )
        )
        group["proventos_grupo"] = round(received_dividends, 2)
        group["performance_source"] = "intraday_valuation_and_received_dividends"
        group["proventos_as_of"] = date.today().isoformat()

        # Campo legado calculava retorno simples e era apresentado como rentabilidade.
        group.pop("rentabilidade_pct", None)

    return groups
