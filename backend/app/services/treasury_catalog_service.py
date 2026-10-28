"""Serviço de catálogo do Tesouro Direto.

Fonte de verdade: tabela assets. O bootstrap popula o catálogo por meio da
fronteira `treasury_catalog_provider`, que usa Tesouro Transparente como fonte
primária e BRAPI somente como fallback operacional.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_safety import sanitize_log_value
from app.integrations.brapi_treasury import canonical_treasury_symbol_from_text
from app.integrations.treasury_catalog_provider import fetch_treasury_catalog
from app.models.asset import Asset, AssetType
from app.models.asset_alias import AssetAlias
from app.services.treasury_legacy_identity_service import (
    consolidate_legacy_educa_identities,
)

logger = logging.getLogger(__name__)

_TREASURY_TYPE = AssetType.TESOURO_DIRETO.value
_INACTIVE_STATUS = "NOT_APPLICABLE"


@dataclass
class TreasurySeedResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    consolidated: int = 0
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


def format_friendly_treasury_title(name: str | None, ticker: str | None = None) -> str:
    raw = (name or ticker or "").strip()
    if not raw:
        return ""

    cleaned = re.sub(r"\s+aposentadoria\s+extra\b", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"\brenda\+", "Renda+", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\beduca\+", "Educa+", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    from_full_date = False
    full_date_year = None
    dmy_match = re.search(r"\b\d{1,2}/\d{1,2}/(20\d{2})\b", cleaned)
    if dmy_match:
        from_full_date = True
        full_date_year = int(dmy_match.group(1))
        cleaned = re.sub(r"\b\d{1,2}/\d{1,2}/20\d{2}\b", "", cleaned).strip()
    else:
        iso_match = re.search(r"\b(20\d{2})[-/]\d{1,2}[-/]\d{1,2}\b", cleaned)
        if iso_match:
            from_full_date = True
            full_date_year = int(iso_match.group(1))
            cleaned = re.sub(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", "", cleaned).strip()
        else:
            digits_match = re.search(r"\b\d{4}(20\d{2})\b", cleaned)
            if digits_match:
                from_full_date = True
                full_date_year = int(digits_match.group(1))
                cleaned = re.sub(r"\b\d{8}\b", "", cleaned).strip()

    name_years = [int(m) for m in re.findall(r"\b(20\d{2})\b", cleaned)]
    cleaned = re.sub(r"\b20\d{2}\b", "", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    ticker_clean = (ticker or "").lower().strip()
    ticker_full_date_year = None
    ticker_years: list[int] = []
    if ticker_clean:
        tm_digits = re.search(r"\b\d{4}(20\d{2})\b", ticker_clean) or re.search(r"(\d{2})(\d{2})(20\d{2})", ticker_clean)
        if tm_digits:
            ticker_full_date_year = int(tm_digits.group(len(tm_digits.groups())))
        ticker_without_digits = re.sub(r"\d{8}", "", ticker_clean)
        ticker_years = [int(m) for m in re.findall(r"\b(20\d{2})\b", ticker_without_digits) or re.findall(r"(20\d{2})", ticker_without_digits)]

    norm = f"{cleaned} {ticker_clean}".lower()
    if "renda" in norm:
        final_year = None
        # 1. Commercial year from ticker
        comm_ticker = [y for y in ticker_years if y >= 2030 and y % 5 == 0]
        if comm_ticker:
            final_year = comm_ticker[0]
        # 2. Commercial year from name
        elif any(y >= 2030 and y % 5 == 0 for y in name_years):
            final_year = [y for y in name_years if y >= 2030 and y % 5 == 0][0]
        # 3. Full date in ticker (maturity date)
        elif ticker_full_date_year:
            final_year = ticker_full_date_year - 19 if ticker_full_date_year >= 2049 else ticker_full_date_year
        # 4. Full date in name (maturity date)
        elif from_full_date and full_date_year:
            final_year = full_date_year - 19 if full_date_year >= 2049 else full_date_year
        # 5. Maturity year in ticker
        elif ticker_years:
            y = ticker_years[0]
            final_year = y - 19 if y >= 2049 and y % 5 == 4 else y
        # 6. Maturity year in name
        elif name_years:
            y = name_years[0]
            final_year = y - 19 if y >= 2049 and y % 5 == 4 else y

        return f"Tesouro Renda+ {final_year}" if final_year else "Tesouro Renda+"

    if "educa" in norm:
        final_year = None
        # 1. Commercial year from ticker
        comm_ticker = [y for y in ticker_years if 2026 <= y <= 2043]
        if comm_ticker:
            final_year = comm_ticker[0]
        # 2. Full date in ticker (e.g. tesouro-educa-15122030)
        elif ticker_full_date_year:
            final_year = ticker_full_date_year - 4 if ticker_full_date_year >= 2030 else ticker_full_date_year
        # 3. Full date in name (maturity date, e.g. 15/12/2030)
        elif from_full_date and full_date_year:
            final_year = full_date_year - 4 if full_date_year >= 2030 else full_date_year
        # 4. Commercial year from name (e.g. Tesouro Educa+ 2026 or Tesouro Educa+ 2030 without ticker)
        elif any(2026 <= y <= 2043 for y in name_years):
            final_year = [y for y in name_years if 2026 <= y <= 2043][0]
        # 5. Maturity year > 2043 in ticker or name (e.g. 2046 -> 2042)
        elif any(2043 < y <= 2055 for y in (ticker_years + name_years)):
            y = [y for y in (ticker_years + name_years) if 2043 < y <= 2055][0]
            final_year = y - 4
        # 6. Ticker years fallback
        elif ticker_years:
            final_year = ticker_years[0]
        # 7. Name years fallback
        elif name_years:
            final_year = name_years[0]

        return f"Tesouro Educa+ {final_year}" if final_year else "Tesouro Educa+"

    final_year = (ticker_years[0] if ticker_years else None) or ticker_full_date_year or (name_years[0] if name_years else None) or full_date_year
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if cleaned.lower().startswith("tesouro-"):
        slug_norm = cleaned.lower().strip("-")
        if "selic" in slug_norm:
            cleaned = "Tesouro Selic"
        elif "prefixado" in slug_norm:
            cleaned = "Tesouro Prefixado com Juros Semestrais" if "juros-semestrais" in slug_norm else "Tesouro Prefixado"
        elif "ipca" in slug_norm:
            cleaned = "Tesouro IPCA+ com Juros Semestrais" if "juros-semestrais" in slug_norm else "Tesouro IPCA+"
        elif "igpm" in slug_norm or "igp-m" in slug_norm:
            cleaned = "Tesouro IGPM com Juros Semestrais" if "juros-semestrais" in slug_norm else "Tesouro IGPM"
    else:
        cleaned = re.sub(r"-+$", "", cleaned).strip()

    return f"{cleaned} {final_year}" if final_year else cleaned


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
    bond_type = re.sub(r"\s+aposentadoria\s+extra\b", "", bond_type, flags=re.IGNORECASE).strip()
    maturity_year = item.get("maturityYear")
    maturity = str(item.get("maturityDate") or item.get("dueDate") or item.get("expiresAt") or "").strip()

    raw_label = bond_type
    if maturity:
        raw_label = f"{raw_label} {maturity}"
    elif maturity_year:
        raw_label = f"{raw_label} {maturity_year}"

    friendly = format_friendly_treasury_title(raw_label or symbol, symbol)
    if friendly:
        return friendly

    year = None
    if maturity_year:
        year = str(maturity_year).strip()
    elif maturity and len(maturity) >= 4 and maturity[:4].isdigit():
        year = maturity[:4]
    elif symbol:
        year_match = re.search(r"20\d{2}", symbol)
        if year_match:
            year = year_match.group(0)

    if bond_type and year:
        return f"{bond_type} {year}"
    return format_friendly_treasury_title(bond_type or symbol, symbol)


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
    """Importa/atualiza títulos reais e consolida identidades legadas conhecidas."""
    result = TreasurySeedResult()
    try:
        items = await fetch_treasury_catalog()
    except Exception as exc:
        logger.error(
            "[treasury_seed] falha ao buscar catálogo Tesouro: %s",
            sanitize_log_value(exc),
        )
        result.errors += 1
        return result

    for item in items:
        symbol = _symbol(item)
        if not symbol:
            result.errors += 1
            continue

        name = _name(item, symbol)
        friendly_name = format_friendly_treasury_title(name, symbol)
        final_name = friendly_name or name
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
                        name=final_name,
                        asset_type=_TREASURY_TYPE,
                        currency="BRL",
                        sector=sector,
                    )
                )
                result.created += 1
                continue
            changed = False
            if final_name and existing.name != final_name:
                existing.name = final_name
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
            logger.error(
                "[treasury_seed] erro ao salvar %s: %s",
                sanitize_log_value(symbol),
                sanitize_log_value(exc),
            )
            result.errors += 1

    await db.flush()
    consolidation = await consolidate_legacy_educa_identities(db)
    result.consolidated = consolidation.consolidated
    result.errors += consolidation.errors

    if commit:
        await db.commit()
    logger.info(
        "[treasury_seed] concluído: %d criados, %d atualizados, %d ignorados, "
        "%d consolidados, %d erros",
        result.created,
        result.updated,
        result.skipped,
        result.consolidated,
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
    canonical = canonical_treasury_symbol_from_text(value)
    if canonical and canonical.lower() != lower:
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

    alias = await db.execute(
        select(Asset.ticker)
        .join(AssetAlias, AssetAlias.asset_id == Asset.id)
        .where(
            Asset.asset_type == _TREASURY_TYPE,
            AssetAlias.asset_type == _TREASURY_TYPE,
            func.lower(AssetAlias.alias_ticker) == lower,
            func.coalesce(Asset.provider_status, "") != _INACTIVE_STATUS,
        )
    )
    found = alias.scalars().first()
    if found:
        return str(found).lower()

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
        logger.info(
            "[treasury_catalog] %r resolvido para %s",
            sanitize_log_value(value),
            sanitize_log_value(resolved),
        )
        return resolved

    logger.warning(
        "[treasury_catalog] sem match para %r no catálogo persistido",
        sanitize_log_value(value),
    )
    return None
