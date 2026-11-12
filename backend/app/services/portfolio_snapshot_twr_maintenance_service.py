"""Manutenção automática dos snapshots enriquecidos consolidados e por classe."""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.fx_rate import FxRate
from app.models.rate_history import RateHistory
from app.models.portfolio import Portfolio
from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction
from app.services.canonical_dividend_aggregation_service import (
    aggregate_received_entitlements,
)
from app.services.canonical_dividend_entitlement_reader import (
    load_portfolio_dividend_entitlements,
)
from app.services.portfolio_class_reconciliation_service import (
    reconcile_latest_class_snapshots,
)
from app.services.portfolio_class_snapshot_service import (
    SUPPORTED_CLASS_TWR_TYPES,
    rebuild_class_snapshots,
)
from app.services.portfolio_snapshot_canonical_twr_service import (
    backfill_canonical_snapshots_with_returns,
)
from app.services.portfolio_snapshot_access_service import (
    authorize_system_snapshot_maintenance,
)

logger = logging.getLogger(__name__)
_BRT = ZoneInfo("America/Sao_Paulo")
_MONEY_TOLERANCE = Decimal("0.01")
_RETURN_TOLERANCE = Decimal("0.000001")


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def _today_brt() -> date:
    return datetime.now(_BRT).date()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _latest_weekday_close_date(today: date | None = None) -> date:
    """Class snapshots follow market weekdays; avoid rebuilding them on weekends."""
    target = today or _today_brt()
    while target.weekday() >= 5:
        target -= timedelta(days=1)
    return target


def _latest_snapshot_has_legacy_zero_twr(
    latest: PortfolioSnapshot,
    previous: PortfolioSnapshot | None,
) -> bool:
    """Detecta snapshot diário criado pelo refresh legado sem TWR materializado.

    O refresh patrimonial simples pode inserir o fechamento do dia apenas com os
    campos monetários. Como os campos TWR possuem default zero, esse registro fica
    indistinguível de uma performance realmente neutra quando observado sozinho.
    A comparação com o fechamento anterior e com o retorno simples evita que esse
    zero técnico seja promovido ao contrato ``summary.v2``.
    """
    if previous is None:
        return False

    latest_accumulated = _decimal(latest.accumulated_return_pct)
    latest_daily = _decimal(latest.daily_return_pct)
    previous_accumulated = _decimal(previous.accumulated_return_pct)
    simple_return = _decimal(latest.return_pct)

    twr_is_zero = (
        abs(latest_accumulated) <= _RETURN_TOLERANCE
        and abs(latest_daily) <= _RETURN_TOLERANCE
    )
    historical_twr_exists = abs(previous_accumulated) > _RETURN_TOLERANCE
    monetary_return_exists = abs(simple_return) > _RETURN_TOLERANCE

    return twr_is_zero and (historical_twr_exists or monetary_return_exists)


async def _has_newer_market_inputs(
    db: AsyncSession,
    portfolio_id: int,
    latest: PortfolioSnapshot,
    *,
    now_brt: datetime,
) -> bool:
    snapshot_updated = _as_utc(latest.updated_at or latest.created_at)
    if snapshot_updated is None:
        return True

    today_brt = now_brt.date()
    snapshot_brt = snapshot_updated.astimezone(_BRT)
    if (
        latest.snapshot_date == today_brt
        and now_brt.time() >= time(20, 45)
        and (snapshot_brt.date() < today_brt or snapshot_brt.time() < time(20, 45))
    ):
        return True

    portfolio_assets = (
        select(Asset.id)
        .join(
            Transaction,
            (func.upper(func.trim(Transaction.ticker)) == func.upper(func.trim(Asset.ticker)))
            & (Transaction.asset_type == Asset.asset_type),
        )
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    max_price_sync = _as_utc(
        (
            await db.execute(
                select(func.max(Asset.provider_last_sync_at)).where(
                    Asset.id.in_(portfolio_assets),
                )
            )
        ).scalar_one_or_none()
    )
    if max_price_sync is not None and max_price_sync > snapshot_updated:
        return True

    max_fx_created = _as_utc(
        (
            await db.execute(
                select(func.max(FxRate.created_at)).where(FxRate.pair == "USD-BRL")
            )
        ).scalar_one_or_none()
    )
    if max_fx_created is not None and max_fx_created > snapshot_updated:
        return True

    max_rate_created = _as_utc(
        (
            await db.execute(
                select(func.max(RateHistory.created_at)).where(
                    RateHistory.indicator.in_(("CDI", "SELIC"))
                )
            )
        ).scalar_one_or_none()
    )
    if max_rate_created is not None and max_rate_created > snapshot_updated:
        return True

    return False


async def _portfolio_needs_twr_rebuild(
    db: AsyncSession,
    portfolio_id: int,
    *,
    now_brt: datetime | None = None,
) -> bool:
    current_brt = now_brt or datetime.now(_BRT)
    today_brt = current_brt.date()

    first_tx_result = await db.execute(
        select(func.min(Transaction.date)).where(Transaction.portfolio_id == portfolio_id)
    )
    first_date = first_tx_result.scalar_one_or_none()
    if first_date is None:
        return False

    snapshot_result = await db.execute(
        select(
            func.count(PortfolioSnapshot.id),
            func.min(PortfolioSnapshot.snapshot_date),
            func.max(PortfolioSnapshot.snapshot_date),
        ).where(PortfolioSnapshot.portfolio_id == portfolio_id)
    )
    count, min_date, max_date = snapshot_result.one()
    if int(count or 0) == 0 or min_date is None or min_date > first_date:
        return True
    if max_date is None or max_date < today_brt:
        return True

    latest_rows_result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(2)
    )
    latest_rows = list(latest_rows_result.scalars().all())
    latest = latest_rows[0] if latest_rows else None
    previous = latest_rows[1] if len(latest_rows) > 1 else None
    if latest is None:
        return True

    canonical_dividends = aggregate_received_entitlements(
        await load_portfolio_dividend_entitlements(db, portfolio_id),
        as_of=latest.snapshot_date,
    )
    snapshot_dividends = _decimal(latest.dividends_accumulated)
    if abs(snapshot_dividends - canonical_dividends) > _MONEY_TOLERANCE:
        return True

    if _latest_snapshot_has_legacy_zero_twr(latest, previous):
        logger.warning(
            "[snapshot_twr_auto] portfolio=%s snapshot=%s possui TWR técnico zerado; reconstruindo",
            portfolio_id,
            latest.snapshot_date,
        )
        return True

    if await _has_newer_market_inputs(db, portfolio_id, latest, now_brt=current_brt):
        logger.info(
            "[snapshot_twr_auto] portfolio=%s possui insumos de mercado mais recentes; reconstruindo",
            portfolio_id,
        )
        return True

    return False


