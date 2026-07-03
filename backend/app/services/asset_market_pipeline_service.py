"""
asset_market_pipeline_service.py

Orquestrador único de dados de mercado por ativo.

Este serviço centraliza o fluxo que antes estava espalhado entre seed,
onboarding, backfill de preços, logo e proventos:

  1. garantir Asset básico no banco;
  2. sincronizar histórico de preços;
  3. preencher logo/metadados faltantes;
  4. sincronizar eventos/proventos globais em AssetDividend;
  5. materializar carteiras reais com posição na Data Com.

O objetivo é que seed, onboarding, cron e comandos manuais chamem a mesma
porta de entrada, reduzindo divergências de comportamento.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import INTL_TYPES, NO_QUOTE_TYPES
from app.integrations.brapi import fetch_fii_historical_v2, fetch_price_history_full, fetch_stocks_historical_v2
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.dividend_backfill_service import materialize_asset_dividends, run_backfill
from app.services.logo_service import fetch_logo_url
from app.services.price_history_service import persist_daily_prices

logger = logging.getLogger(__name__)

_FULL_HISTORY_TYPES = {AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL, AssetType.BDR}
_EVENT_TYPES = {AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL, AssetType.BDR}
_PRICE_HISTORY_DAYS_INTL = 365 * 5
_PRICE_HISTORY_DAYS_FALLBACK_BR = 365 * 80


@dataclass
class AssetMarketPipelineResult:
    ticker: str
    asset_type: str
    asset_created: bool = False
    asset_updated: bool = False
    prices_inserted: int = 0
    logo_updated: bool = False
    events_synced: bool = False
    materialized: int = 0
    skipped_steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _asset_type_from_value(value: AssetType | str) -> AssetType:
    if isinstance(value, AssetType):
        return value
    return AssetType(str(value))


def _currency_for_type(asset_type: AssetType) -> str:
    return "USD" if asset_type in INTL_TYPES else "BRL"


def _to_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


async def _get_or_create_asset(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    *,
    name: str | None = None,
    sector: str | None = None,
    logo_url: str | None = None,
) -> tuple[Asset, bool, bool]:
    result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type.value)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = Asset(
            ticker=ticker,
            name=name or ticker,
            asset_type=asset_type.value,
            currency=_currency_for_type(asset_type),
            sector=sector,
            logo_url=logo_url,
        )
        db.add(asset)
        await db.flush()
        return asset, True, False

    updated = False
    if name and (not asset.name or asset.name == asset.ticker):
        asset.name = name
        updated = True
    if sector and not asset.sector:
        asset.sector = sector
        updated = True
    if logo_url and not asset.logo_url:
        asset.logo_url = logo_url
        updated = True
    if not asset.currency:
        asset.currency = _currency_for_type(asset_type)
        updated = True
    if updated:
        await db.flush()
    return asset, False, updated


async def _upsert_price(db: AsyncSession, asset_id: int, timestamp: datetime, close: float, source: str) -> None:
    stmt = (
        pg_insert(AssetPrice)
        .values(
            asset_id=asset_id,
            timestamp=timestamp,
            close=Decimal(str(round(float(close), 8))),
            source=source,
        )
        .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
    )
    await db.execute(stmt)


async def _persist_full_br_history(db: AsyncSession, asset: Asset, asset_type: AssetType) -> int:
    ticker = asset.ticker.upper()
    rows: list[tuple[datetime, float]] = []
    source = "brapi_range_max"

    if asset_type == AssetType.FII:
        rows = await fetch_fii_historical_v2(ticker=ticker, range_="max")
        source = "brapi_v2_fii_range_max"
    elif asset_type in {AssetType.ACAO, AssetType.ETF_NACIONAL, AssetType.BDR}:
        rows = await fetch_stocks_historical_v2(ticker=ticker, range_="max")
        source = "brapi_v2_stocks_range_max"

    # Fallback para quote range=max usado em fluxos antigos. Mantemos para
    # ativos que a rota v2/historical não cobre, especialmente units/BDRs.
    if not rows:
        rows = await fetch_price_history_full(ticker)
        source = "brapi_quote_range_max"

    if not rows:
        return 0

    inserted = 0
    for dt, close in rows:
        if close and float(close) > 0:
            await _upsert_price(db, asset.id, _to_utc_datetime(dt), float(close), source)
            inserted += 1

    if inserted:
        latest_close = float(rows[-1][1])
        asset.last_price = Decimal(str(round(latest_close, 8)))
        asset.last_price_updated_at = datetime.now(timezone.utc)
        await db.flush()
    return inserted


async def _sync_prices(db: AsyncSession, asset: Asset, asset_type: AssetType, *, full: bool) -> int:
    if asset_type in NO_QUOTE_TYPES:
        return 0
    if full and asset_type in _FULL_HISTORY_TYPES:
        return await _persist_full_br_history(db, asset, asset_type)
    if asset_type in INTL_TYPES:
        return await persist_daily_prices(db, asset.ticker, asset_type, days_back=_PRICE_HISTORY_DAYS_INTL, force=True)
    return await persist_daily_prices(db, asset.ticker, asset_type, days_back=_PRICE_HISTORY_DAYS_FALLBACK_BR, force=True)


async def _sync_logo(db: AsyncSession, asset: Asset, asset_type: AssetType) -> bool:
    if asset.logo_url:
        return False
    logo = await fetch_logo_url(asset.ticker, asset_type)
    if not logo:
        return False
    asset.logo_url = logo
    await db.flush()
    return True


async def sync_asset_market_data(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType | str,
    *,
    name: str | None = None,
    sector: str | None = None,
    logo_url: str | None = None,
    full: bool = True,
    sync_prices: bool = True,
    sync_logo: bool = True,
    sync_events: bool = True,
    materialize: bool = True,
    commit: bool = True,
) -> AssetMarketPipelineResult:
    """Executa o pipeline único de mercado para um ativo."""
    t = ticker.upper().strip()
    at = _asset_type_from_value(asset_type)
    result = AssetMarketPipelineResult(ticker=t, asset_type=at.value)

    try:
        asset, created, updated = await _get_or_create_asset(
            db,
            t,
            at,
            name=name,
            sector=sector,
            logo_url=logo_url,
        )
        result.asset_created = created
        result.asset_updated = updated

        if at in NO_QUOTE_TYPES:
            result.skipped_steps.append("market_data_no_quote_type")
        else:
            if sync_prices:
                result.prices_inserted = await _sync_prices(db, asset, at, full=full)
            else:
                result.skipped_steps.append("prices")

            if sync_logo:
                result.logo_updated = await _sync_logo(db, asset, at)
            else:
                result.skipped_steps.append("logo")

            if sync_events and at in _EVENT_TYPES:
                await run_backfill(db, t, at)
                result.events_synced = True
            elif sync_events:
                result.skipped_steps.append("events_not_supported_for_type")
            else:
                result.skipped_steps.append("events")

            if materialize and at in _EVENT_TYPES:
                result.materialized = await materialize_asset_dividends(db=db, tickers=[t], commit=False)
            elif materialize:
                result.skipped_steps.append("materialize_not_supported_for_type")

        if commit:
            await db.commit()
        else:
            await db.flush()
    except Exception as exc:
        await db.rollback()
        result.errors.append(str(exc))
        logger.error("[market_pipeline] erro em %s/%s: %s", t, at.value, exc)
        raise

    logger.info(
        "[market_pipeline] %s/%s ok: created=%s updated=%s prices=%s logo=%s events=%s materialized=%s skipped=%s",
        result.ticker,
        result.asset_type,
        result.asset_created,
        result.asset_updated,
        result.prices_inserted,
        result.logo_updated,
        result.events_synced,
        result.materialized,
        result.skipped_steps,
    )
    return result
