"""Elegibilidade DB-first de CRIPTO para gravações transacionais."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_universe_membership import AssetUniverseMembership
from app.services.asset_universe_membership_service import CRYPTO_TOP100_UNIVERSE_KEY
from app.services.crypto_financial_certification_service import (
    is_crypto_financially_certified,
)


@dataclass(frozen=True)
class CryptoTransactionEligibilityError(ValueError):
    """Erro de domínio para CRIPTO fora do universo financeiro certificado."""

    ticker: str
    reason: str
    provider_status: str | None = None

    def __str__(self) -> str:
        detail = f"CRIPTO {self.ticker} não elegível para transações: {self.reason}"
        if self.provider_status:
            detail += f" (provider_status={self.provider_status})"
        return detail


async def require_financially_certified_crypto_asset(
    db: AsyncSession,
    ticker: str,
) -> Asset:
    """Retorna CRIPTO apenas se candidata Top100 e financeiramente certificada.

    A validação é estritamente DB-first: não consulta CoinGecko, BRAPI ou qualquer
    outro provider durante o request transacional.
    """
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise CryptoTransactionEligibilityError(
            ticker=normalized_ticker,
            reason="ticker vazio",
        )

    asset_result = await db.execute(
        select(Asset)
        .where(Asset.asset_type == AssetType.CRIPTO.value)
        .where(func.upper(Asset.ticker) == normalized_ticker)
        .limit(1)
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        raise CryptoTransactionEligibilityError(
            ticker=normalized_ticker,
            reason="ativo não pertence ao catálogo CRIPTO persistido",
        )

    membership_result = await db.execute(
        select(AssetUniverseMembership.id)
        .where(AssetUniverseMembership.asset_id == asset.id)
        .where(AssetUniverseMembership.universe_key == CRYPTO_TOP100_UNIVERSE_KEY)
        .limit(1)
    )
    if membership_result.scalar_one_or_none() is None:
        raise CryptoTransactionEligibilityError(
            ticker=normalized_ticker,
            reason="ativo fora do universo candidato Top 100 persistido",
            provider_status=asset.provider_status,
        )

    if not is_crypto_financially_certified(asset.provider_status):
        raise CryptoTransactionEligibilityError(
            ticker=normalized_ticker,
            reason="histórico financeiro não certificado",
            provider_status=asset.provider_status,
        )

    return asset
