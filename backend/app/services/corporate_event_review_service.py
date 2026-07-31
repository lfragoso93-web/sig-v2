"""Fila e decisões administrativas auditáveis para eventos corporativos."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import (
    CorporateEvent,
    CorporateEventReconciliationStatus,
    CorporateEventStatus,
)
from app.schemas.corporate_event_review import (
    CorporateEventEvidence,
    CorporateEventEvidenceComparison,
    CorporateEventEvidenceGroup,
    CorporateEventReviewDecision,
)
from app.services.audit_log_service import AuditLogService
from app.services.corporate_destination_asset_service import (
    DestinationResolutionStatus,
    resolve_corporate_destination_asset,
)
from app.services.corporate_event_terms_service import assess_corporate_event_terms
from app.services.corporate_exchange_projection_service import (
    CorporateExchangeProjectionPlan,
    build_corporate_exchange_projection_plan,
)


class CorporateEventReviewNotFoundError(LookupError):
    pass


class CorporateEventAlreadyReviewedError(RuntimeError):
    pass


class CorporateEventReviewConflictError(RuntimeError):
    pass


class CorporateEventTermsIncompleteError(RuntimeError):
    pass


def _audit_snapshot(event: CorporateEvent) -> dict[str, object]:
    return {
        "status": str(event.status),
        "reconciliation_status": str(event.reconciliation_status),
        "is_canonical": bool(event.is_canonical),
        "requires_review": bool(event.requires_review),
        "review_reason": event.review_reason,
        "reviewed_by_user_id": event.reviewed_by_user_id,
        "review_note": event.review_note,
        "quantity_factor": str(Decimal(str(event.quantity_factor))),
    }


def _comparison_value(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


async def get_corporate_event_evidence_group(
    db: AsyncSession,
    *,
    event_id: int,
) -> CorporateEventEvidenceGroup:
    selected_result = await db.execute(
        select(CorporateEvent).where(
            CorporateEvent.id == event_id,
            CorporateEvent.portfolio_id.is_(None),
        )
    )
    selected = selected_result.scalar_one_or_none()
    if selected is None:
        raise CorporateEventReviewNotFoundError(event_id)

    if selected.reconciliation_group_hash:
        group_result = await db.execute(
            select(CorporateEvent)
            .where(
                CorporateEvent.asset_id == selected.asset_id,
                CorporateEvent.reconciliation_group_hash
                == selected.reconciliation_group_hash,
                CorporateEvent.portfolio_id.is_(None),
            )
            .order_by(CorporateEvent.source_provider, CorporateEvent.id)
        )
        rows = list(group_result.scalars().all())
    else:
        rows = [selected]

    fields = (
        "event_type",
        "effective_date",
        "record_date",
        "ex_date",
        "payment_date",
        "quantity_factor",
        "cash_component",
        "subscription_price",
        "destination_cost_allocation",
        "quantity_step",
        "fractional_settlement_price",
        "cash_treatment",
        "currency",
        "isin_code",
        "destination_isin_code",
    )
    comparisons: list[CorporateEventEvidenceComparison] = []
    for field in fields:
        values = {str(row.id): _comparison_value(getattr(row, field)) for row in rows}
        comparisons.append(
            CorporateEventEvidenceComparison(
                field=field,
                values=values,
                divergent=len(set(values.values())) > 1,
            )
        )

    assessment = assess_corporate_event_terms(selected)
    resolution = None
    if assessment.economic_effect.value in {
        "DESTINATION_ASSET_EXCHANGE",
        "TERMINATION",
    }:
        resolution = await resolve_corporate_destination_asset(db, selected)
    return CorporateEventEvidenceGroup(
        selected_event_id=selected.id,
        reconciliation_group_hash=selected.reconciliation_group_hash,
        evidences=[CorporateEventEvidence.model_validate(row) for row in rows],
        comparisons=comparisons,
        economic_effect=assessment.economic_effect.value,
        terms_complete=assessment.complete,
        automatic_application_supported=assessment.automatic_application_supported,
        missing_terms=list(assessment.missing_terms),
        destination_resolution_status=(resolution.status.value if resolution else None),
        destination_asset_id=(resolution.asset_id if resolution else None),
        destination_ticker=(resolution.ticker if resolution else None),
        destination_candidate_ids=(
            list(resolution.candidate_ids) if resolution else []
        ),
    )


async def preview_corporate_exchange_projection(
    db: AsyncSession,
    *,
    event_id: int,
    source_quantity: Decimal,
    total_cost: Decimal,
) -> CorporateExchangeProjectionPlan:
    result = await db.execute(
        select(CorporateEvent).where(
            CorporateEvent.id == event_id,
            CorporateEvent.portfolio_id.is_(None),
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise CorporateEventReviewNotFoundError(event_id)

    resolution = await resolve_corporate_destination_asset(db, event)
    if resolution.status is not DestinationResolutionStatus.RESOLVED:
        raise CorporateEventTermsIncompleteError(
            f"ativo de destino não resolvido: {resolution.status.value.lower()}"
        )
    return build_corporate_exchange_projection_plan(
        event,
        source_quantity=source_quantity,
        total_cost=total_cost,
        resolved_destination_asset_id=resolution.asset_id,
    )


async def list_corporate_events_for_review(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    ticker: str | None = None,
    reconciliation_status: str | None = None,
) -> tuple[list[CorporateEvent], int]:
    filters = [
        CorporateEvent.portfolio_id.is_(None),
        CorporateEvent.requires_review.is_(True),
        or_(
            CorporateEvent.is_canonical.is_(True),
            CorporateEvent.reconciliation_status
            == CorporateEventReconciliationStatus.CONFLICT.value,
        ),
    ]
    if ticker:
        filters.append(CorporateEvent.ticker == ticker.strip().upper())
    if reconciliation_status:
        filters.append(
            CorporateEvent.reconciliation_status == reconciliation_status.upper()
        )

    total = int(
        (
            await db.execute(select(func.count(CorporateEvent.id)).where(*filters))
        ).scalar_one()
        or 0
    )
    rows = await db.execute(
        select(CorporateEvent)
        .where(*filters)
        .order_by(CorporateEvent.effective_date.desc(), CorporateEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows.scalars().all()), total


async def review_corporate_event(
    db: AsyncSession,
    *,
    event_id: int,
    decision: CorporateEventReviewDecision,
    note: str,
    reviewer_user_id: int,
) -> CorporateEvent:
    result = await db.execute(
        select(CorporateEvent).where(CorporateEvent.id == event_id).with_for_update()
    )
    event = result.scalar_one_or_none()
    if event is None or event.portfolio_id is not None:
        raise CorporateEventReviewNotFoundError(event_id)
    if not event.requires_review:
        raise CorporateEventAlreadyReviewedError(event_id)

    old_values = _audit_snapshot(event)
    now = datetime.now(UTC)
    rejected_peer_ids: list[int] = []

    if decision is CorporateEventReviewDecision.APPROVE:
        assessment = assess_corporate_event_terms(event)
        if assessment.economic_effect.value == "DESTINATION_ASSET_EXCHANGE" or (
            assessment.economic_effect.value == "TERMINATION"
            and not event.cash_component
        ):
            resolution = await resolve_corporate_destination_asset(db, event, bind=True)
            if resolution.status is not DestinationResolutionStatus.RESOLVED:
                raise CorporateEventTermsIncompleteError(
                    f"ativo de destino não resolvido: {resolution.status.value.lower()}"
                )
            assessment = assess_corporate_event_terms(event)
        if not assessment.complete:
            missing = ", ".join(assessment.missing_terms)
            raise CorporateEventTermsIncompleteError(
                f"termos econômicos incompletos: {missing}"
            )
        is_conflict = (
            event.reconciliation_status
            == CorporateEventReconciliationStatus.CONFLICT.value
        )
        if not is_conflict and not event.is_canonical:
            raise CorporateEventReviewConflictError(
                "somente a evidência canônica pode ser aprovada"
            )
        peers: list[CorporateEvent] = []
        if is_conflict:
            if not event.reconciliation_group_hash:
                raise CorporateEventReviewConflictError(
                    "conflito sem grupo de reconciliação"
                )
            peer_result = await db.execute(
                select(CorporateEvent)
                .where(
                    CorporateEvent.asset_id == event.asset_id,
                    CorporateEvent.reconciliation_group_hash
                    == event.reconciliation_group_hash,
                    CorporateEvent.id != event.id,
                )
                .with_for_update()
            )
            peers = list(peer_result.scalars().all())
            for peer in peers:
                peer.status = CorporateEventStatus.REJECTED.value
                peer.is_canonical = False
                peer.requires_review = False
                peer.review_reason = "evidência concorrente rejeitada em revisão manual"
                peer.reviewed_at = now
                peer.reviewed_by_user_id = reviewer_user_id
                peer.review_note = note
                rejected_peer_ids.append(int(peer.id))

        event.status = CorporateEventStatus.VALIDATED.value
        event.reconciliation_status = (
            CorporateEventReconciliationStatus.MANUALLY_VALIDATED.value
        )
        event.is_canonical = True
        event.requires_review = False
        event.review_reason = None
    else:
        event.status = CorporateEventStatus.REJECTED.value
        event.requires_review = False
        event.review_reason = "evento rejeitado em revisão manual"

    event.reviewed_at = now
    event.reviewed_by_user_id = reviewer_user_id
    event.review_note = note.strip()
    await db.flush()

    new_values = _audit_snapshot(event)
    new_values["decision"] = decision.value
    new_values["rejected_peer_ids"] = rejected_peer_ids
    await AuditLogService.log_action(
        db,
        user_id=reviewer_user_id,
        action="UPDATE",
        resource_type="CORPORATE_EVENT_REVIEW",
        resource_id=event.id,
        old_values=old_values,
        new_values=new_values,
    )
    return event
