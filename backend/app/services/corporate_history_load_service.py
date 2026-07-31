"""Carga histórica controlada do catálogo global de eventos corporativos."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.corporate_event import CorporateEvent
from app.services.corporate_event_reconciliation_service import (
    reconcile_corporate_events_for_asset,
)
from app.services.corporate_event_service import (
    fetch_brapi_corporate_actions_payload,
    sync_corporate_events_for_asset,
)

CORPORATE_HISTORY_SCHEMA_VERSION = "corporate-history-load.v1"
CORPORATE_HISTORY_LOCK_KEY = 743_219_031
ELIGIBLE_ASSET_TYPES = ("ACAO", "BDR", "ETF_NACIONAL")


class CorporateHistoryAlreadyRunningError(RuntimeError):
    """Outra carga corporativa mantém o lock transacional."""


@dataclass(frozen=True)
class CorporateHistoryState:
    total_events: int
    assets_with_events: int
    canonical_events: int
    conflicts: int
    unreconciled: int


@dataclass(frozen=True)
class CorporateHistoryLoadResult:
    run_id: str
    generated_at: str
    date_from: str
    date_to: str
    dry_run: bool
    ok: bool
    transaction_state: str
    committed: bool
    before: CorporateHistoryState
    projected_after: CorporateHistoryState
    assets_scanned: int
    assets_changed: int
    events_created: int
    reconciliation: dict[str, int]
    errors: tuple[dict[str, str], ...]
    schema_version: str = CORPORATE_HISTORY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def inspect_corporate_history_state(db: AsyncSession) -> CorporateHistoryState:
    result = await db.execute(
        select(
            func.count(CorporateEvent.id),
            func.count(func.distinct(CorporateEvent.asset_id)),
            func.count(CorporateEvent.id).filter(CorporateEvent.is_canonical.is_(True)),
            func.count(CorporateEvent.id).filter(
                CorporateEvent.reconciliation_status == "CONFLICT"
            ),
            func.count(CorporateEvent.id).filter(
                CorporateEvent.reconciliation_status == "UNRECONCILED"
            ),
        ).where(CorporateEvent.portfolio_id.is_(None))
    )
    row = result.one()
    return CorporateHistoryState(*(int(value or 0) for value in row))


async def load_corporate_history_assets(db: AsyncSession) -> tuple[Asset, ...]:
    result = await db.execute(
        select(Asset)
        .where(Asset.asset_type.in_(ELIGIBLE_ASSET_TYPES))
        .order_by(Asset.ticker, Asset.id)
    )
    return tuple(result.scalars().all())


async def _acquire_lock(db: AsyncSession) -> None:
    result = await db.execute(
        text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
        {"lock_key": CORPORATE_HISTORY_LOCK_KEY},
    )
    if result.scalar_one() is not True:
        raise CorporateHistoryAlreadyRunningError(
            "outra carga histórica corporativa já está em execução"
        )


async def run_corporate_history_load(
    *,
    run_id: str,
    date_from: date,
    date_to: date,
    dry_run: bool,
    db: AsyncSession,
) -> CorporateHistoryLoadResult:
    """Executa a coleta em uma transação; dry-run sempre termina em rollback."""
    if not run_id.strip():
        raise ValueError("run_id é obrigatório")
    if date_from > date_to:
        raise ValueError("date_from não pode ser posterior a date_to")

    before = await inspect_corporate_history_state(db)
    errors: list[dict[str, str]] = []
    reconciliation = Counter[str]()
    events_created = assets_changed = 0
    try:
        await _acquire_lock(db)
        assets = await load_corporate_history_assets(db)
        for asset in assets:
            try:
                async with db.begin_nested():

                    async def brapi_fetcher(ticker: str) -> dict[str, Any]:
                        return await fetch_brapi_corporate_actions_payload(
                            ticker, date_from=date_from, date_to=date_to
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

        projected_after = await inspect_corporate_history_state(db)
        if dry_run or errors:
            await db.rollback()
            transaction_state = "dry_run_rolled_back" if dry_run else "rolled_back"
            committed = False
        else:
            await db.commit()
            transaction_state = "committed"
            committed = True
    except BaseException:
        await db.rollback()
        raise

    return CorporateHistoryLoadResult(
        run_id=run_id,
        generated_at=datetime.now(UTC).isoformat(),
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        dry_run=dry_run,
        ok=not errors,
        transaction_state=transaction_state,
        committed=committed,
        before=before,
        projected_after=projected_after,
        assets_scanned=len(assets),
        assets_changed=assets_changed,
        events_created=events_created,
        reconciliation=dict(reconciliation),
        errors=tuple(errors),
    )
