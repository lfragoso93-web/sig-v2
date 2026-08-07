"""Resolvedor pontual de lacuna de cotação por data.

Este é o único caminho de exceção ao runtime DB-first para preço histórico:
1. lê primeiro pelo `get_price_at_date()` puro;
2. se houver cobertura, retorna sem provider;
3. se faltar cobertura, consulta somente a janela mínima de até 5 dias;
4. persiste em `asset_prices`;
5. refaz a leitura DB-first e retorna o valor persistido.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import INTL_TYPES, NO_QUOTE_TYPES, yf_ticker
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.asset_price_gap_sync_service import normalize_provider_symbol
from app.services.price_history_service import _run_yf_with_throttle, get_price_at_date

logger = logging.getLogger(__name__)

POINT_GAP_LOOKBACK_DAYS = 5


def _parse_target_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def _bounded_window(target: date) -> tuple[date, date]:
    return target - timedelta(days=POINT_GAP_LOOKBACK_DAYS), target


def _yf_history_sync(symbol: str, start: date, end: date) -> list[tuple[datetime, float]]:
    history = yf.Ticker(symbol).history(
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        interval="1d",
        auto_adjust=True,
    )
    if history.empty:
        return []
    rows: list[tuple[datetime, float]] = []
    for timestamp, row in history.iterrows():
        close = row.get("Close")
        if close is None:
            continue
        value = float(close)
        if value <= 0:
            continue
        ts = timestamp.to_pydatetime()
        ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
        if start <= ts.date() <= end:
            rows.append((ts, value))
    return rows


async def _fetch_window(
    db: AsyncSession,
    asset: Asset,
    asset_type: AssetType,
    start: date,
    end: date,
) -> tuple[list[tuple[datetime, float]], str]:
    ticker = str(asset.ticker).upper().strip()
    provider_symbol = normalize_provider_symbol(ticker, asset_type)

    if asset_type == AssetType.TESOURO_DIRETO:
        from app.integrations.brapi_treasury import fetch_treasury_history
        from app.services.treasury_catalog_service import resolve_treasury_symbol

        symbol = await resolve_treasury_symbol(db, ticker)
        if not symbol:
            return [], "brapi_treasury"
        history = await fetch_treasury_history([symbol], start, end)
        return list(history.get(symbol.lower(), [])), "brapi_treasury"

    if asset_type in INTL_TYPES or asset_type == AssetType.CRIPTO:
        symbol = yf_ticker(provider_symbol, asset_type)
        rows = await _run_yf_with_throttle(_yf_history_sync, symbol, start, end)
        return rows, "yfinance_point_gap"

    from app.integrations.brapi import fetch_fii_historical_v2, fetch_stocks_historical_v2

    if asset_type == AssetType.FII:
        rows = await fetch_fii_historical_v2(
            ticker=provider_symbol,
            date_from=start.isoformat(),
            date_to=end.isoformat(),
        )
        return rows, "brapi_v2_fii_point_gap"

    rows = await fetch_stocks_historical_v2(
        ticker=provider_symbol,
        date_from=start.isoformat(),
        date_to=end.isoformat(),
    )
    return rows, "brapi_v2_stocks_point_gap"


async def _persist_window(
    db: AsyncSession,
    asset: Asset,
    rows: list[tuple[datetime, float]],
    *,
    source: str,
    start: date,
    end: date,
) -> int:
    inserted = 0
    for timestamp, close in rows:
        ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        ts = ts.astimezone(timezone.utc)
        if not (start <= ts.date() <= end) or close <= 0:
            continue
        stmt = (
            pg_insert(AssetPrice)
            .values(
                asset_id=asset.id,
                timestamp=ts,
                close=Decimal(str(round(float(close), 8))),
                source=source,
            )
            .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
            .returning(AssetPrice.id)
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            inserted += 1
    await db.commit()
    return inserted


async def resolve_price_at_date_gap(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    target_date: str,
) -> Optional[float]:
    """Resolve uma lacuna pontual sem transformar o leitor DB-first em provider client."""
    existing = await get_price_at_date(db, ticker, asset_type, target_date)
    if existing is not None:
        return existing
    if asset_type in NO_QUOTE_TYPES:
        return None

    asset_result = await db.execute(
        select(Asset).where(
            Asset.ticker == ticker,
            Asset.asset_type == asset_type.value,
        )
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        logger.warning(
            "[PriceDateGap] ativo ausente; consulta externa bloqueada ticker=%s type=%s",
            ticker,
            asset_type.value,
        )
        return None

    target = _parse_target_date(target_date)
    start, end = _bounded_window(target)
    rows, source = await _fetch_window(db, asset, asset_type, start, end)
    await _persist_window(db, asset, rows, source=source, start=start, end=end)

    resolved = await get_price_at_date(db, ticker, asset_type, target_date)
    if resolved is None:
        logger.warning(
            "[PriceDateGap] lacuna não resolvida ticker=%s type=%s target=%s window=%s..%s",
            ticker,
            asset_type.value,
            target_date,
            start,
            end,
        )
    return resolved
