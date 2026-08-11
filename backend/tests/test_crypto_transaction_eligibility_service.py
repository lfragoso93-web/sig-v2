from __future__ import annotations

from dataclasses import dataclass

import pytest
from app.models.asset import Asset, AssetType
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
    require_financially_certified_crypto_asset,
)


@dataclass
class _ScalarResult:
    value: object | None

    def scalar_one_or_none(self):
        return self.value


class _FakeSession:
    def __init__(self, *values: object | None) -> None:
        self._values = list(values)
        self.execute_calls = 0

    async def execute(self, _statement):
        self.execute_calls += 1
        return _ScalarResult(self._values.pop(0))


def _crypto(ticker: str, provider_status: str | None) -> Asset:
    return Asset(
        id=1,
        ticker=ticker,
        asset_type=AssetType.CRIPTO.value,
        provider_status=provider_status,
    )


@pytest.mark.asyncio
async def test_certified_crypto_is_allowed() -> None:
    asset = _crypto("BTC", "HISTORY_START_EXHAUSTED")
    db = _FakeSession(asset, 10)

    resolved = await require_financially_certified_crypto_asset(db, " btc ")

    assert resolved is asset
    assert db.execute_calls == 2


@pytest.mark.asyncio
async def test_crypto_outside_candidate_membership_is_rejected() -> None:
    db = _FakeSession(_crypto("XUSD", "HISTORY_START_EXHAUSTED"), None)

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
    db = _FakeSession(_crypto("APT", provider_status), 20)

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
