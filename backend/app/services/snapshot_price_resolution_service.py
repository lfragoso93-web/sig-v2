"""Resolucao de precos de snapshot sob a politica DB-first.

O servico recebe o mapa ja lido do banco e somente para tickers ausentes aciona
o resolvedor pontual de lacuna historica. Nenhum prefetch amplo ou proxy de
preco e permitido.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import AssetType
from app.services.price_date_gap_resolver_service import resolve_price_at_date_gap


@dataclass(frozen=True)
class SnapshotPriceRequirement:
    ticker: str
    asset_type: AssetType


class SnapshotPriceUnavailableError(RuntimeError):
    """Cotacao historica obrigatoria continuou ausente apos fallback pontual."""


async def resolve_missing_snapshot_prices(
    db: AsyncSession,
    requirements: list[SnapshotPriceRequirement],
    target_date: str,
    prices: dict[str, float | None],
) -> dict[str, float]:
    """Completa somente lacunas reais e falha se alguma permanecer sem preco."""
    resolved: dict[str, float] = {
        ticker: float(value)
        for ticker, value in prices.items()
        if value is not None
    }

    missing: list[str] = []
    for requirement in requirements:
        if requirement.ticker in resolved:
            continue

        price = await resolve_price_at_date_gap(
            db,
            requirement.ticker,
            requirement.asset_type,
            target_date,
        )
        if price is None:
            missing.append(requirement.ticker)
            continue
        resolved[requirement.ticker] = float(price)

    if missing:
        tickers = ", ".join(sorted(set(missing)))
        raise SnapshotPriceUnavailableError(
            f"cotacao historica ausente para snapshot em {target_date}: {tickers}"
        )

    return resolved
