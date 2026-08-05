"""Regressões do leitor canônico de eventos aplicado às posições."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.corporate_event import CorporateEvent, CorporateEventStatus
from app.services.corporate_action_position_reader import (
    _effective_date,
    _quantity_factor,
    _raw_payload,
    _source_identity,
    load_global_corporate_actions_by_ticker,
)


@pytest.mark.asyncio
async def test_reader_prioritizes_canonical_fields_over_legacy_aliases(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="TEST3",
        name="Ativo de teste",
        asset_type=AssetType.ACAO.value,
    )
    db.add(asset)
    await db.flush()

    event = CorporateEvent(
        asset_id=asset.id,
        ticker="TEST3",
        event_type="BONIFICACAO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=date(2026, 2, 10),
        quantity_factor=Decimal("1.25"),
        source_provider="brapi",
        source_event_id="brapi:canonical",
        raw_metadata={"factor": "1.25", "origin": "canonical"},
        event_date=date(2020, 1, 1),
        ratio=Decimal("9.00"),
        brapi_event_id="legacy:identity",
        raw_data='{"source":"legacy","provider_payload":{"origin":"legacy"}}',
        portfolio_id=None,
    )
    db.add(event)
    await db.flush()

    loaded = await load_global_corporate_actions_by_ticker(db, ["test3"])

    assert tuple(loaded) == ("TEST3",)
    assert len(loaded["TEST3"]) == 1
    action = loaded["TEST3"][0]
    assert action.source == "brapi"
    assert action.source_event_id == "brapi:canonical"
    assert action.event_date == date(2026, 2, 10)
    assert action.quantity_factor == Decimal("1.25")
    assert action.raw_payload == {"factor": "1.25", "origin": "canonical"}


def test_reader_helpers_keep_explicit_legacy_fallback() -> None:
    event = CorporateEvent(
        id=42,
        asset_id=1,
        ticker="TEST3",
        event_type="DESDOBRAMENTO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=date(2026, 3, 1),
        quantity_factor=Decimal("2"),
        source_provider="brapi",
        source_event_id="brapi:canonical",
        event_date=date(2021, 4, 5),
        ratio=Decimal("3"),
        brapi_event_id="legacy:event",
        raw_data=(
            '{"source":"legacy","source_event_id":"legacy:event",'
            '"provider_payload":{"factor":"3"}}'
        ),
        portfolio_id=None,
    )

    event.effective_date = None
    event.quantity_factor = None
    event.source_provider = None
    event.source_event_id = None
    event.raw_metadata = None

    assert _effective_date(event) == date(2021, 4, 5)
    assert _quantity_factor(event) == Decimal("3")
    assert _source_identity(event) == ("catalog", "legacy:event")
    assert _raw_payload(event) == {"factor": "3"}
