"""
Asset Seed Service.

Popula/atualiza `assets` com todos os ativos listados na B3 via BRAPI v2.

Além do catálogo, o seed executa pipeline idempotente para renda variável nacional:
  1. metadados e logo quando disponível no catálogo
  2. histórico completo de preços diário
  3. logo via cotação quando ausente
  4. histórico global de proventos/eventos corporativos
"""
import asyncio
import logging
import re
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.integrations.brapi import fetch_all_tickers_v2, fetch_crypto_available_all

logger = logging.getLogger(__name__)

_SEED_TYPES: list[tuple[str, AssetType]] = [
    ("stock",    AssetType.ACAO),
    ("unit",     AssetType.ACAO),
    ("fii",      AssetType.FII),
    ("fi-infra", AssetType.FII),
    ("fi-agro",  AssetType.FII),
    ("etf",      AssetType.ETF_NACIONAL),
    ("bdr",      AssetType.BDR),
]

_NO_HISTORY_SUFFIX_RE = re.compile(r"^[A-Z]{4}\d+[FRBD]$")
BACKFILL_CONCURRENCY = 3
BACKFILL_BATCH_DELAY = 2.0
BACKFILL_DAYS = 365 * 80


@dataclass
class SeedResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    new_tickers: dict[str, list[str]] = field(default_factory=dict)
    seeded_tickers: dict[str, list[str]] = field(default_factory=dict)
    skipped_backfill: int = 0


def _extract_logo_url(item: dict) -> str | None:
    raw = item.get("logourl") or item.get("logoUrl") or item.get("logo_url") or item.get("logo") or item.get("image")
    return str(raw).strip() if raw else None


async def _upsert_asset(
    db: AsyncSession,
    ticker: str,
    name: str,
    asset_type: AssetType,
    sector: str | None,
    logo_url: str | None = None,
) -> str:
    result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type.value)
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        db.add(Asset(
            ticker=ticker,
            name=name or ticker,
            asset_type=asset_type.value,
            currency="BRL",
            sector=sector,
            logo_url=logo_url,
        ))
        return "created"

    changed = False
    if not existing.name and name:
        existing.name = name
        changed = True
    if not existing.sector and sector:
        existing.sector = sector
        changed = True
    if not existing.logo_url and logo_url:
        existing.logo_url = logo_url
        changed = True
    return "updated" if changed else "skipped"


def _has_history(ticker: str) -> bool:
    return not _NO_HISTORY_SUFFIX_RE.match(ticker)


async def _ensure_logo_if_missing(db: AsyncSession, ticker: str, asset_type: AssetType) -> None:
    from app.services.logo_service import fetch_logo_url

    result = await db.execute(select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type.value))
    asset = result.scalar_one_or_none()
    if not asset or asset.logo_url:
        return

    logo = await fetch_logo_url(ticker, asset_type)
    if logo:
        asset.logo_url = logo
        await db.commit()
        logger.info(f"[seed_market] {ticker}: logo salva via fallback")


async def _backfill_market_data_for_ticker(ticker: str, asset_type: AssetType) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.price_history_service import persist_daily_prices
    from app.services.dividend_backfill_service import run_backfill

    try:
        async with AsyncSessionLocal() as db:
            inserted = await persist_daily_prices(
                db=db,
                ticker=ticker,
                asset_type=asset_type,
                days_back=BACKFILL_DAYS,
                force=True,
            )
            logger.info(f"[seed_market] {ticker} ({asset_type.value}): {inserted} preços persistidos")

            await _ensure_logo_if_missing(db, ticker, asset_type)
            await run_backfill(db, ticker, asset_type)
            logger.info(f"[seed_market] {ticker} ({asset_type.value}): proventos sincronizados")
    except Exception as e:
        logger.error(f"[seed_market] erro em {ticker} ({asset_type.value}): {e}")