async def _portfolio_needs_class_twr_rebuild(db: AsyncSession, portfolio_id: int) -> bool:
    supported_values = [asset_type.value for asset_type in SUPPORTED_CLASS_TWR_TYPES]
    transaction_types_result = await db.execute(
        select(Transaction.asset_type)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_type.in_(list(SUPPORTED_CLASS_TWR_TYPES)),
        )
        .distinct()
    )
    transaction_types = {
        str(getattr(value, "value", value)).upper()
        for value in transaction_types_result.scalars().all()
    }
    if not transaction_types:
        return False

    snapshot_result = await db.execute(
        select(
            PortfolioClassSnapshot.asset_type,
            func.max(PortfolioClassSnapshot.snapshot_date),
        )
        .where(
            PortfolioClassSnapshot.portfolio_id == portfolio_id,
            PortfolioClassSnapshot.asset_type.in_(supported_values),
        )
        .group_by(PortfolioClassSnapshot.asset_type)
    )
    latest_by_type = {row.asset_type: row[1] for row in snapshot_result.all()}
    weekday_close = _latest_weekday_close_date()
    if any(
        latest_by_type.get(asset_type) is None
        or latest_by_type[asset_type] < (_today_brt() if asset_type == AssetType.CRIPTO.value else weekday_close)
        for asset_type in transaction_types
    ):
        return True

    reconciliation = await reconcile_latest_class_snapshots(db, portfolio_id)
    if (
        reconciliation.get("is_comparable") is True
        and reconciliation.get("is_reconciled") is False
    ):
        logger.warning(
            "[snapshot_twr_auto] portfolio=%s divergência entre consolidado e classes em %s; reconstruindo",
            portfolio_id,
            reconciliation.get("snapshot_date"),
        )
        return True

    return False


async def maintain_twr_snapshots_for_active_portfolios(
    db: AsyncSession,
) -> dict[str, int]:
    result = await db.execute(
        select(Portfolio.id)
        .join(Transaction, Transaction.portfolio_id == Portfolio.id)
        .where(Portfolio.is_active.is_(True))
        .distinct()
    )
    portfolio_ids = [row.id for row in result.all()]

    processed = 0
    skipped = 0
    errors = 0
    snapshots = 0
    class_snapshots = 0

    for portfolio_id in portfolio_ids:
        try:
            access = await authorize_system_snapshot_maintenance(
                db,
                portfolio_id,
                purpose="background_nightly_twr_maintenance",
            )
            rebuild_consolidated = await _portfolio_needs_twr_rebuild(db, access.portfolio_id)
            rebuild_classes = await _portfolio_needs_class_twr_rebuild(db, access.portfolio_id)
            if not rebuild_consolidated and not rebuild_classes:
                skipped += 1
                continue
            logger.info(
                "[snapshot_twr_auto] portfolio=%s executando manutencao (purpose=%s)",
                access.portfolio_id,
                access.purpose,
            )
            if rebuild_consolidated:
                snapshots += await backfill_canonical_snapshots_with_returns(
                    db,
                    access.portfolio_id,
                    end_date=_today_brt(),
                )
            if rebuild_classes:
                class_snapshots += await rebuild_class_snapshots(db, access.portfolio_id)
            processed += 1
        except Exception as exc:
            await db.rollback()
            errors += 1
            logger.exception(
                "[snapshot_twr_auto] portfolio=%s falhou: %s",
                portfolio_id,
                exc,
            )

    return {
        "portfolios": len(portfolio_ids),
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "snapshots": snapshots,
        "class_snapshots": class_snapshots,
    }
