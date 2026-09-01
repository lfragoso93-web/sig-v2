"""Catálogo B3 COTAHIST-first sem dependência de provider externo."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.b3_cotahist import (
    CotahistClassificationStatus,
    CotahistRecord,
    classify_cotahist_record,
)
from app.models.asset import Asset


@dataclass
class B3CotahistCatalogResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    unresolved: int = 0
    ineligible: int = 0
    by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _currency_from_cotahist(raw: str) -> str:
    normalized = raw.strip().upper()
    if normalized in {"R$", "REAL", "BRL"}:
        return "BRL"
    return normalized or "BRL"


async def upsert_b3_cotahist_catalog(
    db: AsyncSession,
    records: list[CotahistRecord],
) -> B3CotahistCatalogResult:
    """Cria/atualiza catálogo B3 mínimo a partir de registros COTAHIST."""
    result = B3CotahistCatalogResult()
    seen: set[tuple[str, str]] = set()

    for record in records:
        classification = classify_cotahist_record(record)
        if classification.status == CotahistClassificationStatus.INELEGIVEL:
            result.ineligible += 1
            continue
        if (
            classification.status != CotahistClassificationStatus.CLASSIFIED
            or classification.asset_type is None
        ):
            result.unresolved += 1
            continue

        asset_type = classification.asset_type.value
        ticker = record.ticker.upper().strip()
        identity = (ticker, asset_type)
        if identity in seen:
            result.skipped += 1
            continue
        seen.add(identity)

        existing = (
            await db.execute(
                select(Asset).where(
                    Asset.ticker == ticker,
                    Asset.asset_type == asset_type,
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            db.add(
                Asset(
                    ticker=ticker,
                    name=record.short_name.strip() or ticker,
                    asset_type=asset_type,
                    currency=_currency_from_cotahist(record.currency),
                    isin_code=record.isin,
                )
            )
            result.created += 1
            result.by_type[asset_type] = result.by_type.get(asset_type, 0) + 1
            continue

        changed = False
        if not existing.name and record.short_name.strip():
            existing.name = record.short_name.strip()
            changed = True
        if not existing.currency and record.currency.strip():
            existing.currency = _currency_from_cotahist(record.currency)
            changed = True
        if not existing.isin_code and record.isin:
            existing.isin_code = record.isin
            changed = True

        if changed:
            result.updated += 1
        else:
            result.skipped += 1

    await db.flush()
    return result
