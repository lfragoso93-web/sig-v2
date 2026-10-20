"""Regressões do leitor canônico de eventos aplicado às posições."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.corporate_event import CorporateEvent, CorporateEventStatus
from app.models.corporate_event_reconciliation_evidence import (
    CorporateEventReconciliationEvidence,
)
from app.models.transaction import OperationType, Transaction
from app.services.corporate_event_fractional_resolution import (
    FractionalResolutionPolicy,
)
from app.services.corporate_action_position_reader import (
    _effective_date,
    _fractional_resolution,
    _quantity_factor,
    _raw_payload,
    _source_identity,
    load_global_corporate_actions_by_ticker,
)
from app.services.portfolio_position_state_service import build_positions_at


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
        is_canonical=True,
        reconciliation_status="MATCHED",
        requires_review=False,
        event_date=date(2020, 1, 1),
        ratio=Decimal("9.00"),
        brapi_event_id="legacy:identity",
        raw_data='{"source":"legacy","provider_payload":{"origin":"legacy"}}',
        portfolio_id=None,
    )
    db.add(event)
    await db.flush()

    db.add(
        CorporateEventReconciliationEvidence(
            corporate_event_id=event.id,
            decision="MATCHED",
            evidence_type="OFFICIAL_ISSUER_DOCUMENT",
            evidence_reference="TEST-EVIDENCE",
            fractional_policy="NO_FRACTIONAL_RESIDUE",
        )
    )
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
    assert action.fractional_resolution is not None
    assert (
        action.fractional_resolution.policy
        == FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE
    )


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


def test_reader_does_not_use_b3_record_date_as_effective_date() -> None:
    event = CorporateEvent(
        id=43,
        asset_id=1,
        ticker="NIKE34",
        event_type="GRUPAMENTO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=None,
        quantity_factor=Decimal("0.2"),
        source_provider="b3",
        source_event_id="b3:nike-reverse-split",
        event_date=date(2026, 10, 9),
        portfolio_id=None,
    )

    with pytest.raises(ValueError, match="sem data efetiva"):
        _effective_date(event)


@pytest.mark.asyncio
async def test_reader_transports_cash_settlement_evidence(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="FRAC3",
        name="Ativo fracionario",
        asset_type=AssetType.ACAO.value,
    )
    db.add(asset)
    await db.flush()

    event = CorporateEvent(
        asset_id=asset.id,
        ticker="FRAC3",
        event_type="BONIFICACAO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=date(2026, 2, 10),
        ratio=Decimal("1.01"),
        quantity_factor=Decimal("1.01"),
        source_provider="brapi",
        source_event_id="brapi:fraction",
        event_date=date(2026, 2, 10),
        is_canonical=True,
        reconciliation_status="MATCHED",
        requires_review=False,
        portfolio_id=None,
    )
    db.add(event)
    await db.flush()

    db.add(
        CorporateEventReconciliationEvidence(
            corporate_event_id=event.id,
            decision="MATCHED",
            evidence_type="OFFICIAL_ISSUER_DOCUMENT",
            evidence_reference="TEST-CASH",
            fractional_policy="CASH_SETTLEMENT",
            fractional_quantity=Decimal("0.10"),
            fractional_settlement_price=Decimal("3.94"),
            cash_treatment="AUCTION_SETTLEMENT",
        )
    )
    await db.flush()

    loaded = await load_global_corporate_actions_by_ticker(db, ["FRAC3"])

    action = loaded["FRAC3"][0]
    resolution = action.fractional_resolution

    assert resolution is not None
    assert resolution.policy == FractionalResolutionPolicy.CASH_SETTLEMENT
    assert resolution.fractional_quantity == Decimal("0.10")
    assert resolution.settlement_price == Decimal("3.94")
    assert resolution.cash_treatment == "AUCTION_SETTLEMENT"


@pytest.mark.asyncio
async def test_cash_settlement_reaches_position_state_without_ledger_mutation(
    db: AsyncSession,
    portfolio,
) -> None:
    asset = Asset(
        ticker="FRAC3",
        name="Ativo fracionario",
        asset_type=AssetType.ACAO.value,
    )
    db.add(asset)
    await db.flush()

    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="FRAC3",
            asset_type=AssetType.ACAO.value,
            operation=OperationType.buy,
            quantity=Decimal("10"),
            price=Decimal("18.53"),
            fees=Decimal("0"),
            date=date(2026, 1, 1),
            currency="BRL",
        )
    )

    event = CorporateEvent(
        asset_id=asset.id,
        ticker="FRAC3",
        event_type="BONIFICACAO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=date(2026, 1, 2),
        ratio=Decimal("1.01"),
        quantity_factor=Decimal("1.01"),
        source_provider="brapi",
        source_event_id="brapi:fraction-e2e",
        event_date=date(2026, 1, 2),
        is_canonical=True,
        reconciliation_status="MATCHED",
        requires_review=False,
        portfolio_id=None,
    )
    db.add(event)
    await db.flush()

    db.add(
        CorporateEventReconciliationEvidence(
            corporate_event_id=event.id,
            decision="MATCHED",
            evidence_type="BROKER_STATEMENT",
            evidence_reference="broker-note:FRAC3:2026-01",
            fractional_policy="CASH_SETTLEMENT",
            fractional_quantity=Decimal("0.10"),
            fractional_settlement_price=Decimal("4.00"),
            cash_treatment="AUCTION_SETTLEMENT",
        )
    )
    await db.flush()

    states = await build_positions_at(db, portfolio.id, date(2026, 1, 3))

    state = states["FRAC3"]
    fractional_cost = Decimal("185.30") * (
        Decimal("0.10") / Decimal("10.10")
    )
    assert state.qty == Decimal("10")
    assert state.cost == Decimal("185.30") - fractional_cost
    assert state.realized_pnl == Decimal("0.4000") - fractional_cost
    assert len(state.corporate_action_cash_flows) == 1
    cash_flow = state.corporate_action_cash_flows[0]
    assert cash_flow.source_event_id == "brapi:fraction-e2e"
    assert cash_flow.gross_amount_brl == Decimal("0.4000")
    assert cash_flow.cost_basis_brl == fractional_cost
    assert cash_flow.realized_pnl_brl == Decimal("0.4000") - fractional_cost


@pytest.mark.asyncio
async def test_pending_fraction_is_excluded_from_canonical_position_state(
    db: AsyncSession,
    portfolio,
) -> None:
    asset = Asset(
        ticker="PEND3",
        name="Ativo com fração pendente",
        asset_type=AssetType.ACAO.value,
    )
    db.add(asset)
    await db.flush()

    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="PEND3",
            asset_type=AssetType.ACAO.value,
            operation=OperationType.buy,
            quantity=Decimal("6"),
            price=Decimal("100"),
            fees=Decimal("0"),
            date=date(2026, 1, 1),
            currency="BRL",
        )
    )
    event = CorporateEvent(
        asset_id=asset.id,
        ticker="PEND3",
        event_type="GRUPAMENTO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=date(2026, 1, 2),
        ratio=Decimal("0.2"),
        quantity_factor=Decimal("0.2"),
        source_provider="brapi",
        source_event_id="brapi:pending-fraction",
        event_date=date(2026, 1, 2),
        is_canonical=True,
        reconciliation_status="MATCHED",
        requires_review=False,
        portfolio_id=None,
    )
    db.add(event)
    await db.flush()
    db.add(
        CorporateEventReconciliationEvidence(
            corporate_event_id=event.id,
            decision="MATCHED",
            evidence_type="BROKER_STATEMENT",
            evidence_reference="broker-note:PEND3:2026-01",
            fractional_policy="PENDING_SETTLEMENT",
            fractional_quantity=Decimal("0.2"),
        )
    )
    await db.flush()

    states = await build_positions_at(db, portfolio.id, date(2026, 1, 3))

    assert states["PEND3"].qty == Decimal("1")
    assert states["PEND3"].cost == Decimal("500")


@pytest.mark.asyncio
async def test_reader_fails_closed_for_matched_event_without_evidence(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="MISS3",
        name="Ativo sem evidencia",
        asset_type=AssetType.ACAO.value,
    )
    db.add(asset)
    await db.flush()

    event = CorporateEvent(
        asset_id=asset.id,
        ticker="MISS3",
        event_type="BONIFICACAO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=date(2026, 2, 10),
        ratio=Decimal("1.01"),
        quantity_factor=Decimal("1.01"),
        source_provider="brapi",
        source_event_id="brapi:missing-evidence",
        event_date=date(2026, 2, 10),
        is_canonical=True,
        reconciliation_status="MATCHED",
        requires_review=False,
        portfolio_id=None,
    )
    db.add(event)
    await db.flush()

    with pytest.raises(
        ValueError,
        match="sem evidencia de reconciliacao",
    ):
        await load_global_corporate_actions_by_ticker(db, ["MISS3"])


@pytest.mark.asyncio
async def test_reader_fails_closed_for_amob3_matched_without_ledger_basis(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="AMOB3",
        name="Automob",
        asset_type=AssetType.ACAO.value,
    )
    db.add(asset)
    await db.flush()

    event = CorporateEvent(
        asset_id=asset.id,
        ticker="AMOB3",
        event_type="GRUPAMENTO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=date(2025, 5, 29),
        ratio=Decimal("0.02"),
        quantity_factor=Decimal("0.02"),
        source_provider="yahoo",
        source_event_id="yahoo:AMOB3:2025-05-29",
        event_date=date(2025, 5, 29),
        is_canonical=True,
        reconciliation_status="MATCHED",
        requires_review=False,
        portfolio_id=None,
    )
    db.add(event)
    await db.flush()

    db.add(
        CorporateEventReconciliationEvidence(
            corporate_event_id=event.id,
            decision="MATCHED",
            evidence_type="OFFICIAL_ISSUER_DOCUMENT",
            evidence_reference="AUTOMOB:AVISO:2025-04-25",
            fractional_policy="NO_FRACTIONAL_RESIDUE",
        )
    )
    await db.flush()

    with pytest.raises(ValueError, match="AMOB3 exige base do ledger"):
        await load_global_corporate_actions_by_ticker(db, ["AMOB3"])


@pytest.mark.asyncio
async def test_reader_allows_amob3_matched_with_persisted_ledger_basis(
    db: AsyncSession,
) -> None:
    asset = Asset(
        ticker="AMOB3",
        name="Automob",
        asset_type=AssetType.ACAO.value,
    )
    db.add(asset)
    await db.flush()

    event = CorporateEvent(
        asset_id=asset.id,
        ticker="AMOB3",
        event_type="GRUPAMENTO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=date(2025, 5, 29),
        ratio=Decimal("0.02"),
        quantity_factor=Decimal("0.02"),
        source_provider="yahoo",
        source_event_id="yahoo:AMOB3:2025-05-29",
        event_date=date(2025, 5, 29),
        is_canonical=True,
        reconciliation_status="MATCHED",
        requires_review=False,
        portfolio_id=None,
    )
    db.add(event)
    await db.flush()

    db.add(
        CorporateEventReconciliationEvidence(
            corporate_event_id=event.id,
            decision="MATCHED",
            evidence_type="OFFICIAL_ISSUER_DOCUMENT",
            evidence_reference="AUTOMOB:AVISO:2025-04-25",
            fractional_policy="NO_FRACTIONAL_RESIDUE",
            ledger_basis="RAW_HISTORICAL",
            ledger_transformation_reference="AUTOMOB:LEDGER-BASIS",
            ledger_quantity_factor=Decimal("0.02"),
        )
    )
    await db.flush()

    loaded = await load_global_corporate_actions_by_ticker(db, ["AMOB3"])

    assert len(loaded["AMOB3"]) == 1
    assert loaded["AMOB3"][0].quantity_factor == Decimal("0.02")


def test_fractional_resolution_keeps_legacy_compatibility() -> None:
    event = CorporateEvent(
        id=99,
        asset_id=1,
        ticker="LEG3",
        event_type="DESDOBRAMENTO",
        status=CorporateEventStatus.PENDENTE.value,
        effective_date=date(2026, 3, 1),
        quantity_factor=Decimal("2"),
        source_provider="legacy",
        portfolio_id=None,
    )

    assert _fractional_resolution(event, None) is None
