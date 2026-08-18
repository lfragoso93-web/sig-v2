"""Persistência canônica de taxas de câmbio coletadas pelo bootstrap.

Este módulo não consulta provedores e não oferece leitura para requests HTTP.
Consumidores financeiros devem usar os readers DB-first dedicados.
"""
from datetime import date as DateType, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

PAIR_USD_BRL = "USD-BRL"
_RATE_QUANTUM = Decimal("0.00000001")


def _normalize_rate(rate: float | Decimal) -> Decimal:
    return Decimal(str(rate)).quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)


async def persist_usd_brl_rate(
    db: AsyncSession,
    date_str: str,
    rate: float | Decimal,
    *,
    commit: bool = True,
) -> None:
    """Persiste USD/BRL por UPSERT, com controle transacional pelo chamador."""
    try:
        rate_date = DateType.fromisoformat(date_str)
        await db.execute(
            text("""
                INSERT INTO fx_rates (pair, rate_date, rate, created_at)
                VALUES (:pair, :rate_date, :rate, :created_at)
                ON CONFLICT (pair, rate_date)
                DO UPDATE SET rate = EXCLUDED.rate, created_at = EXCLUDED.created_at
            """),
            {
                "pair": PAIR_USD_BRL,
                "rate_date": rate_date,
                "rate": _normalize_rate(rate),
                "created_at": datetime.now(timezone.utc),
            },
        )
        if commit:
            await db.commit()
    except Exception:
        if commit:
            try:
                await db.rollback()
            except Exception:
                pass
        raise
