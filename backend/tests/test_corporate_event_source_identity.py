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
    assert symbol == "TEST3.SA"
    return []


@pytest.mark.asyncio
async def test_sync_persists_and_deduplicates_by_canonical_source_identity(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="TEST3",
        brapi_ticker="TEST3",
        name="Ativo de teste",
        asset_type=AssetType.ACAO.value,
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
        asset_type=AssetType.ACAO.value,
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
        asset_type=AssetType.ACAO.value,
    )
    db.add(asset)
    await db.flush()

    async def unavailable_brapi(ticker: str) -> dict[str, object]:
        raise CorporateActionCollectionError(f"{ticker}/brapi: indisponivel")

    async def yahoo_fallback(symbol: str) -> list[tuple[date, float]]:
        assert symbol == "TEST3.SA"
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
async def test_sync_does_not_call_yahoo_when_brapi_returns_valid_empty_payload(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="TEST3",
        brapi_ticker="TEST3",
        name="Ativo de teste",
        asset_type=AssetType.ACAO.value,
    )
    db.add(asset)
    await db.flush()

    async def empty_brapi(ticker: str) -> dict[str, object]:
        assert ticker == "TEST3"
        return {"results": []}

    async def unexpected_yahoo(symbol: str) -> list[tuple[date, float]]:
        raise AssertionError("Yahoo nao deve ser consultado apos resposta BRAPI valida")

    created = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=empty_brapi,
        yahoo_fetcher=unexpected_yahoo,
    )

    assert created == []


@pytest.mark.asyncio
async def test_sync_does_not_fallback_on_invalid_brapi_payload(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="TEST3",
        brapi_ticker="TEST3",
        name="Ativo de teste",
        asset_type=AssetType.ACAO.value,
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