async def _run_market_backfill(seeded_tickers: dict[str, list[str]]) -> int:
    tasks: list[tuple[str, AssetType]] = []
    filtered = 0

    for type_value, tickers in seeded_tickers.items():
        if type_value == AssetType.CRIPTO.value:
            continue
        try:
            at = AssetType(type_value)
        except ValueError:
            continue
        for t in sorted(set(tickers)):
            if _has_history(t):
                tasks.append((t, at))
            else:
                filtered += 1

    if filtered:
        logger.info(f"[seed_market] {filtered} tickers sem histórico ignorados (sufixos F/R/B/D)")
    if not tasks:
        logger.info("[seed_market] nenhum ativo elegível para backfill")
        return filtered

    logger.info(
        f"[seed_market] iniciando pipeline de {len(tasks)} ativos "
        f"(lotes de {BACKFILL_CONCURRENCY}, delay {BACKFILL_BATCH_DELAY}s)"
    )

    total_done = 0
    for i in range(0, len(tasks), BACKFILL_CONCURRENCY):
        batch = tasks[i:i + BACKFILL_CONCURRENCY]
        await asyncio.gather(*[_backfill_market_data_for_ticker(ticker, at) for ticker, at in batch], return_exceptions=True)
        total_done += len(batch)
        if total_done % 20 == 0:
            logger.info(f"[seed_market] {total_done}/{len(tasks)} ativos processados")
        if i + BACKFILL_CONCURRENCY < len(tasks):
            await asyncio.sleep(BACKFILL_BATCH_DELAY)

    logger.info(f"[seed_market] pipeline concluído: {total_done} ativos, {filtered} ignorados")
    return filtered


async def _run_crypto_seed(db: AsyncSession, result: SeedResult) -> None:
    type_label = AssetType.CRIPTO.value
    result.by_type.setdefault(type_label, 0)
    result.new_tickers.setdefault(type_label, [])
    result.seeded_tickers.setdefault(type_label, [])

    logger.info("[seed] iniciando seed de criptomoedas via /api/v2/crypto/available")
    coins = await fetch_crypto_available_all()
    logger.info(f"[seed] criptomoedas recebidas da BRAPI: {len(coins)}")

    BATCH_SIZE = 200
    batch_ops = 0
    for item in coins:
        coin = (item.get("coin") or item.get("symbol") or "").strip().upper()
        if not coin:
            result.errors += 1
            continue
        coin_name = (item.get("coinName") or item.get("name") or item.get("longName") or coin).strip()

        try:
            status = await _upsert_asset(db, coin, coin_name, AssetType.CRIPTO, None, _extract_logo_url(item))
            result.seeded_tickers[type_label].append(coin)
            if status == "created":
                result.created += 1
                result.by_type[type_label] += 1
                result.new_tickers[type_label].append(coin)
            elif status == "updated":
                result.updated += 1
            else:
                result.skipped += 1

            batch_ops += 1
            if batch_ops >= BATCH_SIZE:
                await db.commit()
                batch_ops = 0
        except Exception as e:
            result.errors += 1
            logger.error(f"[seed] erro ao upsert cripto {coin}: {e}")

    if batch_ops > 0:
        await db.commit()


async def run_asset_seed(db: AsyncSession, run_backfill: bool = True) -> SeedResult:
    result = SeedResult()
    BATCH_SIZE = 200
    batch_ops = 0

    for brapi_subtype, asset_type in _SEED_TYPES:
        type_label = asset_type.value
        result.by_type.setdefault(type_label, 0)
        result.new_tickers.setdefault(type_label, [])
        result.seeded_tickers.setdefault(type_label, [])

        logger.info(f"[seed] iniciando subtype={brapi_subtype} -> {type_label}")
        items = await fetch_all_tickers_v2(brapi_subtype)
        logger.info(f"[seed] subtype={brapi_subtype}: {len(items)} ativos recebidos da BRAPI")

        for item in items:
            ticker = (item.get("stock") or item.get("symbol") or item.get("ticker") or "").strip().upper()
            if not ticker:
                result.errors += 1
                continue

            name = (item.get("name") or item.get("longName") or "").strip()
            sector = (item.get("sector") or item.get("segment") or item.get("subSector") or "").strip() or None
            logo_url = _extract_logo_url(item)

            try:
                status = await _upsert_asset(db, ticker, name, asset_type, sector, logo_url)
                result.seeded_tickers[type_label].append(ticker)
                if status == "created":
                    result.created += 1
                    result.by_type[type_label] += 1
                    result.new_tickers[type_label].append(ticker)
                elif status == "updated":
                    result.updated += 1
                else:
                    result.skipped += 1

                batch_ops += 1
                if batch_ops >= BATCH_SIZE:
                    await db.commit()
                    batch_ops = 0
            except Exception as e:
                result.errors += 1
                logger.error(f"[seed] erro ao upsert {ticker} ({type_label}): {e}")

    if batch_ops > 0:
        await db.commit()

    await _run_crypto_seed(db, result)

    logger.info(
        f"[seed] catálogo concluído: {result.created} criados, "
        f"{result.updated} atualizados, {result.skipped} sem mudança, "
        f"{result.errors} erros | por tipo: {result.by_type}"
    )

    if run_backfill:
        result.skipped_backfill = await _run_market_backfill(result.seeded_tickers)
    else:
        logger.info("[seed] run_backfill=False — pipeline de mercado ignorado")

    return result
