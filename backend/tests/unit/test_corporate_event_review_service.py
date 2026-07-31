from datetime import date
from decimal import Decimal

import pytest
from app.models.asset import Asset, AssetType
from app.models.audit_log import AuditLog
from app.models.corporate_event import CorporateEvent
from app.models.user import User, UserRole
from app.schemas.corporate_event_review import CorporateEventReviewDecision
from app.services.corporate_event_reconciliation_service import (
    reconcile_corporate_events_for_asset,
)
from app.services.corporate_event_review_service import (
    CorporateEventTermsIncompleteError,
    get_corporate_event_evidence_group,
    preview_corporate_exchange_projection,
    review_corporate_event,
)
from app.services.corporate_position_projection_service import (
    load_eligible_quantity_actions,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _reviewer(db: AsyncSession) -> User:
    user = User(
        name="Admin",
        email="reviewer@example.com",
        hashed_password="hash",
        role=UserRole.superadmin,
    )
    db.add(user)
    await db.flush()
    return user


async def _asset(db: AsyncSession) -> Asset:
    asset = Asset(
        ticker="ABCD3",
        name="ABCD",
        asset_type=AssetType.ACAO.value,
        currency="BRL",
    )
    db.add(asset)
    await db.flush()
    return asset


async def _event(
    db: AsyncSession,
    asset: Asset,
    *,
    source: str,
    source_id: str,
    reconciliation_status: str,
    group: str,
    factor: str = "2",
) -> CorporateEvent:
    event = CorporateEvent(
        asset_id=asset.id,
        ticker=asset.ticker,
        event_type="DESDOBRAMENTO",
        status="DISCOVERED",
        reconciliation_status=reconciliation_status,
        requires_review=True,
        review_reason="revisão necessária",
        source_provider=source,
        source_event_id=source_id,
        reconciliation_group_hash=group,
        is_canonical=reconciliation_status != "CONFLICT",
        effective_date=date(2026, 7, 1),
        quantity_factor=Decimal(factor),
        event_date=date(2026, 7, 1),
        ratio=Decimal(factor),
        currency="BRL",
        raw_metadata={"provider_id": source_id, "factor": factor},
    )
    db.add(event)
    await db.flush()
    return event


@pytest.mark.asyncio
async def test_manual_approval_is_audited_and_becomes_projection_eligible(
    db: AsyncSession,
):
    reviewer = await _reviewer(db)
    asset = await _asset(db)
    event = await _event(
        db,
        asset,
        source="brapi",
        source_id="brapi-1",
        reconciliation_status="UNRECONCILED",
        group="group-1",
    )

    reviewed = await review_corporate_event(
        db,
        event_id=event.id,
        decision=CorporateEventReviewDecision.APPROVE,
        note="Evidência oficial conferida manualmente.",
        reviewer_user_id=reviewer.id,
    )
    actions = await load_eligible_quantity_actions(
        db,
        tickers=[asset.ticker],
        through_date=date(2026, 7, 31),
    )
    audit = (await db.execute(select(AuditLog))).scalar_one()
    await reconcile_corporate_events_for_asset(db, asset.id)

    assert reviewed.status == "VALIDATED"
    assert reviewed.reconciliation_status == "MANUALLY_VALIDATED"
    assert reviewed.requires_review is False
    assert reviewed.reviewed_by_user_id == reviewer.id
    assert actions[asset.ticker][0].event_id == event.id
    assert audit.resource_type == "CORPORATE_EVENT_REVIEW"
    assert audit.new_values["decision"] == "APPROVE"
    assert reviewed.reconciliation_status == "MANUALLY_VALIDATED"
    assert reviewed.requires_review is False


@pytest.mark.asyncio
async def test_conflict_approval_rejects_competing_evidence(db: AsyncSession):
    reviewer = await _reviewer(db)
    asset = await _asset(db)
    selected = await _event(
        db,
        asset,
        source="brapi",
        source_id="brapi-conflict",
        reconciliation_status="CONFLICT",
        group="conflict-1",
    )
    competing = await _event(
        db,
        asset,
        source="yahoo",
        source_id="yahoo-conflict",
        reconciliation_status="CONFLICT",
        group="conflict-1",
    )

    await review_corporate_event(
        db,
        event_id=selected.id,
        decision=CorporateEventReviewDecision.APPROVE,
        note="BRAPI escolhida após conferência documental.",
        reviewer_user_id=reviewer.id,
    )
    await db.refresh(competing)

    assert selected.is_canonical is True
    assert selected.reconciliation_status == "MANUALLY_VALIDATED"
    assert competing.status == "REJECTED"
    assert competing.is_canonical is False
    assert competing.requires_review is False
    assert competing.reviewed_by_user_id == reviewer.id


@pytest.mark.asyncio
async def test_evidence_group_exposes_payloads_and_marks_divergent_fields(
    db: AsyncSession,
):
    await _reviewer(db)
    asset = await _asset(db)
    first = await _event(
        db,
        asset,
        source="brapi",
        source_id="brapi-evidence",
        reconciliation_status="CONFLICT",
        group="comparison-1",
        factor="2",
    )
    await _event(
        db,
        asset,
        source="yahoo",
        source_id="yahoo-evidence",
        reconciliation_status="CONFLICT",
        group="comparison-1",
        factor="3",
    )

    group = await get_corporate_event_evidence_group(db, event_id=first.id)
    comparison = {item.field: item for item in group.comparisons}

    assert len(group.evidences) == 2
    assert group.evidences[0].raw_metadata is not None
    assert comparison["quantity_factor"].divergent is True
    assert comparison["event_type"].divergent is False
    assert group.terms_complete is True
    assert group.automatic_application_supported is True


@pytest.mark.asyncio
async def test_incomplete_complex_event_cannot_be_manually_approved(
    db: AsyncSession,
):
    reviewer = await _reviewer(db)
    asset = await _asset(db)
    event = await _event(
        db,
        asset,
        source="brapi",
        source_id="merger-incomplete",
        reconciliation_status="REVIEW_REQUIRED",
        group="merger-1",
    )
    event.event_type = "MERGER"
    event.destination_asset_id = None
    event.destination_ticker = None
    event.destination_isin_code = None

    with pytest.raises(
        CorporateEventTermsIncompleteError,
        match="destino não resolvido",
    ):
        await review_corporate_event(
            db,
            event_id=event.id,
            decision=CorporateEventReviewDecision.APPROVE,
            note="Documento não informa o ativo de destino.",
            reviewer_user_id=reviewer.id,
        )

    assert event.requires_review is True
    assert event.status == "DISCOVERED"


@pytest.mark.asyncio
async def test_complex_approval_binds_unambiguous_destination(
    db: AsyncSession,
):
    reviewer = await _reviewer(db)
    source = await _asset(db)
    destination = Asset(
        ticker="EFGH3",
        name="EFGH",
        asset_type=AssetType.ACAO.value,
        currency="BRL",
        isin_code="BREGFHACNOR1",
    )
    db.add(destination)
    await db.flush()
    event = await _event(
        db,
        source,
        source="brapi",
        source_id="merger-complete",
        reconciliation_status="REVIEW_REQUIRED",
        group="merger-2",
        factor="0.5",
    )
    event.event_type = "MERGER"
    event.destination_isin_code = "BREGFHACNOR1"
    event.destination_cost_allocation = Decimal(1)

    reviewed = await review_corporate_event(
        db,
        event_id=event.id,
        decision=CorporateEventReviewDecision.APPROVE,
        note="Destino e fator conferidos no documento oficial.",
        reviewer_user_id=reviewer.id,
    )

    assert reviewed.destination_asset_id == destination.id
    assert reviewed.destination_ticker == "EFGH3"
    assert reviewed.reconciliation_status == "MANUALLY_VALIDATED"


@pytest.mark.asyncio
async def test_projection_preview_resolves_destination_without_binding_event(
    db: AsyncSession,
):
    source = await _asset(db)
    destination = Asset(
        ticker="IJKL3",
        name="IJKL",
        asset_type=AssetType.ACAO.value,
        currency="BRL",
        isin_code="BRIJKLACNOR1",
    )
    db.add(destination)
    await db.flush()
    event = await _event(
        db,
        source,
        source="brapi",
        source_id="merger-preview",
        reconciliation_status="REVIEW_REQUIRED",
        group="merger-3",
        factor="0.5",
    )
    event.event_type = "MERGER"
    event.destination_isin_code = "BRIJKLACNOR1"
    event.destination_cost_allocation = Decimal(1)

    plan = await preview_corporate_exchange_projection(
        db,
        event_id=event.id,
        source_quantity=Decimal(100),
        total_cost=Decimal(5000),
    )

    assert plan.destination_asset_id == destination.id
    assert plan.destination_quantity_delta == Decimal(50)
    assert plan.allocated_destination_cost == Decimal(5000)
    assert plan.executable is True
    assert event.destination_asset_id is None
