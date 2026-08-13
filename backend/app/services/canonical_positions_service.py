"""Contrato canônico da tabela de posições da página Resumo.

A camada reaproveita o valuation intradiário existente, mas projeta apenas o
contrato público canônico. Isso impede que campos legados vazem pelo endpoint e
mantém a validação FastAPI/Pydantic como gate de deriva arquitetural.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.canonical_dividend_aggregation_service import (
    load_received_entitlements_by_ticker,
)
from app.services.portfolio_service import get_portfolio_positions

_POSITION_KEYS = (
    "id",
    "ticker",
    "asset_type",
    "asset_label",
    "quantity",
    "average_price",
    "average_price_brl",
    "average_price_usd",
    "current_price",
    "current_price_brl",
    "current_price_usd",
    "current_value",
    "invested_value",
    "variation_value",
    "variation_percent",
    "allocation_pct",
    "logo_url",
    "is_usd",
    "currency",
    "quote_updated_at",
    "applications_count",
    "maturity_date",
    "indexer",
    "rate_pct",
)


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


def _project_position(position: dict) -> dict:
    return {key: position[key] for key in _POSITION_KEYS if key in position}


def _project_group(
    group: dict,
    *,
    received_dividends: float,
    proventos_as_of: str,
) -> dict:
    total_value = float(group.get("total_value") or 0)
    total_invested = float(group.get("total_invested") or 0)
    metrics = build_canonical_group_metrics(
        total_value=total_value,
        total_invested=total_invested,
        received_dividends=received_dividends,
    )

    return {
        "label": group["label"],
        "count": int(group.get("count") or 0),
        "total_value": total_value,
        "total_invested": total_invested,
        "positions": [
            _project_position(position) for position in group.get("positions", [])
        ],
        "daily_variation_value": group.get("daily_variation_value"),
        "daily_variation_pct": group.get("daily_variation_pct"),
        "variation_pct": group.get("daily_variation_pct"),
        "variation_reference_date": group.get("previous_reference_date"),
        **metrics,
        "proventos_grupo": round(received_dividends, 2),
        "performance_source": "intraday_valuation_and_received_dividends",
        "proventos_as_of": proventos_as_of,
        "target_pct": group.get("target_pct"),
    }


async def get_canonical_portfolio_positions(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> list[dict]:
    legacy_groups = await get_portfolio_positions(db, portfolio_id, user_id)

    tickers = [
        str(position.get("ticker", "")).upper()
        for group in legacy_groups
        for position in group.get("positions", [])
        if position.get("ticker")
    ]
    today = datetime.now(timezone.utc).date()
    dividends_by_ticker = await load_received_entitlements_by_ticker(
        db,
        portfolio_id,
        tickers,
        as_of=today,
    )

    canonical_groups: list[dict] = []
    for group in legacy_groups:
        positions = group.get("positions", [])
        received_dividends = sum(
            dividends_by_ticker.get(str(position.get("ticker", "")).upper(), 0.0)
            for position in positions
        )
        canonical_groups.append(
            _project_group(
                group,
                received_dividends=received_dividends,
                proventos_as_of=today.isoformat(),
            )
        )

    return canonical_groups
