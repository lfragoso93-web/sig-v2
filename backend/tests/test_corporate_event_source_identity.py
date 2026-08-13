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
from app.services.corporate_action_engine import normalize_brapi_corporate_actions
from app.services.corporate_event_service import sync_corporate_events_for_asset


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
    assert event.brapi_event_id == event.source_event_id
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
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert event.source_payload_hash == hashlib.sha256(
        expected_payload.encode("utf-8")
    ).hexdigest()

    serialized_legacy = json.loads(event.raw_data)
    assert serialized_legacy["source"] == event.source_provider
    assert serialized_legacy["source_event_id"] == event.source_event_id
    assert serialized_legacy["event_date"] == event.effective_date.isoformat()
    assert Decimal(serialized_legacy["quantity_factor"]) == Decimal(
        str(event.quantity_factor)
    )
    assert serialized_legacy["provider_payload"] == event.raw_metadata

    repeated = await sync_corporate_events_for_asset(
        db,
        asset,
        brapi_fetcher=brapi_fetcher,
        yahoo_fetcher=_empty_yahoo,
    )

    assert repeated == []


@pytest.mark.asyncio
async def test_sync_respects_legacy_identity_during_transition(
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

    normalized = normalize_brapi_corporate_actions("TEST3", _brapi_payload())
    assert len(normalized) == 1
    action = normalized[0]

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

    assert created == []
