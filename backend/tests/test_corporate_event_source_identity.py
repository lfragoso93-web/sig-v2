"""Cobertura da identidade canônica do catálogo de eventos corporativos."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.corporate_event import CorporateEvent, CorporateEventStatus
from app.services.corporate_action_engine import (
    CorporateActionNormalizationError,
    normalize_brapi_corporate_actions,
)
from app.services.corporate_event_service import (
    CorporateActionCollectionError,
    sync_corporate_events_for_asset,
)


def _brapi_payload() -> dict[str, object]:
    return {
        "results": [
            {
                "symbol": "TEST3",
                "data": {
                    "stockDividends": [
                        {
                            "lastDatePrior": "2026-01-15",
                            "factor": "1.10",
                            "assetIssued": "TEST3",
                        }
                    ],
                    "subscriptions": [],
                },
            }
        ]
    }


async def _empty_yahoo(symbol: str) -> list[tuple[date, float]]:
    assert symbol == "TEST3"
    return []


@pytest.mark.asyncio
async def test_sync_persists_and_deduplicates_by_canonical_source_identity(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="TEST3",
        brapi_ticker="TEST3",
        name="Ativo de teste",
        asset_type=AssetType.STOCK.value,
    )
    db.add(asset)
    await db.flush()

    async def brapi_fetcher(ticker: str) -> dict[str, object]:
        assert ticker == "TEST3"
        return _brapi_payload()

    created = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=_empty_yahoo,
    )

    assert len(created) == 1
    event = created[0]
    assert event.source_provider == "brapi"
    assert event.source_event_id
    assert event.portfolio_id is None
    assert event.effective_date == event.event_date == date(2026, 1, 15)
    assert Decimal(str(event.quantity_factor)) == Decimal(str(event.ratio))
    assert Decimal(str(event.quantity_factor)) == Decimal("1.10")

    expected_metadata = {
        "assetIssued": "TEST3",
        "factor": "1.10",
        "lastDatePrior": "2026-01-15",
    }
    assert event.raw_metadata == expected_metadata
    expected_payload = json.dumps(
        expected_metadata,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    assert event.source_payload_hash == hashlib.sha256(
        expected_payload.encode("utf-8")
    ).hexdigest()

    repeated = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=_empty_yahoo,
    )

    assert repeated == []


@pytest.mark.asyncio
async def test_sync_does_not_use_legacy_brapi_alias_as_canonical_identity(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="TEST3",
        brapi_ticker="TEST3",
        name="Ativo de teste",
        asset_type=AssetType.STOCK.value,
    )
    db.add(asset)
    await db.flush()

    [action] = normalize_brapi_corporate_actions("TEST3", _brapi_payload())
    db.add(
        CorporateEvent(
            asset_id=asset.id,
            ticker="TEST3",
            event_type=action.kind.value,
            status=CorporateEventStatus.PENDENTE.value,
            event_date=action.event_date,
            ratio=Decimal("1.10"),
            source_provider="legacy",
            source_event_id=None,
            brapi_event_id=action.source_event_id,
            raw_data="{}",
            portfolio_id=None,
            effective_date=action.event_date,
            quantity_factor=Decimal("1.10"),
        )
    )
    await db.flush()

    async def brapi_fetcher(ticker: str) -> dict[str, object]:
        assert ticker == "TEST3"
        return _brapi_payload()

    created = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=_empty_yahoo,
    )

    assert len(created) == 1
    assert created[0].source_provider == "brapi"
    assert created[0].source_event_id == action.source_event_id
    assert created[0].brapi_event_id is None


@pytest.mark.asyncio
async def test_sync_uses_yahoo_only_when_brapi_is_unavailable(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="TEST3",
        brapi_ticker="TEST3",
        name="Ativo de teste",
        asset_type=AssetType.STOCK.value,
    )
    db.add(asset)
    await db.flush()

    async def unavailable_brapi(ticker: str) -> dict[str, object]:
        raise CorporateActionCollectionError(f"{ticker}/brapi: indisponivel")

    async def yahoo_fallback(symbol: str) -> list[tuple[date, float]]:
        assert symbol == "TEST3"
        return [(date(2026, 2, 1), 0.5)]

    created = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=unavailable_brapi,
        yahoo_fetcher=yahoo_fallback,
    )

    assert len(created) == 1
    assert created[0].source_provider == "yahoo"
    assert created[0].effective_date == date(2026, 2, 1)
    assert Decimal(str(created[0].quantity_factor)) == Decimal("0.5")
    assert created[0].raw_metadata["provider_fallback"] == "brapi_unavailable"


@pytest.mark.asyncio
async def test_sync_uses_yahoo_as_separate_source_when_brapi_returns_valid_empty_payload(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="TEST3",
        brapi_ticker="TEST3",
        name="Ativo de teste",
        asset_type=AssetType.STOCK.value,
    )
    db.add(asset)
    await db.flush()

    async def empty_brapi(ticker: str) -> dict[str, object]:
        assert ticker == "TEST3"
        return {"results": []}

    async def yahoo_supplement(symbol: str) -> list[tuple[date, float]]:
        assert symbol == "TEST3"
        return [(date(2026, 2, 1), 0.5)]

    created = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=empty_brapi,
        yahoo_fetcher=yahoo_supplement,
    )

    assert len(created) == 1
    assert created[0].source_provider == "yahoo"
    assert created[0].effective_date == date(2026, 2, 1)
    assert Decimal(str(created[0].quantity_factor)) == Decimal("0.5")
    assert created[0].raw_metadata["provider_supplement"] == "brapi_valid_empty"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("asset_type", "ticker", "expected_yahoo_symbol", "expected_source"),
    [
        (AssetType.FII.value, "TEST11", "TEST11.SA", "b3"),
        (AssetType.STOCK.value, "AAPL", "AAPL", "yahoo"),
        (AssetType.ETF_INTERNACIONAL.value, "VOO", "VOO", "yahoo"),
    ],
)
async def test_sync_supports_fii_and_international_securities(
    db: AsyncSession,
    asset_type: str,
    ticker: str,
    expected_yahoo_symbol: str,
    expected_source: str,
) -> None:
    asset = Asset(
        ticker=ticker,
        brapi_ticker=ticker,
        name="Ativo de teste",
        asset_type=asset_type,
    )
    db.add(asset)
    await db.flush()

    async def empty_brapi(requested_ticker: str) -> dict[str, object]:
        assert requested_ticker == ticker
        return {"results": []}

    async def yahoo_supplement(symbol: str) -> list[tuple[date, float]]:
        assert symbol == expected_yahoo_symbol
        return [(date(2026, 2, 1), 0.5)]

    async def b3_fetcher(requested_ticker: str, requested_type: str):
        assert requested_ticker == ticker
        assert requested_type == asset_type
        return {
            "stockDividends": [
                {
                    "label": "DESDOBRAMENTO",
                    "factor": "100",
                    "lastDatePrior": "2026-02-01",
                    "isinCode": "BRTEST11ALQ0",
                }
            ],
            "subscriptions": [],
        }

    created = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=empty_brapi,
        yahoo_fetcher=yahoo_supplement,
        b3_fetcher=b3_fetcher,
    )

    assert len(created) == 1
    assert created[0].ticker == ticker
    assert created[0].source_provider == expected_source
    assert created[0].event_date == date(2026, 2, 1)
    if expected_source == "b3":
        assert created[0].effective_date is None
        assert Decimal(str(created[0].quantity_factor)) == Decimal("2")
    else:
        assert Decimal(str(created[0].quantity_factor)) == Decimal("0.5")


@pytest.mark.asyncio
async def test_sync_does_not_fallback_on_invalid_brapi_payload(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="TEST3",
        brapi_ticker="TEST3",
        name="Ativo de teste",
        asset_type=AssetType.STOCK.value,
    )
    db.add(asset)
    await db.flush()

    async def invalid_brapi(ticker: str) -> dict[str, object]:
        return {"results": {"invalid": True}}

    async def unexpected_yahoo(symbol: str) -> list[tuple[date, float]]:
        raise AssertionError("Yahoo nao deve mascarar payload BRAPI invalido")

    with pytest.raises(CorporateActionNormalizationError, match="results deve ser lista"):
        await sync_corporate_events_for_asset(
            db,
            asset,
            brapi_fetcher=invalid_brapi,
            yahoo_fetcher=unexpected_yahoo,
        )
