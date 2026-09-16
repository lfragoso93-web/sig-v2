from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent, CorporateEventStatus
from app.services.corporate_action_engine import (
    normalize_brapi_corporate_actions,
    source_payload_hash,
)
from app.services.corporate_event_semantic_repair import (
    CorporateEventSemanticRepairError,
    build_corporate_event_semantic_repair_plan,
    build_corporate_event_semantic_repair_dry_run,
    execute_corporate_event_semantic_repair,
)


def _raw(label: str = "GRUPAMENTO", factor: str = "0.1") -> dict[str, object]:
    return {
        "label": label,
        "lastDatePrior": "2024-07-10",
        "factor": factor,
        "assetIssued": "AMOB3",
    }


def _event(**overrides: object) -> CorporateEvent:
    values = {
        "id": 370,
        "asset_id": 1,
        "ticker": "AMOB3",
        "event_type": "BONIFICACAO",
        "status": CorporateEventStatus.PENDENTE.value,
        "event_date": date(2024, 7, 10),
        "ratio": Decimal("0.1"),
        "source_provider": "brapi",
        "source_event_id": "brapi:old",
        "source_payload_hash": "old-hash",
        "raw_metadata": _raw(),
        "portfolio_id": None,
        "effective_date": date(2024, 7, 10),
        "quantity_factor": Decimal("0.1"),
        "reconciliation_status": "UNRECONCILED",
        "requires_review": True,
        "is_canonical": True,
        "matched_event_id": None,
        "brapi_event_id": None,
    }
    values.update(overrides)
    return CorporateEvent(**values)


def _action_for(event: CorporateEvent):
    payload = {
        "results": [
            {
                "symbol": event.ticker,
                "data": {
                    "stockDividends": [dict(event.raw_metadata)],
                    "subscriptions": [],
                },
            }
        ]
    }
    return normalize_brapi_corporate_actions(event.ticker, payload)[0]


def test_amob3_like_grupamento_generates_dry_run_candidate() -> None:
    event = _event()

    report = build_corporate_event_semantic_repair_plan([event])

    [candidate] = report.candidates
    assert report.total_candidates == 1
    assert candidate.event_id == 370
    assert candidate.ticker == "AMOB3"
    assert candidate.old_event_type == "BONIFICACAO"
    assert candidate.new_event_type == "GRUPAMENTO"
    assert candidate.old_source_event_id == "brapi:old"
    assert candidate.new_source_event_id != "brapi:old"
    assert candidate.old_source_payload_hash == "old-hash"
    assert candidate.new_source_payload_hash != "old-hash"
    assert candidate.event_date == date(2024, 7, 10)
    assert candidate.quantity_factor == Decimal("0.1")
    assert report.to_dict()["database_writes_executed"] == 0


def test_desdobramento_generates_dry_run_candidate() -> None:
    event = _event(
        ticker="TEST3",
        raw_metadata=_raw("DESDOBRAMENTO", "5"),
        quantity_factor=Decimal("5"),
        ratio=Decimal("5"),
    )

    report = build_corporate_event_semantic_repair_plan([event])

    [candidate] = report.candidates
    assert candidate.new_event_type == "DESDOBRAMENTO"
    assert candidate.quantity_factor == Decimal("5")


@pytest.mark.parametrize("label", ["BONIFICACAO", "INCORPORACAO"])
def test_non_repairable_labels_are_rejected(label: str) -> None:
    event = _event(raw_metadata=_raw(label))

    with pytest.raises(CorporateEventSemanticRepairError, match="label fora do escopo"):
        build_corporate_event_semantic_repair_plan([event])


def test_matched_event_is_rejected() -> None:
    event = _event(reconciliation_status="MATCHED")

    with pytest.raises(CorporateEventSemanticRepairError, match="UNRECONCILED"):
        build_corporate_event_semantic_repair_plan([event])


def test_requires_review_false_is_rejected() -> None:
    event = _event(requires_review=False)

    with pytest.raises(CorporateEventSemanticRepairError, match="requires_review"):
        build_corporate_event_semantic_repair_plan([event])


def test_filled_matched_event_id_is_rejected() -> None:
    event = _event(matched_event_id=123)

    with pytest.raises(CorporateEventSemanticRepairError, match="matched_event_id"):
        build_corporate_event_semantic_repair_plan([event])


