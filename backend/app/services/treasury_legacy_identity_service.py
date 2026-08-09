"""Consolidação segura de identidades legadas conhecidas do Tesouro Direto."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_alias import AssetAlias
from app.models.asset_dividend import AssetDividend
from app.models.asset_price import AssetPrice
from app.models.corporate_event import CorporateEvent
from app.models.portfolio_position import PortfolioPosition
from app.models.transaction import Transaction

_TREASURY_TYPE = AssetType.TESOURO_DIRETO.value

# Identidades antigas produzidas pelo catálogo anterior. O destino canônico é
# derivado do Tesouro Transparente e representa o mesmo título econômico.
LEGACY_EDUCA_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("tesouro-educa-15122030", "tesouro-educa-mais-2026"),
    ("tesouro-educa-15122031", "tesouro-educa-mais-2027"),
)


@dataclass
class TreasuryLegacyIdentityResult:
    consolidated: int = 0
    migrated_prices: int = 0
    migrated_transactions: int = 0
    created_aliases: int = 0
    skipped: int = 0
    errors: int = 0


async def _asset_by_ticker(db: AsyncSession, ticker: str) -> Asset | None:
    result = await db.execute(
        select(Asset).where(
            Asset.ticker == ticker,
            Asset.asset_type == _TREASURY_TYPE,
        )
    )
    return result.scalar_one_or_none()


async def _count_blockers(db: AsyncSession, legacy_id: int) -> int:
    dividend_count = await db.scalar(
        select(func.count()).select_from(AssetDividend).where(AssetDividend.asset_id == legacy_id)
    )
    event_count = await db.scalar(
        select(func.count()).select_from(CorporateEvent).where(
            (CorporateEvent.asset_id == legacy_id)
            | (CorporateEvent.destination_asset_id == legacy_id)
        )
    )
    position_count = await db.scalar(
        select(func.count()).select_from(PortfolioPosition).where(
            PortfolioPosition.asset_id == legacy_id
        )
    )
    return int(dividend_count or 0) + int(event_count or 0) + int(position_count or 0)


async def _ensure_alias(
    db: AsyncSession,
    *,
    canonical: Asset,
    legacy_ticker: str,
) -> bool:
    result = await db.execute(
        select(AssetAlias).where(
            AssetAlias.alias_ticker == legacy_ticker,
            AssetAlias.asset_type == _TREASURY_TYPE,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        if existing.asset_id != canonical.id:
            raise RuntimeError(
                f"alias legado {legacy_ticker} já aponta para asset_id={existing.asset_id}"
            )
        return False

    db.add(
        AssetAlias(
            asset_id=canonical.id,
            alias_ticker=legacy_ticker,
            asset_type=_TREASURY_TYPE,
            source_provider="tesouro_transparente_identity_migration",
        )
    )
    return True


async def consolidate_legacy_educa_identities(
    db: AsyncSession,
) -> TreasuryLegacyIdentityResult:
    """Consolida os dois Educa+ legados sem perder histórico.

    Segurança:
    - exige o ativo canônico já persistido;
    - recusa qualquer dependência em Proventos, eventos ou posições;
    - recusa colisão de preço em `(asset_id, timestamp)`;
    - migra transações textuais para o ticker canônico;
    - cria alias legado -> canônico antes de remover o Asset legado;
    - não executa commit; a transação pertence ao chamador.
    """
    result = TreasuryLegacyIdentityResult()

    for legacy_ticker, canonical_ticker in LEGACY_EDUCA_IDENTITIES:
        canonical = await _asset_by_ticker(db, canonical_ticker)
        if canonical is None:
            result.errors += 1
            continue

        legacy = await _asset_by_ticker(db, legacy_ticker)
        try:
            alias_created = await _ensure_alias(
                db,
                canonical=canonical,
                legacy_ticker=legacy_ticker,
            )
            if alias_created:
                result.created_aliases += 1

            if legacy is None:
                result.skipped += 1
                continue

            if await _count_blockers(db, legacy.id):
                result.errors += 1
                continue

            legacy_prices = list(
                (
                    await db.execute(
                        select(AssetPrice).where(AssetPrice.asset_id == legacy.id)
                    )
                ).scalars().all()
            )
            if legacy_prices:
                timestamps = [row.timestamp for row in legacy_prices]
                collisions = await db.scalar(
                    select(func.count())
                    .select_from(AssetPrice)
                    .where(
                        AssetPrice.asset_id == canonical.id,
                        AssetPrice.timestamp.in_(timestamps),
                    )
                )
                if int(collisions or 0) > 0:
                    result.errors += 1
                    continue
                for row in legacy_prices:
                    row.asset_id = canonical.id
                result.migrated_prices += len(legacy_prices)

            tx_result = await db.execute(
                update(Transaction)
                .where(
                    Transaction.asset_type == _TREASURY_TYPE,
                    func.lower(Transaction.ticker) == legacy_ticker,
                )
                .values(ticker=canonical_ticker)
            )
            result.migrated_transactions += int(tx_result.rowcount or 0)

            await db.delete(legacy)
            result.consolidated += 1
        except Exception:
            result.errors += 1

    return result
