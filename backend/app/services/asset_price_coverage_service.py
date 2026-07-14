"""Auditoria DB-only da cobertura historica de precos por ativo.

Este modulo nao consulta provedores externos. Ele cruza o catalogo ``assets``, os
lancamentos e ``asset_prices`` para dizer exatamente quais ativos estao completos,
sem historico, com inicio ausente ou desatualizados. A sincronizacao de lacunas e
responsabilidade de outro servico.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import NO_QUOTE_TYPES
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.transaction import Transaction


class CoverageStatus(str, Enum):
    COMPLETE = "COMPLETE"
    MISSING = "MISSING"
    PARTIAL_START = "PARTIAL_START"
    STALE = "STALE"
    PARTIAL_BOTH = "PARTIAL_BOTH"
    MISSING_ASSET = "MISSING_ASSET"
    NO_MARKET_QUOTE = "NO_MARKET_QUOTE"


@dataclass(frozen=True)
class AssetPriceCoverage:
    ticker: str
    asset_type: str
    asset_id: int | None
    required_from: date | None
    required_to: date
    first_price_date: date | None
    last_price_date: date | None
    price_count: int
    status: CoverageStatus
    needs_sync: bool

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


def _as_asset_type(value: AssetType | str | None) -> AssetType:
    if isinstance(value, AssetType):
        return value
    return AssetType(str(value))


def classify_coverage(
    *,
    asset_type: AssetType,
    asset_exists: bool,
    required_from: date | None,
    required_to: date,
    first_price_date: date | None,
    last_price_date: date | None,
    grace_days: int = 5,
) -> CoverageStatus:
    """Classifica a cobertura pelas bordas conhecidas do historico.

    ``grace_days`` cobre fins de semana, feriados e diferencas pequenas entre a
    primeira operacao e o primeiro fechamento disponivel.
    """
    if asset_type in NO_QUOTE_TYPES:
        return CoverageStatus.NO_MARKET_QUOTE
    if not asset_exists:
        return CoverageStatus.MISSING_ASSET
    if first_price_date is None or last_price_date is None:
        return CoverageStatus.MISSING

    missing_start = (
        required_from is not None
        and first_price_date > required_from + timedelta(days=grace_days)
    )
    stale = last_price_date < required_to - timedelta(days=grace_days)

    if missing_start and stale:
        return CoverageStatus.PARTIAL_BOTH
    if missing_start:
        return CoverageStatus.PARTIAL_START
    if stale:
        return CoverageStatus.STALE
    return CoverageStatus.COMPLETE


async def audit_asset_price_coverage(
    db: AsyncSession,
    *,
    required_to: date | None = None,
) -> list[AssetPriceCoverage]:
    """Lista a cobertura de todos os ativos conhecidos pelo SGI.

    Inclui ativos presentes apenas em transacoes para revelar inconsistencias de
    catalogo que antes ficavam invisiveis.
    """
    target = required_to or datetime.now(timezone.utc).date()

    assets_result = await db.execute(select(Asset))
    assets = list(assets_result.scalars().all())
    assets_by_key = {
        (str(asset.ticker).upper(), str(asset.asset_type)): asset
        for asset in assets
    }

    tx_result = await db.execute(
        select(
            func.upper(Transaction.ticker).label("ticker"),
            Transaction.asset_type.label("asset_type"),
            func.min(Transaction.date).label("required_from"),
        )
        .group_by(func.upper(Transaction.ticker), Transaction.asset_type)
    )
    tx_requirements = {
        (str(row.ticker).upper(), str(row.asset_type)): row.required_from
        for row in tx_result.all()
    }

    price_result = await db.execute(
        select(
            AssetPrice.asset_id,
            func.min(AssetPrice.timestamp).label("first_ts"),
            func.max(AssetPrice.timestamp).label("last_ts"),
            func.count(AssetPrice.id).label("price_count"),
        )
        .group_by(AssetPrice.asset_id)
    )
    price_stats = {row.asset_id: row for row in price_result.all()}

    keys = set(assets_by_key) | set(tx_requirements)
    report: list[AssetPriceCoverage] = []

    for ticker, asset_type_raw in sorted(keys):
        try:
            asset_type = _as_asset_type(asset_type_raw)
        except ValueError:
            asset_type = AssetType.OUTRO

        asset = assets_by_key.get((ticker, asset_type_raw))
        stats = price_stats.get(asset.id) if asset is not None else None
        first_date = stats.first_ts.date() if stats and stats.first_ts else None
        last_date = stats.last_ts.date() if stats and stats.last_ts else None
        count = int(stats.price_count or 0) if stats else 0
        required_from = tx_requirements.get((ticker, asset_type_raw))
        status = classify_coverage(
            asset_type=asset_type,
            asset_exists=asset is not None,
            required_from=required_from,
            required_to=target,
            first_price_date=first_date,
            last_price_date=last_date,
        )
        report.append(
            AssetPriceCoverage(
                ticker=ticker,
                asset_type=asset_type.value,
                asset_id=asset.id if asset is not None else None,
                required_from=required_from,
                required_to=target,
                first_price_date=first_date,
                last_price_date=last_date,
                price_count=count,
                status=status,
                needs_sync=status
                not in {CoverageStatus.COMPLETE, CoverageStatus.NO_MARKET_QUOTE},
            )
        )

    return report


async def summarize_asset_price_coverage(
    db: AsyncSession,
    *,
    required_to: date | None = None,
) -> dict:
    report = await audit_asset_price_coverage(db, required_to=required_to)
    by_status: dict[str, int] = {}
    for item in report:
        by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
    return {
        "total_assets": len(report),
        "needs_sync": sum(1 for item in report if item.needs_sync),
        "by_status": by_status,
        "assets": [item.to_dict() for item in report],
    }
