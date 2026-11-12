"""Consultas DB-first ao catálogo persistido de ativos.

Este serviço não consulta providers. O catálogo é abastecido pelo bootstrap
certificado e deve ser a única fonte para descoberta/sugestão no runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_alias import AssetAlias
from app.services.asset_universe_membership_service import (
    CRYPTO_SYNTHETIC_CERTIFICATION_PROVIDER,
)
from app.services.treasury_catalog_service import format_friendly_treasury_title


@dataclass(frozen=True)
class AssetCatalogSuggestion:
    ticker: str
    name: str
    asset_type: str


_B3_CLASS_TYPES = frozenset({
    AssetType.ACAO.value,
    AssetType.FII.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.BDR.value,
})
_B3_TICKER_DIGITS_RE = re.compile(r"^[A-Z][A-Z0-9]*\d+[A-Z]?$")


def _normalize_filter(asset_type: str | None) -> tuple[str, ...] | None:
    if not asset_type:
        return None

    value = asset_type.strip().upper()
    aliases: dict[str, tuple[str, ...]] = {
        "ACAO": (AssetType.ACAO.value,),
        "ACOES": (AssetType.ACAO.value,),
        "AÇÃO": (AssetType.ACAO.value,),
        "AÇÕES": (AssetType.ACAO.value,),
        "FUND": (AssetType.FII.value,),
        "FII": (AssetType.FII.value,),
        "FIIS": (AssetType.FII.value,),
        "ETF": (AssetType.ETF_NACIONAL.value,),
        "ETF_BR": (AssetType.ETF_NACIONAL.value,),
        "ETF_NACIONAL": (AssetType.ETF_NACIONAL.value,),
        "BDR": (AssetType.BDR.value,),
        "STOCK": (AssetType.STOCK.value,),
        "STOCK_INT": (AssetType.STOCK.value,),
        "ETF_INT": (AssetType.ETF_INTERNACIONAL.value,),
        "ETF_INTERNACIONAL": (AssetType.ETF_INTERNACIONAL.value,),
        "CRIPTO": (AssetType.CRIPTO.value,),
        "CRYPTO": (AssetType.CRIPTO.value,),
        "TESOURO": (AssetType.TESOURO_DIRETO.value,),
        "TESOURO_DIRETO": (AssetType.TESOURO_DIRETO.value,),
        "RENDA_FIXA": (AssetType.RENDA_FIXA.value,),
        "OUTRO": (AssetType.OUTRO.value,),
    }
    return aliases.get(value, (value,))


def _user_selectable_catalog_predicate():
    return or_(
        Asset.asset_type != AssetType.CRIPTO.value,
        and_(
            Asset.asset_type == AssetType.CRIPTO.value,
            func.lower(func.coalesce(Asset.provider, ""))
            != CRYPTO_SYNTHETIC_CERTIFICATION_PROVIDER,
        ),
    )


async def suggest_assets_from_catalog(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 10,
    asset_type: str | None = None,
) -> list[AssetCatalogSuggestion]:
    """Search persisted user assets, excluding synthetic certification fixtures."""
    normalized = query.strip().upper()
    if not normalized:
        return []

    from app.core.asset_types import normalize_b3_equity_ticker
    from app.services.crypto_transaction_eligibility_service import _CRYPTO_NAME_TO_TICKER

    allowed_types = _normalize_filter(asset_type)
    allowed_set = set(allowed_types) if allowed_types else None

    search_terms = [normalized]
    if allowed_set is None or bool(allowed_set & _B3_CLASS_TYPES):
        base_equity = normalize_b3_equity_ticker(normalized)
        if base_equity != normalized and base_equity not in search_terms:
            search_terms.append(base_equity)
    if allowed_set is None or AssetType.CRIPTO.value in allowed_set:
        mapped_crypto = _CRYPTO_NAME_TO_TICKER.get(normalized)
        if mapped_crypto and mapped_crypto not in search_terms:
            search_terms.append(mapped_crypto)
        for c_name, c_ticker in _CRYPTO_NAME_TO_TICKER.items():
            if normalized == c_ticker and c_name not in search_terms:
                search_terms.append(c_name)

    predicates = []
    for term in search_terms:
        term_like = f"%{term}%"
        predicates.extend([
            func.upper(Asset.ticker).like(term_like),
            func.upper(func.coalesce(Asset.name, "")).like(term_like),
            func.upper(AssetAlias.alias_ticker).like(term_like),
        ])

    alias_join = (
        and_(
            AssetAlias.asset_id == Asset.id,
            AssetAlias.asset_type.in_(allowed_types),
        )
        if allowed_types
        else (AssetAlias.asset_id == Asset.id)
    )
    stmt = (
        select(Asset, AssetAlias.alias_ticker)
        .outerjoin(AssetAlias, alias_join)
        .where(
            or_(*predicates),
            _user_selectable_catalog_predicate(),
        )
    )
    if allowed_types:
        stmt = stmt.where(Asset.asset_type.in_(allowed_types))

    stmt = stmt.order_by(
        case(
            (func.upper(Asset.ticker) == normalized, 0),
            (func.upper(Asset.ticker).in_(search_terms), 1),
            (func.upper(func.coalesce(Asset.name, "")) == normalized, 2),
            (func.upper(func.coalesce(AssetAlias.alias_ticker, "")) == normalized, 3),
            else_=4,
        ),
        Asset.ticker,
    ).limit(max(1, min(limit, 50)))

    result = await db.execute(stmt)
    rows = result.all()
    seen: set[tuple[str, str]] = set()
    suggestions: list[AssetCatalogSuggestion] = []
    for asset, alias_ticker in rows:
        ticker_upper = str(asset.ticker or "").strip().upper()
        asset_type_str = str(asset.asset_type)
        if (
            allowed_set is not None
            and asset_type_str in _B3_CLASS_TYPES
            and not _B3_TICKER_DIGITS_RE.fullmatch(ticker_upper)
        ):
            continue
        key = (asset.ticker, asset_type_str)
        if key in seen:
            continue
        seen |= {key}
        name = asset.name or asset.ticker
        if str(asset.asset_type) == AssetType.TESOURO_DIRETO.value:
            name = format_friendly_treasury_title(name, asset.ticker)
        elif alias_ticker and normalized in alias_ticker.upper() and alias_ticker.upper() != asset.ticker.upper():
            name = f"{name} (antigo {alias_ticker})"
        suggestions.append(
            AssetCatalogSuggestion(
                ticker=asset.ticker,
                name=name,
                asset_type=str(asset.asset_type),
            )
        )
    return suggestions


async def list_treasury_from_catalog(
    db: AsyncSession,
    query: str = "",
    *,
    limit: int = 200,
) -> list[AssetCatalogSuggestion]:
    """Lista títulos do Tesouro já persistidos pelo bootstrap."""
    import re
    stmt = select(Asset).where(Asset.asset_type == AssetType.TESOURO_DIRETO.value)
    normalized = query.strip().upper()
    if normalized:
        tokens = [t for t in re.split(r"[\s+\-]+", normalized) if t]
        if tokens:
            predicates = [
                or_(
                    func.upper(Asset.ticker).like(f"%{token}%"),
                    func.upper(func.coalesce(Asset.name, "")).like(f"%{token}%"),
                )
                for token in tokens
            ]
            stmt = stmt.where(and_(*predicates))

    stmt = stmt.order_by(Asset.ticker).limit(max(1, min(limit, 500)))
    result = await db.execute(stmt)
    assets = result.scalars().all()
    return [
        AssetCatalogSuggestion(
            ticker=asset.ticker,
            name=format_friendly_treasury_title(asset.name or asset.ticker, asset.ticker),
            asset_type=AssetType.TESOURO_DIRETO.value,
        )
        for asset in assets
    ]
