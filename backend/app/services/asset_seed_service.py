"""Enriquecimento BRAPI do catálogo persistido e catálogo CRIPTO suportado.

B3 é descoberta pelo COTAHIST. A BRAPI só complementa metadados de ativos B3
já existentes; CRIPTO permanece com catálogo próprio pelo universo suportado.
"""
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_safety import sanitize_log_value
from app.integrations.brapi import fetch_all_tickers_v2
from app.models.asset import Asset, AssetType
from app.services.asset_universe_membership_service import (
    replace_crypto_candidate_memberships,
)
from app.services.crypto_supported_universe_service import (
    fetch_supported_crypto_universe,
)

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

_NO_HISTORY_SUFFIX_RE = re.compile(r"^[A-Z0-9]{4,6}(3|4|5|6|11|31|32|33|34|35)$")


@dataclass
class SeedResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    new_tickers: dict[str, list[str]] = field(default_factory=dict)
    seeded_tickers: dict[str, list[str]] = field(default_factory=dict)


def _extract_logo_url(item: dict) -> str | None:
    raw = (
        item.get("logourl")
        or item.get("logoUrl")
        or item.get("logo_url")
        or item.get("logo")
        or item.get("image")
    )
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


async def _enrich_b3_asset(
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
        return "skipped"
    return await _upsert_asset(db, ticker, name, asset_type, sector, logo_url)


def _has_history(ticker: str) -> bool:
    t = ticker.upper()
    if t.endswith("F") or t[-1:] in {"B", "D", "R"} or t[-2:] in {"97", "98", "99"}:
        return False
    return bool(_NO_HISTORY_SUFFIX_RE.match(t))


async def _run_crypto_seed(db: AsyncSession, result: SeedResult) -> None:
    type_label = AssetType.CRIPTO.value
    result.by_type.setdefault(type_label, 0)
    result.new_tickers.setdefault(type_label, [])
    result.seeded_tickers.setdefault(type_label, [])

    logger.info("[seed] iniciando seed CRIPTO do universo suportado Top 100 por market cap")
    coins = await fetch_supported_crypto_universe()
    logger.info("[seed] universo CRIPTO suportado e disponível na BRAPI: %d", len(coins))

    BATCH_SIZE = 200
    batch_ops = 0
    for item in coins:
        coin = item.ticker
        coin_name = item.name

        try:
            status = await _upsert_asset(db, coin, coin_name, AssetType.CRIPTO, None)
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
        except Exception as e:  # noqa: BLE001 -- seed deve registrar e seguir o próximo ativo
            result.errors += 1
            logger.error(
                "[seed] erro ao upsert cripto %s: %s",
                sanitize_log_value(coin),
                sanitize_log_value(e),
            )

    if batch_ops > 0:
        await db.commit()

    memberships = await replace_crypto_candidate_memberships(db, coins)
    await db.commit()
    logger.info("[seed] associações CRIPTO Top 100 persistidas: %d", memberships)


async def run_asset_seed(
    db: AsyncSession,
    include_crypto: bool = True,
) -> SeedResult:
    result = SeedResult()
    BATCH_SIZE = 200
    batch_ops = 0

    for brapi_subtype, asset_type in _SEED_TYPES:
        type_label = asset_type.value
        result.by_type.setdefault(type_label, 0)
        result.new_tickers.setdefault(type_label, [])
        result.seeded_tickers.setdefault(type_label, [])

        logger.info("[seed] iniciando subtype=%s -> %s", brapi_subtype, type_label)
        items = await fetch_all_tickers_v2(brapi_subtype)
        logger.info(
            "[seed] subtype=%s: %d ativos recebidos da BRAPI",
            brapi_subtype,
            len(items),
        )

        for item in items:
            ticker = (
                item.get("stock") or item.get("symbol") or item.get("ticker") or ""
            ).strip().upper()
            if not ticker:
                result.errors += 1
                continue
            if not _has_history(ticker):
                result.skipped += 1
                logger.info(
                    "[seed] ticker nacional inelegível ignorado: %s (%s)",
                    sanitize_log_value(ticker),
                    type_label,
                )
                continue

            name = (item.get("name") or item.get("longName") or "").strip()
            sector = (
                item.get("sector")
                or item.get("segment")
                or item.get("subSector")
                or ""
            ).strip() or None
            logo_url = _extract_logo_url(item)

            try:
                status = await _enrich_b3_asset(
                    db,
                    ticker,
                    name,
                    asset_type,
                    sector,
                    logo_url,
                )
                result.seeded_tickers[type_label].append(ticker)
                if status == "updated":
                    result.updated += 1
                else:
                    result.skipped += 1

                batch_ops += 1
                if batch_ops >= BATCH_SIZE:
                    await db.commit()
                    batch_ops = 0
            except Exception as e:  # noqa: BLE001 -- seed deve registrar e seguir o próximo ativo
                result.errors += 1
                logger.error(
                    "[seed] erro ao upsert %s (%s): %s",
                    sanitize_log_value(ticker),
                    type_label,
                    sanitize_log_value(e),
                )

    if batch_ops > 0:
        await db.commit()

    if include_crypto:
        await _run_crypto_seed(db, result)

    logger.info(
        "[seed] catálogo concluído: %d criados, %d atualizados, "
        "%d sem mudança, %d erros | por tipo: %s",
        result.created,
        result.updated,
        result.skipped,
        result.errors,
        sanitize_log_value(result.by_type),
    )

    return result
