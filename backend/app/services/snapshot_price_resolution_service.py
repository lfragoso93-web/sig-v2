"""Validacao DB-first de precos obrigatorios para snapshots.

O servico recebe o mapa de precos ja lido do banco e nunca consulta provedores
nem persiste dados. Pipelines de mercado sao responsaveis por preencher
``asset_prices`` antes do calculo de snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import AssetType


@dataclass(frozen=True)
class SnapshotPriceRequirement:
    ticker: str
    asset_type: AssetType


class SnapshotPriceUnavailableError(RuntimeError):
    """Cotacao historica obrigatoria nao esta persistida para o snapshot."""


async def resolve_missing_snapshot_prices(
    db: AsyncSession,
    requirements: list[SnapshotPriceRequirement],
    target_date: str,
    prices: dict[str, float | None],
) -> dict[str, float]:
    """Valida cobertura persistida e falha explicitamente se houver lacunas."""
    del db
    resolved: dict[str, float] = {
        ticker: float(value)
        for ticker, value in prices.items()
        if value is not None
    }

    missing = sorted(
        {
            requirement.ticker
            for requirement in requirements
            if requirement.ticker not in resolved
        }
    )
    if missing:
        tickers = ", ".join(missing)
        raise SnapshotPriceUnavailableError(
            f"cotacao historica persistida ausente para snapshot em {target_date}: {tickers}"
        )

    return resolved
