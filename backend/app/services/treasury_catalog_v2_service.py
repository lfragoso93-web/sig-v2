"""Sincronizacao do catalogo oficial do Tesouro Direto via Tesouro Transparente.

O Catalog v2 usa o CSV oficial como fonte de verdade. Ativos existentes que nao
aparecem no catalogo nao sao removidos: recebem status de revisao para preservar
transacoes e historicos legados.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tesouro_transparente import (
    _canonical_symbol,
    _first,
    _legacy_maturity_symbol,
    discover_csv_resources,
)
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)

_OFFICIAL_PROVIDER = "tesouro_transparente"
_REVIEW_STATUS = "NOT_APPLICABLE"
_REVIEW_REASON = "Fora do catalogo oficial atual do Tesouro Transparente; revisar alias ou titulo legado"
_MATURITY_ALIAS_REASON = "Alias legado baseado no ano de vencimento; historico migrado para o ano comercial"


@dataclass
class TreasuryCatalogV2Result:
    official_titles: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    review_marked: int = 0
    legacy_aliases: int = 0
    maturity_aliases: int = 0
    migrated_prices: int = 0
    resources: int = 0
    errors: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def _catalog_rows(text: str) -> dict[str, dict[str, str]]:
    sample = text[:8192]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    catalog: dict[str, dict[str, str]] = {}
    for row in reader:
        title = _first(row, "Tipo Titulo", "Tipo Título", "Titulo", "Título", "Nome")
        maturity = _first(row, "Data Vencimento", "Vencimento")
        symbol = _canonical_symbol(title, maturity)
        if not symbol:
            continue
        catalog[symbol] = {
            "symbol": symbol,
            "legacy_maturity_symbol": _legacy_maturity_symbol(title, maturity) or "",
            "name": f"{title.strip()} {maturity.strip()}".strip(),
            "title": title.strip(),
            "maturity": maturity.strip(),
        }
    return catalog


async def fetch_official_treasury_catalog() -> dict[str, dict[str, str]]:
    """Baixa e consolida todos os recursos CSV oficiais descobertos pelo CKAN."""
    merged: dict[str, dict[str, str]] = {}
    async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
        resources = await discover_csv_resources(client)
        for url in resources:
            try:
                response = await client.get(url, timeout=120.0)
                response.raise_for_status()
                merged.update(_catalog_rows(response.text))
            except Exception as exc:
                logger.warning("[treasury_catalog_v2] falha recurso=%s erro=%s", url, exc)
    return merged


async def _migrate_asset_prices(
    db: AsyncSession,
    source_asset_id: int,
    target_asset_id: int,
) -> int:
    """Move histórico de um alias para o ativo canônico com upsert idempotente."""
    if source_asset_id == target_asset_id:
        return 0
    rows = await db.execute(
        select(AssetPrice).where(AssetPrice.asset_id == source_asset_id)
    )
    prices = list(rows.scalars().all())
    for price in prices:
        stmt = (
            pg_insert(AssetPrice)
            .values(
                asset_id=target_asset_id,
                timestamp=price.timestamp,
                open=price.open,
                high=price.high,
                low=price.low,
                close=price.close,
                volume=price.volume,
                source=price.source,
            )
            .on_conflict_do_update(
                constraint="uq_price_asset_timestamp",
                set_={
                    "open": price.open,
                    "high": price.high,
                    "low": price.low,
                    "close": price.close,
                    "volume": price.volume,
                    "source": price.source,
                },
            )
        )
        await db.execute(stmt)
    if prices:
        await db.execute(delete(AssetPrice).where(AssetPrice.asset_id == source_asset_id))
    return len(prices)


async def sync_treasury_catalog_v2(
    db: AsyncSession,
    *,
    commit: bool = True,
) -> TreasuryCatalogV2Result:
    """Sincroniza assets oficiais e marca, sem excluir, registros fora do catalogo."""
    result = TreasuryCatalogV2Result()
    try:
        official = await fetch_official_treasury_catalog()
    except Exception:
        logger.exception("[treasury_catalog_v2] falha ao carregar catalogo oficial")
        result.errors += 1
        return result

    result.official_titles = len(official)
    if not official:
        result.errors += 1
        return result

    rows = await db.execute(
        select(Asset).where(Asset.asset_type == AssetType.TESOURO_DIRETO.value)
    )
    assets = list(rows.scalars().all())
    by_exact = {str(asset.ticker or ""): asset for asset in assets}
    official_symbols = set(official)
    now = datetime.now(timezone.utc)
    maturity_alias_ids: set[int] = set()

    for symbol, item in official.items():
        asset = by_exact.get(symbol)
        if asset is None:
            asset = Asset(
                ticker=symbol,
                name=item["name"],
                asset_type=AssetType.TESOURO_DIRETO.value,
                currency="BRL",
                sector="Tesouro Direto | fonte=tesouro_transparente",
                provider=_OFFICIAL_PROVIDER,
                provider_symbol=symbol,
                provider_status="OK",
                provider_last_sync_at=now,
            )
            db.add(asset)
            await db.flush()
            by_exact[symbol] = asset
            assets.append(asset)
            result.created += 1
        else:
            changed = False
            expected = {
                "name": item["name"],
                "currency": "BRL",
                "provider": _OFFICIAL_PROVIDER,
                "provider_symbol": symbol,
                "provider_status": "OK",
                "provider_last_error": None,
            }
            for field, value in expected.items():
                if getattr(asset, field, None) != value:
                    setattr(asset, field, value)
                    changed = True
            asset.provider_last_sync_at = now
            if changed:
                result.updated += 1
            else:
                result.unchanged += 1

        legacy_symbol = item.get("legacy_maturity_symbol") or ""
        legacy_asset = by_exact.get(legacy_symbol) if legacy_symbol and legacy_symbol != symbol else None
        if legacy_asset is not None and int(legacy_asset.id) != int(asset.id):
            result.migrated_prices += await _migrate_asset_prices(
                db,
                int(legacy_asset.id),
                int(asset.id),
            )
            legacy_asset.provider_status = _REVIEW_STATUS
            legacy_asset.provider_last_error = _MATURITY_ALIAS_REASON
            legacy_asset.provider_last_sync_at = now
            maturity_alias_ids.add(int(legacy_asset.id))
            result.maturity_aliases += 1

    for asset in assets:
        if int(asset.id) in maturity_alias_ids:
            continue
        ticker = str(asset.ticker or "").strip()
        lower = ticker.lower()
        if ticker in official_symbols:
            continue
        if lower in official_symbols:
            result.legacy_aliases += 1
        if asset.provider_status != _REVIEW_STATUS or asset.provider_last_error != _REVIEW_REASON:
            asset.provider_status = _REVIEW_STATUS
            asset.provider_last_error = _REVIEW_REASON
            asset.provider_last_sync_at = now
            result.review_marked += 1

    if commit:
        await db.commit()

    logger.info(
        "[treasury_catalog_v2] official=%d created=%d updated=%d unchanged=%d review=%d aliases=%d maturity_aliases=%d migrated_prices=%d errors=%d",
        result.official_titles,
        result.created,
        result.updated,
        result.unchanged,
        result.review_marked,
        result.legacy_aliases,
        result.maturity_aliases,
        result.migrated_prices,
        result.errors,
    )
    return result
