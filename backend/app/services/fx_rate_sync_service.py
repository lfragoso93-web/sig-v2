"""Sincronizacao diaria idempotente da taxa de cambio USD-BRL (PTAX BCB)."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.bcb_ptax_strict import (
    PTAX_PAIR,
    StrictPtaxError,
    StrictPtaxRate,
    fetch_strict_usd_brl_period,
)
from app.models.fx_rate import FxRate

logger = logging.getLogger(__name__)
_BRT = ZoneInfo("America/Sao_Paulo")


async def _upsert_fx_rates(
    db: AsyncSession,
    rows: tuple[StrictPtaxRate, ...],
) -> tuple[int, int]:
    if not rows:
        return 0, 0

    dialect_name = db.bind.dialect.name if db.bind is not None else ""
    inserted = 0
    updated = 0

    now_utc = datetime.now(timezone.utc)
    if dialect_name == "postgresql":
        for item in rows:
            existing = (
                await db.execute(
                    select(FxRate.rate).where(
                        FxRate.pair == item.pair,
                        FxRate.rate_date == item.rate_date,
                    )
                )
            ).scalar_one_or_none()
            update_fields: dict[str, object] = {"rate": item.rate}
            if existing is not None and existing != item.rate:
                update_fields["created_at"] = now_utc
            stmt = (
                pg_insert(FxRate)
                .values(pair=item.pair, rate_date=item.rate_date, rate=item.rate, created_at=now_utc)
                .on_conflict_do_update(
                    constraint="uq_fx_rates_pair_date",
                    set_=update_fields,
                )
            )
            await db.execute(stmt)
            if existing is None:
                inserted += 1
            elif existing != item.rate:
                updated += 1
        return inserted, updated

    for item in rows:
        existing_row = (
            await db.execute(
                select(FxRate).where(
                    FxRate.pair == item.pair,
                    FxRate.rate_date == item.rate_date,
                )
            )
        ).scalar_one_or_none()
        if existing_row is None:
            db.add(FxRate(pair=item.pair, rate_date=item.rate_date, rate=item.rate, created_at=now_utc))
            inserted += 1
        elif existing_row.rate != item.rate:
            existing_row.rate = item.rate
            existing_row.created_at = now_utc
            updated += 1
    return inserted, updated


async def sync_usd_brl_fx_rates(
    db: AsyncSession,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    """Sincroniza cotacoes diarias PTAX USD-BRL faltantes ate ``end_date``."""
    target_end = end_date or datetime.now(_BRT).date()
    latest_existing = (
        await db.execute(
            select(func.max(FxRate.rate_date)).where(FxRate.pair == PTAX_PAIR)
        )
    ).scalar_one_or_none()

    if start_date is not None:
        target_start = start_date
    elif latest_existing is not None:
        target_start = min(latest_existing - timedelta(days=3), target_end)
    else:
        target_start = target_end - timedelta(days=14)

    if target_start > target_end:
        target_start = target_end

    try:
        rows = await fetch_strict_usd_brl_period(target_start, target_end)
    except StrictPtaxError as exc:
        logger.warning(
            "[fx_sync] PTAX indisponivel para %s..%s: %s",
            target_start.isoformat(),
            target_end.isoformat(),
            exc,
        )
        return {
            "pair": PTAX_PAIR,
            "start_date": target_start.isoformat(),
            "end_date": target_end.isoformat(),
            "fetched": 0,
            "inserted": 0,
            "updated": 0,
            "latest_date": latest_existing.isoformat() if latest_existing else None,
            "warning": str(exc),
        }

    inserted, updated = await _upsert_fx_rates(db, rows)
    await db.commit()
    latest_date = max((r.rate_date for r in rows), default=latest_existing)
    logger.info(
        "[fx_sync] pair=%s fetched=%d inserted=%d updated=%d latest=%s",
        PTAX_PAIR,
        len(rows),
        inserted,
        updated,
        latest_date.isoformat() if latest_date else None,
    )
    return {
        "pair": PTAX_PAIR,
        "start_date": target_start.isoformat(),
        "end_date": target_end.isoformat(),
        "fetched": len(rows),
        "inserted": inserted,
        "updated": updated,
        "latest_date": latest_date.isoformat() if latest_date else None,
    }
