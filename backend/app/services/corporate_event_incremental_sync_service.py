"""Coleta incremental e observável do catálogo global de eventos corporativos."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.services.corporate_event_reconciliation_service import (
    reconcile_corporate_events_for_asset,
)
from app.services.corporate_event_service import (
    fetch_brapi_corporate_actions_payload,
    sync_corporate_events_for_asset,
)
from app.services.corporate_history_load_service import (
    CORPORATE_HISTORY_LOCK_KEY,
    ELIGIBLE_ASSET_TYPES,
)

CORPORATE_INCREMENTAL_SCHEMA_VERSION = "corporate-incremental-sync.v1"


@dataclass(frozen=True, slots=True)
class CorporateIncrementalSyncResult:
    date_from: str
    date_to: str
    assets_scanned: int
    assets_changed: int
    assets_failed: int
    events_created: int
    reconciliation: dict[str, int]
    errors: tuple[dict[str, str], ...]
    committed: bool
    skipped_reason: str | None = None
    schema_version: str = CORPORATE_INCREMENTAL_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


async def _acquire_incremental_lock(db: AsyncSession) -> bool:
    result = await db.execute(
        text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
        {"lock_key": CORPORATE_HISTORY_LOCK_KEY},
    )
    return result.scalar_one() is True


async def _load_assets(db: AsyncSession) -> tuple[Asset, ...]:
    result = await db.execute(
        select(Asset)
        .where(Asset.asset_type.in_(ELIGIBLE_ASSET_TYPES))
        .order_by(Asset.ticker, Asset.id)
    )
    return tuple(result.scalars().all())


async def run_incremental_corporate_event_sync(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
) -> CorporateIncrementalSyncResult:
    """Persiste sucessos por ciclo e isola falhas com savepoint por ativo."""
    if date_from > date_to:
        raise ValueError("date_from não pode ser posterior a date_to")

    errors: list[dict[str, str]] = []
    reconciliation = Counter[str]()
    assets_changed = events_created = 0
    try:
        if not await _acquire_incremental_lock(db):
            await db.rollback()
            return CorporateIncrementalSyncResult(
                date_from=date_from.isoformat(),
                date_to=date_to.isoformat(),
                assets_scanned=0,
                assets_changed=0,
                assets_failed=0,
                events_created=0,
                reconciliation={},
                errors=(),
                committed=False,
                skipped_reason="corporate_history_lock_busy",
            )

        assets = await _load_assets(db)
        for asset in assets:
            try:
                async with db.begin_nested():

                    async def brapi_fetcher(ticker: str) -> dict[str, object]:
                        return await fetch_brapi_corporate_actions_payload(
                            ticker,
                            date_from=date_from,
                            date_to=date_to,
                        )

                    created = await sync_corporate_events_for_asset(
                        db,
                        asset,
                        brapi_fetcher=brapi_fetcher,
                        date_from=date_from,
                        date_to=date_to,
                    )
                    report = await reconcile_corporate_events_for_asset(db, asset.id)
                    events_created += len(created)
                    assets_changed += int(bool(created))
                    reconciliation.update(
                        {
                            "matched": report.matched,
                            "conflicts": report.conflicts,
                            "unreconciled": report.unreconciled,
                            "canonical": report.canonical,
                            "suppressed_equivalents": report.suppressed_equivalents,
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    {
                        "ticker": str(asset.ticker),
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
                )

        await db.commit()
    except BaseException:
        await db.rollback()
        raise

    return CorporateIncrementalSyncResult(
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        assets_scanned=len(assets),
        assets_changed=assets_changed,
        assets_failed=len(errors),
        events_created=events_created,
        reconciliation=dict(reconciliation),
        errors=tuple(errors),
        committed=True,
    )
