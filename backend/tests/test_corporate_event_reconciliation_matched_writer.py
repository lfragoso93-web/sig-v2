from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.asset import Asset
from app.models.corporate_event import CorporateEvent
from app.models.corporate_event_reconciliation_evidence import (
    CorporateEventReconciliationEvidence,
)
from app.services.corporate_event_reconciliation_dry_run_service import (
    execute_corporate_event_matched_reconciliation,
)
from app.services.corporate_event_reconciliation_plan import (
    CorporateEventLedgerBasis,
    CorporateEventMatchEvidenceType,
    CorporateEventMatchResolutionEvidence,
    FractionalResolutionPolicy,
)


async def _create_event(
    db,
    *,
    asset: Asset,
    source_provider: str,
    source_event_id: str,
) -> CorporateEvent:
    event = CorporateEvent(
        asset_id=asset.id,
        ticker=asset.ticker,
        event_type="GRUPAMENTO",
        event_date=date(2025, 5, 29),
        ratio=Decimal("0.02"),
        effective_date=date(2025, 5, 29),
        quantity_factor=Decimal("0.02"),
        source_provider=source_provider,
        source_event_id=source_event_id,
        reconciliation_status="UNRECONCILED",
        requires_review=True,
        is_canonical=True,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@pytest.mark.asyncio
async def test_matched_writer_persists_state_and_canonical_evidence(db) -> None:
    asset = Asset(
        ticker="ABEV3",
        name="Ambev",
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()

    brapi = await _create_event(
        db,
        asset=asset,
        source_provider="brapi",
        source_event_id="brapi:test",
    )
    yahoo = await _create_event(
        db,
        asset=asset,
        source_provider="yahoo",
        source_event_id="yahoo:test",
    )

    report = await execute_corporate_event_matched_reconciliation(
        db,
        event_ids=(brapi.id, yahoo.id),
        canonical_event_id=yahoo.id,
        reason="documento oficial confirma evento canonico",
        match_resolution_evidence=CorporateEventMatchResolutionEvidence(
            evidence_type=(
                CorporateEventMatchEvidenceType.OFFICIAL_EXCHANGE_DOCUMENT
            ),
            evidence_reference="b3:test:ABEV3",
            fractional_policy=(
                FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE
            ),
        ),
    )

    assert report.dry_run is False
    assert report.decision == "MATCHED"

    assert yahoo.reconciliation_status == "MATCHED"
    assert yahoo.requires_review is False
    assert yahoo.is_canonical is True
    assert yahoo.matched_event_id is None

    assert brapi.reconciliation_status == "CONFLICT"
    assert brapi.requires_review is True
    assert brapi.is_canonical is False
    assert brapi.matched_event_id == yahoo.id

    result = await db.execute(
        select(CorporateEventReconciliationEvidence)
    )
    rows = result.scalars().all()

    assert len(rows) == 1
    evidence = rows[0]
    assert evidence.corporate_event_id == yahoo.id
    assert evidence.decision == "MATCHED"
    assert evidence.evidence_type == "OFFICIAL_EXCHANGE_DOCUMENT"
    assert evidence.evidence_reference == "b3:test:ABEV3"
    assert evidence.fractional_policy == "NO_FRACTIONAL_RESIDUE"
    assert evidence.ledger_basis is None
    assert evidence.ledger_transformation_reference is None
    assert evidence.ledger_quantity_factor is None


@pytest.mark.asyncio
async def test_matched_writer_is_idempotent_for_same_evidence(db) -> None:
    asset = Asset(
        ticker="ABEV3",
        name="Ambev",
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()

    first = await _create_event(
        db,
        asset=asset,
        source_provider="brapi",
        source_event_id="brapi:test",
    )
    canonical = await _create_event(
        db,
        asset=asset,
        source_provider="yahoo",
        source_event_id="yahoo:test",
    )

    evidence = CorporateEventMatchResolutionEvidence(
        evidence_type=CorporateEventMatchEvidenceType.OFFICIAL_EXCHANGE_DOCUMENT,
        evidence_reference="b3:test:ABEV3",
        fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
    )

    await execute_corporate_event_matched_reconciliation(
        db,
        event_ids=(first.id, canonical.id),
        canonical_event_id=canonical.id,
        reason="documento oficial confirma evento canonico",
        match_resolution_evidence=evidence,
    )

    await execute_corporate_event_matched_reconciliation(
        db,
        event_ids=(first.id, canonical.id),
        canonical_event_id=canonical.id,
        reason="documento oficial confirma evento canonico",
        match_resolution_evidence=evidence,
    )

    result = await db.execute(
        select(CorporateEventReconciliationEvidence)
    )
    rows = result.scalars().all()

    assert len(rows) == 1


@pytest.mark.asyncio
async def test_matched_writer_persists_ledger_basis_contract(db) -> None:
    asset = Asset(
        ticker="ABEV3",
        name="Ambev",
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()

    first = await _create_event(
        db,
        asset=asset,
        source_provider="brapi",
        source_event_id="brapi:ledger-basis",
    )
    canonical = await _create_event(
        db,
        asset=asset,
        source_provider="yahoo",
        source_event_id="yahoo:ledger-basis",
    )

    evidence = CorporateEventMatchResolutionEvidence(
        evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT,
        evidence_reference="broker-note:ABEV3:2025-05",
        fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
        ledger_basis=CorporateEventLedgerBasis.RAW_HISTORICAL,
        ledger_transformation_reference="broker-note:ABEV3:2025-05:ratio",
        ledger_quantity_factor="0.02",
    )

    await execute_corporate_event_matched_reconciliation(
        db,
        event_ids=(first.id, canonical.id),
        canonical_event_id=canonical.id,
        reason="documento operacional confirma base do ledger",
        match_resolution_evidence=evidence,
    )

    await execute_corporate_event_matched_reconciliation(
        db,
        event_ids=(first.id, canonical.id),
        canonical_event_id=canonical.id,
        reason="documento operacional confirma base do ledger",
        match_resolution_evidence=evidence,
    )

    result = await db.execute(
        select(CorporateEventReconciliationEvidence)
    )
    rows = result.scalars().all()

    assert len(rows) == 1
    persisted = rows[0]
    assert persisted.ledger_basis == "RAW_HISTORICAL"
    assert (
        persisted.ledger_transformation_reference
        == "broker-note:ABEV3:2025-05:ratio"
    )
    assert persisted.ledger_quantity_factor == Decimal("0.020000000000")


@pytest.mark.asyncio
async def test_matched_writer_rejects_conflicting_evidence(db) -> None:
    asset = Asset(
        ticker="ABEV3",
        name="Ambev",
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()

    first = await _create_event(
        db,
        asset=asset,
        source_provider="brapi",
        source_event_id="brapi:test",
    )
    canonical = await _create_event(
        db,
        asset=asset,
        source_provider="yahoo",
        source_event_id="yahoo:test",
    )

    await execute_corporate_event_matched_reconciliation(
        db,
        event_ids=(first.id, canonical.id),
        canonical_event_id=canonical.id,
        reason="documento oficial confirma evento canonico",
        match_resolution_evidence=CorporateEventMatchResolutionEvidence(
            evidence_type=(
                CorporateEventMatchEvidenceType.OFFICIAL_EXCHANGE_DOCUMENT
            ),
            evidence_reference="b3:test:ABEV3",
            fractional_policy=(
                FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE
            ),
        ),
    )

    with pytest.raises(ValueError, match="evidencia.*divergente"):
        await execute_corporate_event_matched_reconciliation(
            db,
            event_ids=(first.id, canonical.id),
            canonical_event_id=canonical.id,
            reason="tentativa com outra evidencia",
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=(
                    CorporateEventMatchEvidenceType.OFFICIAL_ISSUER_DOCUMENT
                ),
                evidence_reference="issuer:test:ABEV3",
                fractional_policy=(
                    FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE
                ),
            ),
        )


@pytest.mark.asyncio
async def test_matched_writer_keeps_klbn11_cash_settlement_fail_closed(db) -> None:
    asset = Asset(
        ticker="KLBN11",
        name="Klabin Unit",
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()

    brapi = await _create_event(
        db,
        asset=asset,
        source_provider="brapi",
        source_event_id="brapi:klbn11",
    )
    yahoo = await _create_event(
        db,
        asset=asset,
        source_provider="yahoo",
        source_event_id="yahoo:klbn11",
    )

    with pytest.raises(ValueError, match="KLBN11 exige contrato explicito"):
        await execute_corporate_event_matched_reconciliation(
            db,
            event_ids=(brapi.id, yahoo.id),
            canonical_event_id=brapi.id,
            reason="unit composta exige contrato proprio",
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT,
                evidence_reference="broker-note:KLBN11:2025-12",
                fractional_policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
                fractional_quantity="0.10",
                fractional_settlement_price="4.00",
                cash_treatment="AUCTION_SETTLEMENT",
            ),
        )

    assert brapi.reconciliation_status == "UNRECONCILED"
    assert brapi.requires_review is True
    assert brapi.is_canonical is True
    assert brapi.matched_event_id is None

    assert yahoo.reconciliation_status == "UNRECONCILED"
    assert yahoo.requires_review is True
    assert yahoo.is_canonical is True
    assert yahoo.matched_event_id is None

    result = await db.execute(
        select(CorporateEventReconciliationEvidence)
    )
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_matched_writer_keeps_amob3_grouping_fail_closed(db) -> None:
    asset = Asset(
        ticker="AMOB3",
        name="Automob",
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()

    brapi = await _create_event(
        db,
        asset=asset,
        source_provider="brapi",
        source_event_id="brapi:amob3",
    )
    yahoo = await _create_event(
        db,
        asset=asset,
        source_provider="yahoo",
        source_event_id="yahoo:amob3",
    )

    with pytest.raises(ValueError, match="AMOB3 exige contrato explicito"):
        await execute_corporate_event_matched_reconciliation(
            db,
            event_ids=(brapi.id, yahoo.id),
            canonical_event_id=brapi.id,
            reason="ledger pode ja estar ajustado pelo grupamento",
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=CorporateEventMatchEvidenceType.BROKER_STATEMENT,
                evidence_reference="broker-note:AMOB3:2025-05",
                fractional_policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
            ),
        )

    assert brapi.reconciliation_status == "UNRECONCILED"
    assert brapi.requires_review is True
    assert brapi.is_canonical is True
    assert brapi.matched_event_id is None

    assert yahoo.reconciliation_status == "UNRECONCILED"
    assert yahoo.requires_review is True
    assert yahoo.is_canonical is True
    assert yahoo.matched_event_id is None

    result = await db.execute(
        select(CorporateEventReconciliationEvidence)
    )
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_matched_writer_validates_complete_event_set_before_mutation(
    db,
) -> None:
    asset = Asset(
        ticker="AMOB3",
        name="Automob",
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()

    event = await _create_event(
        db,
        asset=asset,
        source_provider="brapi",
        source_event_id="brapi:test",
    )

    original_status = event.reconciliation_status
    original_review = event.requires_review
    original_canonical = event.is_canonical

    with pytest.raises(ValueError, match="eventos nao encontrados durante execucao"):
        await execute_corporate_event_matched_reconciliation(
            db,
            event_ids=(event.id, 999999),
            canonical_event_id=event.id,
            reason="nao deve aplicar parcialmente",
            match_resolution_evidence=CorporateEventMatchResolutionEvidence(
                evidence_type=(
                    CorporateEventMatchEvidenceType.OFFICIAL_EXCHANGE_DOCUMENT
                ),
                evidence_reference="b3:test:AMOB3",
                fractional_policy=(
                    FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE
                ),
            ),
        )

    assert event.reconciliation_status == original_status
    assert event.requires_review is original_review
    assert event.is_canonical is original_canonical

    result = await db.execute(
        select(CorporateEventReconciliationEvidence)
    )
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_matched_writer_changes_are_reverted_by_caller_rollback(db) -> None:
    asset = Asset(
        ticker="ABEV3",
        name="Ambev",
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()

    first = await _create_event(
        db,
        asset=asset,
        source_provider="brapi",
        source_event_id="brapi:rollback",
    )
    canonical = await _create_event(
        db,
        asset=asset,
        source_provider="yahoo",
        source_event_id="yahoo:rollback",
    )

    first_id = first.id
    canonical_id = canonical.id

    # Fixture durable; writer changes remain in a caller-owned transaction.
    await db.commit()

    await execute_corporate_event_matched_reconciliation(
        db,
        event_ids=(first_id, canonical_id),
        canonical_event_id=canonical_id,
        reason="documento oficial confirma evento canonico",
        match_resolution_evidence=CorporateEventMatchResolutionEvidence(
            evidence_type=(
                CorporateEventMatchEvidenceType.OFFICIAL_EXCHANGE_DOCUMENT
            ),
            evidence_reference="b3:test:rollback",
            fractional_policy=(
                FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE
            ),
        ),
    )

    evidence_before = await db.execute(
        select(CorporateEventReconciliationEvidence).where(
            CorporateEventReconciliationEvidence.corporate_event_id
            == canonical_id
        )
    )
    assert evidence_before.scalar_one_or_none() is not None

    canonical_before = await db.get(CorporateEvent, canonical_id)
    first_before = await db.get(CorporateEvent, first_id)

    assert canonical_before is not None
    assert first_before is not None
    assert canonical_before.reconciliation_status == "MATCHED"
    assert canonical_before.requires_review is False
    assert canonical_before.is_canonical is True
    assert first_before.reconciliation_status == "CONFLICT"
    assert first_before.is_canonical is False
    assert first_before.matched_event_id == canonical_id

    await db.rollback()
    db.expire_all()

    canonical_after = await db.get(CorporateEvent, canonical_id)
    first_after = await db.get(CorporateEvent, first_id)

    evidence_after = await db.execute(
        select(CorporateEventReconciliationEvidence).where(
            CorporateEventReconciliationEvidence.corporate_event_id
            == canonical_id
        )
    )

    assert canonical_after is not None
    assert first_after is not None

    assert canonical_after.reconciliation_status == "UNRECONCILED"
    assert canonical_after.requires_review is True
    assert canonical_after.is_canonical is True
    assert canonical_after.matched_event_id is None

    assert first_after.reconciliation_status == "UNRECONCILED"
    assert first_after.requires_review is True
    assert first_after.is_canonical is True
    assert first_after.matched_event_id is None

    assert evidence_after.scalar_one_or_none() is None
