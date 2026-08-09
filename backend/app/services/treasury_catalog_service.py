"""
Serviço de catálogo do Tesouro Direto.

Fonte de verdade: tabela assets, populada a partir de fontes públicas do Tesouro
e da BRAPI. Itens sintéticos podem auxiliar a resolução de aliases, mas nunca
são persistidos como novos ativos.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brapi_treasury import (
    canonical_treasury_symbol_from_text,
    fetch_treasury_list,
)
from app.models.asset import Asset, AssetType

logger = logging.getLogger(__name__)

_TREASURY_TYPE = AssetType.TESOURO_DIRETO.value
_SYNTHETIC_SOURCE = "synthetic_treasury_long_term"
_INACTIVE_STATUS = "NOT_APPLICABLE"


@dataclass
class TreasurySeedResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


def normalize_treasury_text(value: str | None) -> str:
    raw = value or ""
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = raw.lower().replace("+", " mais ")
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def slug_from_text(value: str | None) -> str:
    return normalize_treasury_text(value).replace(" ", "-")


def _symbol(item: dict) -> str:
    direct = str(
        item.get("symbol")
        or item.get("slug")
        or item.get("ticker")
        or item.get("id")
        or ""
    ).strip().lower()
    if direct:
        return direct
    return canonical_treasury_symbol_from_text(
        f"{item.get('bondType') or item.get('name') or item.get('title') or ''} "
        f"{item.get('maturityYear') or item.get('maturityDate') or item.get('dueDate') or ''}"
    ) or ""


def _name(item: dict, symbol: str) -> str:
    bond_type = str(item.get("bondType") or item.get("name") or item.get("title") or "").strip()
    maturity_year = item.get("maturityYear")
    maturity = str(item.get("maturityDate") or item.get("dueDate") or item.get("expiresAt") or "").strip()
    if bond_type and maturity_year:
        return f"{bond_type} {maturity_year}"
    if bond_type and maturity:
        return f"{bond_type} {maturity[:10]}"
    return bond_type or symbol


def _sector(item: dict) -> str:
    bits = []
    source = item.get("source")
    indexer = item.get("indexer")
    coupon = item.get("couponType")
    if indexer:
        bits.append(str(indexer).upper())
    if coupon:
        bits.append(f"cupom={coupon}")
    if source:
        bits.append(f"fonte={source}")
    return "Tesouro Direto" + (" | " + " | ".join(bits) if bits else "")


async def seed_treasury_assets(db: AsyncSession, commit: bool = True) -> TreasurySeedResult:
    """Importa/atualiza apenas títulos confirmados por fontes externas reais."""
    result = TreasurySeedResult()
    try:
        items = await fetch_treasury_list()
    except Exception as exc:
        logger.error("[treasury_seed] falha ao buscar catálogo Tesouro: %s", exc)
        result.errors += 1
        return result

    for item in items:
        if str(item.get("source") or "").strip().lower() == _SYNTHETIC_SOURCE:
            result.skipped += 1
            continue

        symbol = _symbol(item)
        if not symbol:
            result.errors += 1
            continue

        name = _name(item, symbol)
        sector = _sector(item)
        try:
            existing_result = await db.execute(
                select(Asset).where(
                    Asset.ticker == symbol,
                    Asset.asset_type == _TREASURY_TYPE,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing is None:
                db.add(
                    Asset(
                        ticker=symbol,
                        name=name,
                        asset_type=_TREASURY_TYPE,
                        currency="BRL",
                        sector=sector,
                    )
                )
                result.created += 1
                continue
            changed = False
            if name and existing.name != name:
                existing.name = name
                changed = True
            if sector and existing.sector != sector:
                existing.sector = sector
                changed = True
            if getattr(existing, "currency", None) != "BRL":
                existing.currency = "BRL"
                changed = True
            if changed:
                result.updated += 1
            else:
                result.skipped += 1
        except Exception as exc:
            logger.error("[treasury_seed] erro ao salvar %s: %s", symbol, exc)
            result.errors += 1

    if commit:
        await db.commit()
    logger.info(
        "[treasury_seed] concluído: %d criados, %d atualizados, %d ignorados, %d erros",
        result.created,
        result.updated,
        result.skipped,
        result.errors,
    )
    return result


async def _treasury_assets(db: AsyncSession, *, active_only: bool = True) -> list[Asset]:
    stmt = select(Asset).where(Asset.asset_type == _TREASURY_TYPE)
    if active_only:
        stmt = stmt.where(func.coalesce(Asset.provider_status, "") != _INACTIVE_STATUS)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def resolve_treasury_symbol(db: AsyncSession, raw: str | None) -> Optional[str]:
    """Resolve texto/ticker usando exclusivamente o catálogo persistido do Tesouro."""
    value = (raw or "").strip()
    if not value:
        return None

    lower = value.lower()
    exact = await db.execute(
        select(Asset.ticker).where(
            Asset.asset_type == _TREASURY_TYPE,
            func.lower(Asset.ticker) == lower,
            func.coalesce(Asset.provider_status, "") != _INACTIVE_STATUS,
        )
    )
    found = exact.scalars().first()
    if found:
        return str(found).lower()

    canonical = canonical_treasury_symbol_from_text(value)
    if canonical:
        canonical_exists = await db.execute(
            select(Asset.ticker).where(
                Asset.asset_type == _TREASURY_TYPE,
                func.lower(Asset.ticker) == canonical.lower(),
                func.coalesce(Asset.provider_status, "") != _INACTIVE_STATUS,
            )
        )
        found = canonical_exists.scalars().first()
        if found:
            return str(found).lower()

    name_exact = await db.execute(
        select(Asset.ticker).where(
            Asset.asset_type == _TREASURY_TYPE,
            Asset.name.ilike(value),
            func.coalesce(Asset.provider_status, "") != _INACTIVE_STATUS,
        )
    )
    found = name_exact.scalars().first()
    if found:
        return str(found).lower()

    assets = await _treasury_assets(db, active_only=True)

    if canonical:
        for asset in assets:
            if str(asset.ticker or "").lower() == canonical.lower():
                return canonical.lower()
        logger.info("[treasury_catalog] %r resolvido por regra canônica para %s", value, canonical)
        return canonical.lower()

    raw_norm = normalize_treasury_text(value)
    raw_slug = slug_from_text(value)
    raw_years = set(re.findall(r"20\d{2}", value))

    for asset in assets:
        ticker = str(asset.ticker or "").lower()
        name = str(asset.name or "")
        if raw_slug == ticker or raw_slug == slug_from_text(name):
            return ticker

    candidates: list[tuple[int, str]] = []
    for asset in assets:
        ticker = str(asset.ticker or "").lower()
        name_norm = normalize_treasury_text(str(asset.name or ""))
        ticker_norm = normalize_treasury_text(ticker)
        haystack = f"{name_norm} {ticker_norm}"
        score = 0
        if raw_norm and raw_norm in haystack:
            score += 10
        if haystack and haystack in raw_norm:
            score += 8
        for token in raw_norm.split():
            if token and token in haystack:
                score += 1
        years = set(re.findall(r"20\d{2}", haystack))
        if raw_years and raw_years & years:
            score += 5
        if score > 0:
            candidates.append((score, ticker))

    if candidates:
        candidates.sort(reverse=True)
        resolved = candidates[0][1]
        logger.info("[treasury_catalog] %r resolvido para %s", value, resolved)
        return resolved

    logger.warning("[treasury_catalog] sem match para %r no catálogo persistido", value)
    return None
