"""Reconstrução do histórico do Tesouro com fonte oficial primária.

Ordem de coleta:
1. Tesouro Transparente/CKAN (dados oficiais);
2. BRAPI somente para símbolos sem cobertura oficial.

Aliases legados são resolvidos para um único ativo canônico antes da coleta. Nenhum
registro antigo é removido por esta rotina.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.integrations.brapi_treasury import fetch_treasury_history, is_brapi_treasury_symbol
from app.integrations.tesouro_transparente import fetch_official_treasury_history
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.asset_last_price_refresh_service import refresh_asset_last_prices
from app.services.treasury_catalog_service import resolve_treasury_symbol
from app.services.treasury_history_rebuild_service import _last_saved_date

logger = logging.getLogger(__name__)

_OFFICIAL_SOURCE = "tesouro_transparente"
_FALLBACK_SOURCE = "brapi_treasury"
_DEFAULT_YEARS = 10
_LOOKBACK_DAYS = 10
_INACTIVE_STATUS = "NOT_APPLICABLE"


async def _persist_history_rows(db, asset_id: int, rows: list[tuple[datetime, float]], source: str) -> int:
    changed = 0
    for timestamp, close in rows:
        value = Decimal(str(round(close, 8)))
        stmt = (
            pg_insert(AssetPrice)
            .values(asset_id=asset_id, timestamp=timestamp, close=value, source=source)
            .on_conflict_do_update(
                constraint="uq_price_asset_timestamp",
                set_={"close": value, "source": source},
            )
        )
        await db.execute(stmt)
        changed += 1
    return changed


async def _canonical_assets(db) -> tuple[dict[str, Asset], dict[str, list[str]], list[str]]:
    result = await db.execute(
        select(Asset).where(
            Asset.asset_type == AssetType.TESOURO_DIRETO.value,
            Asset.provider_status != _INACTIVE_STATUS,
        )
    )
    assets = list(result.scalars().all())
    exact = {
        str(asset.ticker or "").strip(): asset
        for asset in assets
        if asset.ticker and str(asset.ticker).strip() == str(asset.ticker).strip().lower()
    }

    grouped: dict[str, list[Asset]] = defaultdict(list)
    unresolved: list[str] = []
    for asset in assets:
        ticker = str(asset.ticker or "").strip()
        canonical = await resolve_treasury_symbol(db, ticker)
        if not canonical:
            unresolved.append(ticker)
            continue
        grouped[canonical.lower()].append(asset)

    selected: dict[str, Asset] = {}
    aliases: dict[str, list[str]] = {}
    for canonical, candidates in grouped.items():
        canonical_asset = exact.get(canonical)
        if canonical_asset is None:
            canonical_asset = max(
                candidates,
                key=lambda item: (
                    str(item.ticker or "").strip() == canonical,
                    bool(getattr(item, "last_price_updated_at", None)),
                    -int(item.id),
                ),
            )
        selected[canonical] = canonical_asset
        aliases[canonical] = sorted(
            {
                str(item.ticker or "").strip()
                for item in candidates
                if str(item.ticker or "").strip() != canonical
            }
        )
    return selected, aliases, sorted(set(unresolved))


async def rebuild_official_treasury_history() -> dict[str, object]:
    today = date.today()

    async with AsyncSessionLocal() as db:
        assets_by_symbol, aliases_by_symbol, unresolved_assets = await _canonical_assets(db)
        if not assets_by_symbol:
            logger.warning("[treasury_history_official] nenhum ativo canônico de Tesouro cadastrado")
            return {
                "official_symbols": 0,
                "matched_assets": 0,
                "imported": 0,
                "official_imported": 0,
                "fallback_imported": 0,
                "official_covered": 0,
                "fallback_symbols": 0,
                "empty_payloads": 0,
                "last_prices_refreshed": 0,
                "alias_groups": 0,
                "unresolved_assets": unresolved_assets,
                "history": {},
            }

        windows: dict[tuple[date, date], list[str]] = defaultdict(list)
        for symbol, asset in assets_by_symbol.items():
            last_date = await _last_saved_date(db, int(asset.id))
            start = today - timedelta(days=_DEFAULT_YEARS * 365)
            if last_date:
                start = max(last_date - timedelta(days=2), today - timedelta(days=_LOOKBACK_DAYS))
            windows[(start, today)].append(symbol)

        stats = {symbol: 0 for symbol in assets_by_symbol}
        source_stats = {_OFFICIAL_SOURCE: 0, _FALLBACK_SOURCE: 0}
        official_covered_symbols: set[str] = set()
        fallback_requested_symbols: set[str] = set()
        touched_asset_ids: set[int] = set()
        empty_payloads = 0

        for (start, end), symbols in windows.items():
            unique_symbols = sorted(set(symbols))
            official_history = await fetch_official_treasury_history(
                unique_symbols,
                start_date=start,
                end_date=end,
            )

            missing: list[str] = []
            for symbol in unique_symbols:
                rows = official_history.get(symbol) or []
                asset = assets_by_symbol[symbol]
                if rows:
                    count = await _persist_history_rows(db, int(asset.id), rows, _OFFICIAL_SOURCE)
                    stats[symbol] += count
                    source_stats[_OFFICIAL_SOURCE] += count
                    official_covered_symbols.add(symbol)
                    touched_asset_ids.add(int(asset.id))
                else:
                    missing.append(symbol)
            await db.commit()

            brapi_symbols = sorted(
                {
                    symbol
                    for symbol in missing
                    if is_brapi_treasury_symbol(symbol)
                }
            )
            fallback_requested_symbols.update(brapi_symbols)
            if brapi_symbols:
                fallback_history = await fetch_treasury_history(
                    brapi_symbols,
                    start_date=start,
                    end_date=end,
                )
                for symbol in brapi_symbols:
                    rows = fallback_history.get(symbol) or []
                    if not rows:
                        continue
                    asset = assets_by_symbol[symbol]
                    count = await _persist_history_rows(db, int(asset.id), rows, _FALLBACK_SOURCE)
                    stats[symbol] += count
                    source_stats[_FALLBACK_SOURCE] += count
                    touched_asset_ids.add(int(asset.id))
                await db.commit()

            unresolved = [symbol for symbol in missing if not stats.get(symbol)]
            if unresolved:
                empty_payloads += len(unresolved)
                logger.info(
                    "[treasury_history_official] sem histórico após fallback count=%d sample=%s",
                    len(unresolved),
                    unresolved[:5],
                )

        last_prices_refreshed = 0
        if touched_asset_ids:
            last_prices_refreshed = await refresh_asset_last_prices(db, touched_asset_ids)
            await db.commit()

    imported = sum(stats.values())
    alias_groups = sum(1 for aliases in aliases_by_symbol.values() if aliases)
    logger.info(
        "[treasury_history_official] concluido canonical=%d aliases=%d imported=%d official=%d fallback=%d covered=%d empty=%d refreshed=%d",
        len(assets_by_symbol),
        alias_groups,
        imported,
        source_stats[_OFFICIAL_SOURCE],
        source_stats[_FALLBACK_SOURCE],
        len(official_covered_symbols),
        empty_payloads,
        last_prices_refreshed,
    )
    return {
        "official_symbols": len(assets_by_symbol),
        "matched_assets": len(assets_by_symbol),
        "imported": imported,
        "official_imported": source_stats[_OFFICIAL_SOURCE],
        "fallback_imported": source_stats[_FALLBACK_SOURCE],
        "official_covered": len(official_covered_symbols),
        "fallback_symbols": len(fallback_requested_symbols),
        "empty_payloads": empty_payloads,
        "last_prices_refreshed": last_prices_refreshed,
        "primary_source": _OFFICIAL_SOURCE,
        "fallback_source": _FALLBACK_SOURCE,
        "alias_groups": alias_groups,
        "aliases": {key: value for key, value in aliases_by_symbol.items() if value},
        "unresolved_assets": unresolved_assets,
        "history": stats,
    }
