"""
rate_history_job.py

Job agendado para atualizar o historico de taxas diariamente.
Roda uma vez ao dia apos o fechamento do mercado (20:00 BRT = 23:00 UTC).
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import text

if TYPE_CHECKING:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.database import AsyncSessionLocal

log = logging.getLogger(__name__)

BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"

INDICADORES = {
    "CDI":   {"serie": 12,  "granularity": "daily"},
    "SELIC": {"serie": 11,  "granularity": "daily"},
    "IPCA":  {"serie": 433, "granularity": "monthly"},
}

UPSERT_SQL = text("""
    INSERT INTO rate_history (indicator, date, rate_daily, rate_monthly, rate_annual, source)
    VALUES (:indicator, :date, :rate_daily, :rate_monthly, :rate_annual, :source)
    ON CONFLICT (indicator, date)
    DO UPDATE SET
        rate_daily   = EXCLUDED.rate_daily,
        rate_monthly = EXCLUDED.rate_monthly,
        rate_annual  = EXCLUDED.rate_annual,
        source       = EXCLUDED.source
""")


def _daily_to_monthly(d: float) -> float:
    return ((1 + d / 100) ** 21 - 1) * 100


def _daily_to_annual(d: float) -> float:
    return ((1 + d / 100) ** 252 - 1) * 100


def _monthly_to_daily(m: float) -> float:
    return ((1 + m / 100) ** (1 / 21) - 1) * 100


def _monthly_to_annual(m: float) -> float:
    return ((1 + m / 100) ** 12 - 1) * 100


async def _fetch_today(indicator: str, cfg: dict) -> list[dict] | None:
    today = date.today()
    url = BCB_SGS_URL.format(serie=cfg["serie"])
    params = {
        "formato": "json",
        "dataInicial": today.strftime("%d/%m/%Y"),
        "dataFinal": today.strftime("%d/%m/%Y"),
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.warning("[rate_job] BCB %s falhou: %s", indicator, e)
        return None


async def update_rates_today() -> None:
    """
    Busca e grava as taxas do dia atual para CDI, SELIC e IPCA.
    """
    log.info("[rate_job] Atualizando taxas do dia %s ...", date.today())
    rows_to_insert: list[dict] = []

    for indicator, cfg in INDICADORES.items():
        raw = await _fetch_today(indicator, cfg)
        if not raw:
            log.warning("[rate_job] Sem dados para %s hoje", indicator)
            continue

        for item in raw:
            try:
                ref_date = datetime.strptime(item["data"], "%d/%m/%Y").date()
                val = float(item["valor"].replace(",", "."))
            except (KeyError, ValueError):
                continue

            if cfg["granularity"] == "daily":
                rd, rm, ra = val, _daily_to_monthly(val), _daily_to_annual(val)
            else:
                ref_date = ref_date.replace(day=1)
                rd, rm, ra = _monthly_to_daily(val), val, _monthly_to_annual(val)

            rows_to_insert.append({
                "indicator": indicator,
                "date": ref_date,
                "rate_daily": Decimal(str(round(rd, 8))),
                "rate_monthly": Decimal(str(round(rm, 8))),
                "rate_annual": Decimal(str(round(ra, 4))),
                "source": "BCB",
            })

    if not rows_to_insert:
        log.warning("[rate_job] Nenhuma taxa coletada hoje")
        return

    async with AsyncSessionLocal() as session:
        await session.execute(UPSERT_SQL, rows_to_insert)
        await session.commit()

    log.info("[rate_job] %d taxas gravadas/atualizadas", len(rows_to_insert))


def register_rate_history_job(scheduler: "AsyncIOScheduler") -> None:
    scheduler.add_job(
        update_rates_today,
        trigger="cron",
        hour=23,
        minute=0,
        id="update_rate_history",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    log.info("[rate_job] Job 'update_rate_history' registrado (diario 23:00 UTC)")
