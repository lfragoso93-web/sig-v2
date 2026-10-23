"""Serviço de notificação matinal por e-mail para proventos pagos no dia."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.clock import SYSTEM_CLOCK, Clock
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.canonical_dividend_entitlement import EntitlementReason
from app.services.canonical_dividend_entitlement_reader import (
    load_portfolio_dividend_entitlements,
)
from app.services.email_service import send_dividend_payment_summary_email

logger = logging.getLogger(__name__)

_IDEMPOTENCY_TTL_SECONDS = 48 * 3600


async def _was_already_sent(user_id: int, payment_date: date) -> bool:
    client = await get_redis()
    if not client:
        return False
    key = f"sgi:dividend_email_sent:{user_id}:{payment_date.isoformat()}"
    try:
        return bool(await client.get(key))
    except Exception:
        return False


async def _mark_sent(user_id: int, payment_date: date) -> None:
    client = await get_redis()
    if not client:
        return
    key = f"sgi:dividend_email_sent:{user_id}:{payment_date.isoformat()}"
    try:
        await client.set(key, "1", ex=_IDEMPOTENCY_TTL_SECONDS)
    except Exception as exc:
        logger.warning("[dividend_notify] falha ao gravar idempotência no Redis: %s", exc)


async def notify_daily_dividend_payments(
    db: AsyncSession,
    *,
    target_date: date | None = None,
    force: bool = False,
    clock: Clock = SYSTEM_CLOCK,
) -> dict:
    """Busca proventos com payment_date == target_date e envia resumo por usuário."""
    day = target_date or clock.today()
    day_br = day.strftime("%d/%m/%Y")

    users_result = await db.execute(
        select(User).where(User.is_active.is_(True)).order_by(User.id)
    )
    users = list(users_result.scalars().all())

    users_with_payments = 0
    emails_sent = 0
    skipped_already_sent = 0
    errors = 0

    for user in users:
        if not user.email or not user.email.strip():
            continue

        portfolios_result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id).order_by(Portfolio.id)
        )
        portfolios = list(portfolios_result.scalars().all())
        if not portfolios:
            continue

        user_items: list[dict] = []
        total_net = Decimal("0")

        for portfolio in portfolios:
            entitlements = await load_portfolio_dividend_entitlements(db, portfolio.id)
            for item in entitlements:
                if (
                    item.entitlement.reason is EntitlementReason.ELIGIBLE
                    and item.event.payment_date == day
                    and item.entitlement.net_amount > 0
                ):
                    net_val = Decimal(str(item.entitlement.net_amount))
                    total_net += net_val
                    user_items.append(
                        {
                            "ticker": item.ticker,
                            "event_type": str(getattr(item.event.event_type, "value", item.event.event_type)),
                            "portfolio_name": portfolio.name,
                            "net_amount": float(net_val),
                        }
                    )

        if not user_items:
            continue

        users_with_payments += 1
        if not force and await _was_already_sent(user.id, day):
            skipped_already_sent += 1
            continue

        try:
            ok = await send_dividend_payment_summary_email(
                to_email=user.email,
                name=user.name or user.email.split("@")[0],
                payment_date_str=day_br,
                items=user_items,
                total_net_brl=float(total_net),
            )
            if ok:
                emails_sent += 1
                await _mark_sent(user.id, day)
            else:
                errors += 1
        except Exception as exc:
            errors += 1
            logger.error(
                "[dividend_notify] erro ao enviar proventos para user_id=%s: %s",
                user.id,
                exc,
            )

    summary = {
        "payment_date": day.isoformat(),
        "users_checked": len(users),
        "users_with_payments": users_with_payments,
        "emails_sent": emails_sent,
        "skipped_already_sent": skipped_already_sent,
        "errors": errors,
    }
    logger.info("[dividend_notify] resumo %s", summary)
    return summary
