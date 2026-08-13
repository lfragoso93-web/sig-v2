"""Inventário read-only da compatibilidade histórica do catálogo corporativo."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent

_LEGACY_PROVIDERS = (None, "", "legacy")


@dataclass(frozen=True)
class CorporateEventLegacyInventory:
    total_legacy: int
    global_legacy: int
    portfolio_bound_legacy: int
    ignored_legacy: int
    without_source_event_id: int
    without_effective_date: int
    without_quantity_factor: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


async def load_corporate_event_legacy_inventory(
    db: AsyncSession,
) -> CorporateEventLegacyInventory:
    """Retorna métricas determinísticas sem reconciliar nem alterar registros."""

    provider = func.lower(func.coalesce(CorporateEvent.source_provider, ""))
    legacy_filter = provider.in_(["", "legacy"])

    result = await db.execute(
        select(
            func.count(CorporateEvent.id).filter(legacy_filter),
            func.count(CorporateEvent.id).filter(
                legacy_filter,
                CorporateEvent.portfolio_id.is_(None),
            ),
            func.count(CorporateEvent.id).filter(
                legacy_filter,
                CorporateEvent.portfolio_id.is_not(None),
            ),
            func.count(CorporateEvent.id).filter(
                legacy_filter,
                func.upper(func.coalesce(CorporateEvent.status, "")) == "IGNORADO",
            ),
            func.count(CorporateEvent.id).filter(
                legacy_filter,
                CorporateEvent.source_event_id.is_(None),
            ),
            func.count(CorporateEvent.id).filter(
                legacy_filter,
                CorporateEvent.effective_date.is_(None),
            ),
            func.count(CorporateEvent.id).filter(
                legacy_filter,
                CorporateEvent.quantity_factor.is_(None),
            ),
        )
    )
    row = result.one()

    return CorporateEventLegacyInventory(
        total_legacy=int(row[0] or 0),
        global_legacy=int(row[1] or 0),
        portfolio_bound_legacy=int(row[2] or 0),
        ignored_legacy=int(row[3] or 0),
        without_source_event_id=int(row[4] or 0),
        without_effective_date=int(row[5] or 0),
        without_quantity_factor=int(row[6] or 0),
    )
