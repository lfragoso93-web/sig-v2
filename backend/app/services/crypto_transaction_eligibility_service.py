"""Elegibilidade DB-first de CRIPTO para gravações transacionais."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_universe_membership import AssetUniverseMembership
from app.services.asset_universe_membership_service import (
    CRYPTO_SYNTHETIC_CERTIFICATION_PROVIDER as SYNTHETIC_CERTIFICATION_PROVIDER,
    CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
    CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE,
)

SYNTHETIC_CERTIFICATION_PROVIDER_STATUS = "synthetic-owned"


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


_CRYPTO_NAME_TO_TICKER: dict[str, str] = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "TETHER": "USDT",
    "BINANCE COIN": "BNB",
    "BINANCECOIN": "BNB",
    "BNB": "BNB",
    "SOLANA": "SOL",
    "RIPPLE": "XRP",
    "CARDANO": "ADA",
    "DOGECOIN": "DOGE",
    "POLKADOT": "DOT",
    "AVALANCHE": "AVAX",
    "CHAINLINK": "LINK",
    "POLYGON": "MATIC",
    "SHIBA INU": "SHIB",
    "SHIBA": "SHIB",
    "LITECOIN": "LTC",
    "UNISWAP": "UNI",
    "STELLAR": "XLM",
    "MONERO": "XMR",
    "COSMOS": "ATOM",
    "BITCOIN CASH": "BCH",
    "USD COIN": "USDC",
}


async def require_catalog_crypto_asset(
    db: AsyncSession,
    ticker: str,
) -> Asset:
    """Resolve a persisted CRIPTO asset for a user-entered portfolio fact.

    Incomplete market coverage does not invalidate a transaction supplied by
    the user. Coverage statuses remain available to valuation and readiness.
    Synthetic certification assets still require their dedicated provenance.
    No external provider is queried during a transaction request.
    """
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise CryptoTransactionEligibilityError(
            ticker=normalized_ticker,
            reason="ticker vazio",
        )

    candidate_tickers = [normalized_ticker]
    mapped_ticker = _CRYPTO_NAME_TO_TICKER.get(normalized_ticker)
    if mapped_ticker and mapped_ticker not in candidate_tickers:
        candidate_tickers.append(mapped_ticker)

    asset_result = await db.execute(
        select(Asset)
        .where(Asset.asset_type == AssetType.CRIPTO.value)
        .where(
            or_(
                func.upper(Asset.ticker).in_(candidate_tickers),
                func.upper(Asset.name) == normalized_ticker,
                func.upper(Asset.name).in_(candidate_tickers),
            )
        )
        .limit(1)
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        raise CryptoTransactionEligibilityError(
            ticker=normalized_ticker,
            reason="ativo nao pertence ao catalogo CRIPTO persistido",
        )

    if asset.provider == SYNTHETIC_CERTIFICATION_PROVIDER:
        if asset.provider_status != SYNTHETIC_CERTIFICATION_PROVIDER_STATUS:
            raise CryptoTransactionEligibilityError(
                ticker=normalized_ticker,
                reason="identidade sintetica invalida",
                provider_status=asset.provider_status,
            )
        membership_result = await db.execute(
            select(
                AssetUniverseMembership.universe_key,
                AssetUniverseMembership.source,
            )
            .where(AssetUniverseMembership.asset_id == asset.id)
            .where(
                AssetUniverseMembership.universe_key
                == CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY
            )
        )
        memberships = dict(membership_result.all())
        if memberships.get(CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY) != (
            CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE
        ):
            raise CryptoTransactionEligibilityError(
                ticker=normalized_ticker,
                reason="prova de elegibilidade sintetica ausente ou invalida",
                provider_status=asset.provider_status,
            )
        return asset

    if asset.provider_status == SYNTHETIC_CERTIFICATION_PROVIDER_STATUS:
        raise CryptoTransactionEligibilityError(
            ticker=normalized_ticker,
            reason="metadata sintetica em ativo de provedor real",
            provider_status=asset.provider_status,
        )

    return asset
