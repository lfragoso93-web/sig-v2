from __future__ import annotations

from dataclasses import dataclass

import pytest
from app.models.asset import Asset, AssetType
from app.services.asset_universe_membership_service import (
    CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
    CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE,
    CRYPTO_TOP100_UNIVERSE_KEY,
)
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
    SYNTHETIC_CERTIFICATION_PROVIDER,
    SYNTHETIC_CERTIFICATION_PROVIDER_STATUS,
    require_financially_certified_crypto_asset,
)


@dataclass
class _ScalarResult:
    value: object | None

    def scalar_one_or_none(self):
        return self.value


@dataclass
class _RowsResult:
    rows: list[tuple[str, str]]

    def all(self):
        return self.rows


class _FakeSession:
    def __init__(self, *values: object | None) -> None:
        self._values = list(values)
        self.execute_calls = 0

    async def execute(self, _statement):
        self.execute_calls += 1
        value = self._values.pop(0)
        if isinstance(value, (_ScalarResult, _RowsResult)):
            return value
        return _ScalarResult(value)


def _crypto(
    ticker: str,
    provider_status: str | None,
    *,
    provider: str | None = None,
) -> Asset:
    return Asset(
        id=1,
        ticker=ticker,
        asset_type=AssetType.CRIPTO.value,
        provider=provider,
        provider_status=provider_status,
    )


def _top100_membership() -> _RowsResult:
    return _RowsResult([(CRYPTO_TOP100_UNIVERSE_KEY, "coingecko")])


@pytest.mark.asyncio
async def test_certified_crypto_is_allowed() -> None:
    asset = _crypto("BTC", "HISTORY_START_EXHAUSTED")
    db = _FakeSession(asset, _top100_membership())

    resolved = await require_financially_certified_crypto_asset(db, " btc ")

    assert resolved is asset
    assert db.execute_calls == 2


@pytest.mark.asyncio
async def test_crypto_outside_candidate_membership_is_rejected() -> None:
    db = _FakeSession(_crypto("XUSD", "HISTORY_START_EXHAUSTED"), _RowsResult([]))

    with pytest.raises(CryptoTransactionEligibilityError, match="fora do universo candidato"):
        await require_financially_certified_crypto_asset(db, "XUSD")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_status",
    [
        "HISTORY_START_COMPLEMENT_GAPPED",
        "HISTORY_START_SHALLOW_UNAVAILABLE",
        "ACTIVE",
        None,
        "FUTURE_UNKNOWN_STATUS",
    ],
)
async def test_non_certified_lifecycle_is_fail_closed(
    provider_status: str | None,
) -> None:
    db = _FakeSession(_crypto("APT", provider_status), _top100_membership())

    with pytest.raises(
        CryptoTransactionEligibilityError,
        match="histórico financeiro não certificado",
    ):
        await require_financially_certified_crypto_asset(db, "APT")


@pytest.mark.asyncio
async def test_missing_crypto_asset_is_rejected_without_membership_query() -> None:
    db = _FakeSession(None)

    with pytest.raises(CryptoTransactionEligibilityError, match="catálogo CRIPTO persistido"):
        await require_financially_certified_crypto_asset(db, "UNKNOWN")

    assert db.execute_calls == 1


@pytest.mark.asyncio
async def test_synthetic_certification_crypto_is_allowed_with_dedicated_membership() -> None:
    asset = _crypto(
        "BTC303",
        SYNTHETIC_CERTIFICATION_PROVIDER_STATUS,
        provider=SYNTHETIC_CERTIFICATION_PROVIDER,
    )
    memberships = _RowsResult(
        [
            (
                CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
                CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE,
            )
        ]
    )
    db = _FakeSession(asset, memberships)

    resolved = await require_financially_certified_crypto_asset(db, "BTC303")

    assert resolved is asset
    assert db.execute_calls == 2
