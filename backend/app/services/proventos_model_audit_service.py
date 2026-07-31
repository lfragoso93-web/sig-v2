"""Read-only inventory of physical residues in the legacy dividend model."""

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend


@dataclass(frozen=True)
class ProventosModelAudit:
    """Counts required to plan the physical schema contraction."""

    asset_events: int
    legacy_dividend_rows: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def _count(db: AsyncSession, model: type[Any]) -> int:
    statement = select(func.count()).select_from(model)
    return int((await db.execute(statement)).scalar_one())


async def audit_proventos_model(db: AsyncSession) -> ProventosModelAudit:
    """Count canonical and legacy tables without inspecting materializations."""
    return ProventosModelAudit(
        asset_events=await _count(db, AssetDividend),
        legacy_dividend_rows=await _count(db, Dividend),
    )
