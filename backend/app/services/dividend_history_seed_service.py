"""Complemento histórico para o seed de proventos.

A BRAPI e a B3 permanecem como fontes principais dos eventos corporativos ricos.
Este serviço usa Yahoo Finance para preencher datas retroativas (anteriores à
janela principal) ou lacunas de cobertura sem sobrepor eventos já persistidos.
"""

from __future__ import annotations

import asyncio
import logging
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType

logger = logging.getLogger(__name__)

SKIP_TYPES = {"CRIPTO", "TESOURO_DIRETO", "RENDA_FIXA"}
NATIONAL_TYPES = {"ACAO", "FII", "ETF_NACIONAL", "BDR"}

_UNAVAILABLE_TTL_SECONDS = 24 * 60 * 60
_unavailable_symbols: dict[str, float] = {}


def _yf_symbol(ticker: str, asset_type: str) -> str:
    ticker = ticker.upper().strip()
    if asset_type.upper() in NATIONAL_TYPES and not ticker.endswith(".SA"):
        return f"{ticker}.SA"
    return ticker


def _event_type(asset_type: str) -> DividendType:
    return (
        DividendType.RENDIMENTO
        if asset_type.upper() == "FII"
        else DividendType.DIVIDENDO
    )


def _is_symbol_unavailable(symbol: str) -> bool:
    expires_at = _unavailable_symbols.get(symbol)
    if expires_at is None:
        return False
    if time.monotonic() >= expires_at:
        _unavailable_symbols.pop(symbol, None)
        return False
    return True


def _mark_symbol_unavailable(symbol: str) -> None:
    _unavailable_symbols[symbol] = time.monotonic() + _UNAVAILABLE_TTL_SECONDS


async def _fetch_full_history(ticker: str, asset_type: str) -> list[tuple[date, float]]:
    """Busca dividendos desde 1970 via Yahoo Finance."""
    symbol = _yf_symbol(ticker, asset_type)
    if _is_symbol_unavailable(symbol):
        logger.debug(
            "[dividend_history] %s em cooldown por indisponibilidade no Yahoo", symbol
        )
        return []

    def _sync() -> list[tuple[date, float]]:
        import yfinance as yf

        yf_logger = logging.getLogger("yfinance")
        previous_level = yf_logger.level
        previous_disabled = yf_logger.disabled
        yf_logger.setLevel(logging.CRITICAL)
        yf_logger.disabled = True
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                history = yf.Ticker(symbol).history(
                    start="1970-01-01",
                    end=(date.today() + timedelta(days=1)).isoformat(),
                    actions=True,
                    auto_adjust=False,
                    raise_errors=False,
                )
        finally:
            yf_logger.setLevel(previous_level)
            yf_logger.disabled = previous_disabled

        if history.empty or "Dividends" not in history.columns:
            return []

        rows: list[tuple[date, float]] = []
        for timestamp, value in history["Dividends"].items():
            amount = float(value or 0)
            if amount <= 0:
                continue
            event_date = (
                timestamp.date()
                if hasattr(timestamp, "date")
                else date.fromisoformat(str(timestamp)[:10])
            )
            rows.append((event_date, amount))
        return rows

    loop = asyncio.get_running_loop()
    try:
        with ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="dividend_history"
        ) as pool:
            rows = await loop.run_in_executor(pool, _sync)
    except Exception as exc:
        _mark_symbol_unavailable(symbol)
        logger.debug("[dividend_history] %s indisponível no Yahoo: %s", symbol, exc)
        return []

    if not rows:
        _mark_symbol_unavailable(symbol)
        logger.debug(
            "[dividend_history] %s sem histórico no Yahoo; cooldown aplicado", symbol
        )
    return rows


def _has_nearby_existing_date(
    event_date: date,
    existing_dates: set[date],
    tolerance_days: int = 5,
) -> bool:
    for d in existing_dates:
        if abs((d - event_date).days) <= tolerance_days:
            return True
    return False


async def seed_full_dividend_history(
    db: AsyncSession,
    ticker: str,
    asset_type: str,
) -> int:
    """Persiste o histórico global retroativo e complementar de proventos."""
    ticker = ticker.upper().strip()
    asset_type = asset_type.upper().strip()
    if not ticker or asset_type in SKIP_TYPES:
        return 0

    asset_result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        return 0

    existing_rows = (
        await db.execute(
            select(AssetDividend.ex_date, AssetDividend.record_date).where(
                AssetDividend.asset_id == asset.id
            )
        )
    ).all()
    existing_dates: set[date] = set()
    for ex_d, rec_d in existing_rows:
        if ex_d is not None:
            existing_dates.add(ex_d)
        if rec_d is not None:
            existing_dates.add(rec_d)

    history = await _fetch_full_history(ticker, asset_type)
    if not history:
        return 0

    dividend_type = _event_type(asset_type)
    inserted = 0

    for event_date, amount in history:
        if _has_nearby_existing_date(event_date, existing_dates):
            continue

        stmt = (
            pg_insert(AssetDividend)
            .values(
                asset_id=asset.id,
                record_date=None,
                ex_date=event_date,
                payment_date=event_date,
                value_per_unit=Decimal(str(round(amount, 8))),
                dividend_type=dividend_type,
                source="yfinance_history",
                raw_payload={
                    "source": "yfinance",
                    "symbol": _yf_symbol(ticker, asset_type),
                    "historical_seed": True,
                },
            )
            .on_conflict_do_nothing()
        )
        result = await db.execute(stmt)
        if result.rowcount and result.rowcount > 0:
            inserted += 1
            existing_dates.add(event_date)

    if inserted:
        await db.flush()
        await db.commit()
        logger.info(
            "[dividend_history] %s: %s eventos históricos globais inseridos",
            ticker,
            inserted,
        )
    else:
        await db.rollback()
        logger.debug("[dividend_history] %s já estava atualizado", ticker)

    return inserted
