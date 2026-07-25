"""Reconstrução do histórico do Tesouro com fonte oficial primária.

Ordem de coleta:
1. Tesouro Transparente/CKAN (dados oficiais);
2. BRAPI somente para símbolos sem cobertura oficial.

Aliases legados são resolvidos para um único ativo canônico antes da coleta. Nenhum
registro antigo é removido por esta rotina.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

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
_MATURITY_SUFFIX_PATTERN = re.compile(r"-(\d{2})(\d{2})(\d{4})$")
_MATURITY_YEAR_PATTERN = re.compile(r"-(\d{4})$")


def _maturity_date_from_symbol(symbol: str) -> date | None:
    """Extrai vencimento de símbolos canônicos sem depender de campos adicionais."""
    normalized = str(symbol or "").strip().lower()
    full_match = _MATURITY_SUFFIX_PATTERN.search(normalized)
    if full_match:
        day, month, year = (int(value) for value in full_match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    year_match = _MATURITY_YEAR_PATTERN.search(normalized)
    if year_match:
        return date(int(year_match.group(1)), 12, 31)
    return None


def _classify_empty_symbols(
    symbols: list[str],
    *,
    today: date,
) -> tuple[list[str], list[str]]:
    """Separa ausências bloqueantes de títulos vencidos sem carga incremental."""
    required: list[str] = []
    expected: list[str] = []
    for symbol in sorted(set(symbols)):
        maturity = _maturity_date_from_symbol(symbol)
        if maturity is not None and maturity < today:
            expected.append(symbol)
        else:
            required.append(symbol)
    return required, expected


async def _persist_history_rows(
    db: AsyncSession,
    asset_id: int,
    rows: list[tuple[datetime, float]],
    source: str,
) -> int:
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


async def _canonical_assets(
    db: AsyncSession,
) -> tuple[dict[str, Asset], dict[str, list[str]], list[str]]:
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


async def _rebuild_official_treasury_history(
    db: AsyncSession,
    *,
    commit: bool,
) -> dict[str, object]:
    today = date.today()
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
            "required_empty_payloads": 0,
            "expected_empty_payloads": 0,
            "required_empty_symbols": [],
            "expected_empty_symbols": [],
            "last_prices_refreshed": 0,
            "primary_source": _OFFICIAL_SOURCE,
            "fallback_source": _FALLBACK_SOURCE,
            "alias_groups": 0,
            "aliases": {},
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
    empty_symbols: set[str] = set()

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

        unresolved = [symbol for symbol in missing if not stats.get(symbol)]
        if unresolved:
            empty_symbols.update(unresolved)
            logger.info(
                "[treasury_history_official] sem histórico após fallback count=%d sample=%s",
                len(unresolved),
                unresolved[:5],
            )

    required_empty_symbols, expected_empty_symbols = _classify_empty_symbols(
        list(empty_symbols),
        today=today,
    )

    last_prices_refreshed = 0
    if touched_asset_ids:
        last_prices_refreshed = await refresh_asset_last_prices(db, touched_asset_ids)

    if commit:
        await db.commit()

    imported = sum(stats.values())
    alias_groups = sum(1 for aliases in aliases_by_symbol.values() if aliases)
    logger.info(
        "[treasury_history_official] concluido canonical=%d aliases=%d imported=%d official=%d fallback=%d covered=%d empty=%d required_empty=%d expected_empty=%d refreshed=%d",
        len(assets_by_symbol),
        alias_groups,
        imported,
        source_stats[_OFFICIAL_SOURCE],
        source_stats[_FALLBACK_SOURCE],
        len(official_covered_symbols),
        len(empty_symbols),
        len(required_empty_symbols),
        len(expected_empty_symbols),
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
        "empty_payloads": len(empty_symbols),
        "required_empty_payloads": len(required_empty_symbols),
        "expected_empty_payloads": len(expected_empty_symbols),
        "required_empty_symbols": required_empty_symbols,
        "expected_empty_symbols": expected_empty_symbols,
        "last_prices_refreshed": last_prices_refreshed,
        "primary_source": _OFFICIAL_SOURCE,
        "fallback_source": _FALLBACK_SOURCE,
        "alias_groups": alias_groups,
        "aliases": {key: value for key, value in aliases_by_symbol.items() if value},
        "unresolved_assets": unresolved_assets,
        "history": stats,
    }


async def rebuild_official_treasury_history(
    db: AsyncSession | None = None,
    *,
    commit: bool = True,
) -> dict[str, object]:
    """Reconstrói o histórico usando sessão externa ou uma sessão própria compatível.

    Quando ``db`` é informado, o chamador controla o ciclo de vida da sessão. Com
    ``commit=False``, nenhuma confirmação é executada por este serviço.
    """
    if db is not None:
        return await _rebuild_official_treasury_history(db, commit=commit)

    async with AsyncSessionLocal() as owned_db:
        return await _rebuild_official_treasury_history(owned_db, commit=commit)
