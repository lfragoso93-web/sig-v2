"""Resolução local, determinística e auditável do ativo de destino."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.corporate_event import CorporateEvent


class DestinationResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    MISSING_IDENTITY = "MISSING_IDENTITY"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class DestinationAssetResolution:
    status: DestinationResolutionStatus
    asset_id: int | None
    ticker: str | None
    matched_by: tuple[str, ...]
    candidate_ids: tuple[int, ...]


def _normalized(value: object) -> str | None:
    text = str(value or "").strip().upper()
    return text or None


async def resolve_corporate_destination_asset(
    db: AsyncSession,
    event: CorporateEvent,
    *,
    bind: bool = False,
) -> DestinationAssetResolution:
    """Resolve somente contra o catálogo local; nunca cria ativos implicitamente."""

    if event.destination_asset_id is not None:
        asset = await db.get(Asset, int(event.destination_asset_id))
        if asset is None:
            return DestinationAssetResolution(
                DestinationResolutionStatus.NOT_FOUND,
                None,
                None,
                ("asset_id",),
                (),
            )
        ticker = _normalized(event.destination_ticker)
        isin = _normalized(event.destination_isin_code)
        if ticker and ticker not in {
            _normalized(asset.ticker),
            _normalized(asset.brapi_ticker),
        }:
            return DestinationAssetResolution(
                DestinationResolutionStatus.CONFLICT,
                None,
                None,
                ("asset_id", "ticker"),
                (int(asset.id),),
            )
        if isin and isin != _normalized(asset.isin_code):
            return DestinationAssetResolution(
                DestinationResolutionStatus.CONFLICT,
                None,
                None,
                ("asset_id", "isin_code"),
                (int(asset.id),),
            )
        return DestinationAssetResolution(
            DestinationResolutionStatus.RESOLVED,
            int(asset.id),
            str(asset.ticker),
            ("asset_id",),
            (int(asset.id),),
        )

    ticker = _normalized(event.destination_ticker)
    isin = _normalized(event.destination_isin_code)
    if not ticker and not isin:
        return DestinationAssetResolution(
            DestinationResolutionStatus.MISSING_IDENTITY, None, None, (), ()
        )

    filters = []
    matched_by: list[str] = []
    if ticker:
        filters.append(
            or_(
                func.upper(Asset.ticker) == ticker,
                func.upper(Asset.brapi_ticker) == ticker,
            )
        )
        matched_by.append("ticker")
    if isin:
        filters.append(func.upper(Asset.isin_code) == isin)
        matched_by.append("isin_code")

    result = await db.execute(select(Asset).where(*filters).order_by(Asset.id))
    candidates = list(result.scalars().all())
    if not candidates:
        return DestinationAssetResolution(
            DestinationResolutionStatus.NOT_FOUND,
            None,
            None,
            tuple(matched_by),
            (),
        )
    if len(candidates) > 1:
        return DestinationAssetResolution(
            DestinationResolutionStatus.AMBIGUOUS,
            None,
            None,
            tuple(matched_by),
            tuple(int(item.id) for item in candidates),
        )

    asset = candidates[0]
    if bind:
        event.destination_asset_id = int(asset.id)
        event.destination_ticker = str(asset.ticker)
    return DestinationAssetResolution(
        DestinationResolutionStatus.RESOLVED,
        int(asset.id),
        str(asset.ticker),
        tuple(matched_by),
        (int(asset.id),),
    )