def test_existing_new_identity_collision_is_rejected() -> None:
    event = _event()
    action = _action_for(event)

    with pytest.raises(CorporateEventSemanticRepairError, match="nova identidade"):
        build_corporate_event_semantic_repair_plan(
            [event],
            existing_source_identities={(action.source, action.source_event_id)},
        )


def test_semantically_correct_event_is_rejected() -> None:
    event = _event()
    action = _action_for(event)
    event.event_type = action.kind.value
    event.source_event_id = action.source_event_id
    event.source_payload_hash = source_payload_hash(action)

    with pytest.raises(CorporateEventSemanticRepairError, match="sem mudanca"):
        build_corporate_event_semantic_repair_plan([event])


def test_dry_run_does_not_mutate_event_properties() -> None:
    event = _event()
    before = deepcopy(event.__dict__)

    build_corporate_event_semantic_repair_plan([event])

    after = event.__dict__
    for key, value in before.items():
        if key != "_sa_instance_state":
            assert after[key] == value


@pytest.mark.asyncio
async def test_database_dry_run_does_not_mutate_event(db: AsyncSession) -> None:
    event = _event()
    db.add(event)
    await db.flush()

    report = await build_corporate_event_semantic_repair_dry_run(
        db,
        event_ids=(int(event.id),),
    )

    [candidate] = report.candidates
    assert report.dry_run is True
    assert report.database_writes_executed == 0
    assert candidate.new_event_type == "GRUPAMENTO"
    assert event.event_type == "BONIFICACAO"
    assert event.source_event_id == "brapi:old"
    assert event.source_payload_hash == "old-hash"
    assert event.reconciliation_status == "UNRECONCILED"
    assert event.requires_review is True
    assert event.is_canonical is True
    assert event.matched_event_id is None


@pytest.mark.asyncio
async def test_execute_repairs_only_semantic_identity_fields(db: AsyncSession) -> None:
    event = _event()
    db.add(event)
    await db.flush()
    original_status = event.reconciliation_status
    original_requires_review = event.requires_review
    original_is_canonical = event.is_canonical
    original_matched_event_id = event.matched_event_id
    original_raw_metadata = dict(event.raw_metadata)
    original_quantity_factor = event.quantity_factor

    report = await execute_corporate_event_semantic_repair(
        db,
        event_ids=(int(event.id),),
    )

    [candidate] = report.candidates
    assert report.dry_run is False
    assert report.database_writes_executed == 1
    assert event.event_type == "GRUPAMENTO"
    assert event.source_event_id == candidate.new_source_event_id
    assert event.source_payload_hash == candidate.new_source_payload_hash
    assert event.reconciliation_status == original_status
    assert event.requires_review == original_requires_review
    assert event.is_canonical == original_is_canonical
    assert event.matched_event_id == original_matched_event_id
    assert event.raw_metadata == original_raw_metadata
    assert event.quantity_factor == original_quantity_factor


@pytest.mark.asyncio
async def test_database_execution_rejects_existing_identity_collision(
    db: AsyncSession,
) -> None:
    event = _event()
    action = _action_for(event)
    colliding = _event(
        id=371,
        ticker="ZZZZ3",
        source_event_id=action.source_event_id,
        raw_metadata=_raw("DESDOBRAMENTO", "2"),
        quantity_factor=Decimal("2"),
        ratio=Decimal("2"),
    )
    db.add_all([event, colliding])
    await db.flush()

    with pytest.raises(CorporateEventSemanticRepairError, match="nova identidade"):
        await execute_corporate_event_semantic_repair(db, event_ids=(int(event.id),))

    assert event.event_type == "BONIFICACAO"
    assert event.source_event_id == "brapi:old"


@pytest.mark.asyncio
async def test_database_dry_run_rejects_semantically_correct_event(
    db: AsyncSession,
) -> None:
    event = _event()
    action = _action_for(event)
    event.event_type = action.kind.value
    event.source_event_id = action.source_event_id
    event.source_payload_hash = source_payload_hash(action)
    db.add(event)
    await db.flush()

    with pytest.raises(CorporateEventSemanticRepairError, match="sem mudanca"):
        await build_corporate_event_semantic_repair_dry_run(
            db,
            event_ids=(int(event.id),),
        )
