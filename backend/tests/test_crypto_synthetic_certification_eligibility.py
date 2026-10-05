from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_universe_membership_service import (
    CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
    CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE,
    CRYPTO_TOP100_UNIVERSE_KEY,
)
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
    require_financially_certified_crypto_asset,
)


def _asset(*, provider: str | None, provider_status: str | None):
    return SimpleNamespace(
        id=303,
        ticker="CERT303-BTC",
        asset_type="CRIPTO",
        provider=provider,
        provider_status=provider_status,
    )


def _result_with_asset(asset):
    result = MagicMock()
    result.scalar_one_or_none.return_value = asset
    return result


def _result_with_memberships(rows):
    result = MagicMock()
    result.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_owned_synthetic_crypto_is_eligible_only_with_dedicated_membership() -> None:
    db = AsyncMock(spec=AsyncSession)
    asset = _asset(
        provider="synthetic-certification",
        provider_status="synthetic-owned",
    )
    db.execute = AsyncMock(
        side_effect=[
            _result_with_asset(asset),
            _result_with_memberships(
                [
                    (
                        CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
                        CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE,
                    )
                ]
            ),
        ]
    )

    actual = await require_financially_certified_crypto_asset(db, "cert303-btc")

    assert actual is asset
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_synthetic_crypto_rejects_missing_or_wrong_membership_source() -> None:
    for rows in (
        [],
        [(CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY, "coingecko")],
        [(CRYPTO_TOP100_UNIVERSE_KEY, "synthetic-certification")],
    ):
        db = AsyncMock(spec=AsyncSession)
        asset = _asset(
            provider="synthetic-certification",
            provider_status="synthetic-owned",
        )
        db.execute = AsyncMock(
            side_effect=[
                _result_with_asset(asset),
                _result_with_memberships(rows),
            ]
        )

        with pytest.raises(
            CryptoTransactionEligibilityError,
            match="prova de elegibilidade sintética ausente ou inválida",
        ):
            await require_financially_certified_crypto_asset(db, "CERT303-BTC")


@pytest.mark.asyncio
async def test_real_crypto_path_still_requires_top100_and_financial_status() -> None:
    db = AsyncMock(spec=AsyncSession)
    asset = _asset(provider="brapi", provider_status="HISTORY_START_EXHAUSTED")
    db.execute = AsyncMock(
        side_effect=[
            _result_with_asset(asset),
            _result_with_memberships(
                [(CRYPTO_TOP100_UNIVERSE_KEY, "real-source")]
            ),
        ]
    )

    actual = await require_financially_certified_crypto_asset(db, "CERT303-BTC")

    assert actual is asset


@pytest.mark.asyncio
async def test_synthetic_membership_does_not_certify_non_synthetic_asset() -> None:
    db = AsyncMock(spec=AsyncSession)
    asset = _asset(provider="brapi", provider_status="synthetic-owned")
    db.execute = AsyncMock(
        side_effect=[
            _result_with_asset(asset),
            _result_with_memberships(
                [
                    (
                        CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
                        CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE,
                    )
                ]
            ),
        ]
    )

    with pytest.raises(
        CryptoTransactionEligibilityError,
        match="fora do universo candidato Top 100 persistido",
    ):
        await require_financially_certified_crypto_asset(db, "CERT303-BTC")
