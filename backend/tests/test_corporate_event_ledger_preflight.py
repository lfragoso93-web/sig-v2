from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.asset import Asset
from app.models.corporate_event import CorporateEvent
from app.models.transaction import OperationType, Transaction
from app.services.corporate_event_ledger_preflight import (
    build_corporate_event_ledger_preflight_report,
    read_corporate_event_ledger_preflight,
    read_ledger_transaction_preflight,
)
from app.services.corporate_event_reconciliation_dry_run_service import (
    build_corporate_event_reconciliation_dry_run,
)
from app.services.corporate_event_reconciliation_plan import (
    CorporateEventReconciliationDecision,
)


@pytest.mark.asyncio
async def test_ledger_preflight_is_read_only_and_aggregates_transactions(
    db, portfolio
) -> None:
    db.add_all(
        [
            Transaction(
                portfolio_id=portfolio.id,
                ticker="amob3",
                asset_type="ACAO",
                operation=OperationType.buy,
                quantity=Decimal("100"),
                price=Decimal("0.35"),
                date=date(2024, 1, 10),
                currency="BRL",
            ),
            Transaction(
                portfolio_id=portfolio.id,
                ticker="AMOB3",
                asset_type="ACAO",
                operation=OperationType.buy,
                quantity=Decimal("200"),
                price=Decimal("0.26"),
                date=date(2024, 2, 10),
                currency="BRL",
            ),
            Transaction(
                portfolio_id=portfolio.id,
                ticker="AMOB3",
                asset_type="ACAO",
                operation=OperationType.sell,
                quantity=Decimal("6"),
                price=Decimal("13.80"),
                date=date(2025, 1, 10),
                currency="BRL",
            ),
        ]
    )
    await db.flush()
    before = await db.scalar(select(func.count()).select_from(Transaction))

    snapshot = await read_ledger_transaction_preflight(
        db,
        portfolio_id=portfolio.id,
        ticker=" amob3 ",
        as_of=date(2025, 1, 10),
    )

    after = await db.scalar(select(func.count()).select_from(Transaction))
    assert snapshot.transaction_count == 3
    assert snapshot.buy_quantity == Decimal("300")
    assert snapshot.sell_quantity == Decimal("6")
    assert snapshot.net_quantity == Decimal("294")
    assert snapshot.first_transaction_date == date(2024, 1, 10)
    assert snapshot.last_transaction_date == date(2025, 1, 10)
    assert before == after == 3


@pytest.mark.asyncio
async def test_ledger_preflight_excludes_future_transactions(db, portfolio) -> None:
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="AMOB3",
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal("10"),
            price=Decimal("1"),
            date=date(2026, 1, 1),
            currency="BRL",
        )
    )
    await db.flush()

    snapshot = await read_ledger_transaction_preflight(
        db,
        portfolio_id=portfolio.id,
        ticker="AMOB3",
        as_of=date(2025, 12, 31),
    )

    assert snapshot.transaction_ids == ()
    assert snapshot.net_quantity == Decimal("0")


@pytest.mark.asyncio
async def test_ledger_preflight_requires_ticker(db, portfolio) -> None:
    with pytest.raises(ValueError, match="ticker e obrigatorio"):
        await read_ledger_transaction_preflight(
            db,
            portfolio_id=portfolio.id,
            ticker=" ",
            as_of=date(2025, 1, 1),
        )


@pytest.mark.asyncio
async def test_corporate_event_preflight_projects_quantity_without_writing(
    db, portfolio
) -> None:
    asset = Asset(ticker="AMOB3", name="Automob", asset_type="ACAO", currency="BRL")
    db.add(asset)
    await db.flush()
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="AMOB3",
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal("300"),
            price=Decimal("0.30"),
            date=date(2024, 1, 1),
            currency="BRL",
        )
    )
    event = CorporateEvent(
        asset_id=asset.id,
        ticker="AMOB3",
        event_type="GRUPAMENTO",
        event_date=date(2025, 1, 1),
        ratio=Decimal("0.02"),
        effective_date=date(2025, 1, 1),
        quantity_factor=Decimal("0.02"),
        portfolio_id=portfolio.id,
        source_provider="test",
    )
    db.add(event)
    await db.flush()
    before = await db.scalar(select(func.count()).select_from(Transaction))

    preflight = await read_corporate_event_ledger_preflight(db, event)

    after = await db.scalar(select(func.count()).select_from(Transaction))
    assert preflight.quantity_factor == Decimal("0.02")
    assert preflight.ledger.net_quantity == Decimal("300")
    assert preflight.projected_net_quantity == Decimal("6")
    assert before == after == 1


@pytest.mark.asyncio
async def test_nike34_grouping_preflight_exposes_fractional_residue(
    db, portfolio
) -> None:
    asset = Asset(ticker="NIKE34", name="Nike", asset_type="BDR", currency="BRL")
    db.add(asset)
    await db.flush()
    db.add_all(
        [
            Transaction(
                portfolio_id=portfolio.id,
                ticker="NIKE34",
                asset_type="BDR",
                operation=OperationType.buy,
                quantity=quantity,
                price=price,
                date=transaction_date,
                currency="BRL",
            )
            for quantity, price, transaction_date in (
                (Decimal("1"), Decimal("44.50"), date(2025, 2, 3)),
                (Decimal("2"), Decimal("32.75"), date(2025, 5, 5)),
                (Decimal("3"), Decimal("22.15"), date(2026, 4, 30)),
            )
        ]
    )
    event = CorporateEvent(
        asset_id=asset.id,
        ticker="NIKE34",
        event_type="GRUPAMENTO",
        event_date=date(2026, 10, 13),
        ratio=Decimal("0.2"),
        effective_date=date(2026, 10, 13),
        quantity_factor=Decimal("0.2"),
        source_provider="test",
    )
    db.add(event)
    await db.flush()

    report = await build_corporate_event_ledger_preflight_report(
        db,
        event,
        portfolio_id=portfolio.id,
    )

    payload = report.to_dict()
    assert payload["schema_version"] == "corporate-event-ledger-preflight.v3"
    assert payload["dry_run"] is True
    assert payload["database_writes_executed"] == 0
    assert payload["ready_for_execution"] is False
    assert payload["net_quantity"] == "6.00000000"
    assert payload["projected_net_quantity"] == "1.200000000"
    assert payload["projected_whole_quantity"] == "1"
    assert payload["projected_fractional_quantity"] == "0.200000000"


@pytest.mark.asyncio
async def test_corporate_event_preflight_requires_explicit_portfolio(db, portfolio) -> None:
    asset = Asset(ticker="AMOB3", name="Automob", asset_type="ACAO", currency="BRL")
    db.add(asset)
    await db.flush()
    event = CorporateEvent(
        asset_id=asset.id,
        ticker="AMOB3",
        event_type="GRUPAMENTO",
        event_date=date(2025, 1, 1),
        ratio=Decimal("0.02"),
        effective_date=date(2025, 1, 1),
        quantity_factor=Decimal("0.02"),
        source_provider="test",
    )

    with pytest.raises(ValueError, match="portfolio_id explicito"):
        await read_corporate_event_ledger_preflight(db, event)


@pytest.mark.asyncio
async def test_corporate_event_preflight_accepts_portfolio_for_global_event(
    db, portfolio
) -> None:
    asset = Asset(ticker="AMOB3", name="Automob", asset_type="ACAO", currency="BRL")
    db.add(asset)
    await db.flush()
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="AMOB3",
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal("300"),
            price=Decimal("0.30"),
            date=date(2024, 1, 1),
            currency="BRL",
        )
    )
    event = CorporateEvent(
        asset_id=asset.id,
        ticker="AMOB3",
        event_type="GRUPAMENTO",
        event_date=date(2025, 1, 1),
        ratio=Decimal("0.02"),
        effective_date=date(2025, 1, 1),
        quantity_factor=Decimal("0.02"),
        source_provider="test",
    )
    db.add(event)
    await db.flush()

    preflight = await read_corporate_event_ledger_preflight(
        db,
        event,
        portfolio_id=portfolio.id,
    )

    assert preflight.ledger.portfolio_id == portfolio.id
    assert preflight.ledger.net_quantity == Decimal("300")
    assert preflight.projected_net_quantity == Decimal("6")


@pytest.mark.asyncio
async def test_corporate_event_preflight_report_is_versioned_and_read_only(
    db, portfolio
) -> None:
    asset = Asset(ticker="AMOB3", name="Automob", asset_type="ACAO", currency="BRL")
    db.add(asset)
    await db.flush()
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="AMOB3",
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal("300"),
            price=Decimal("0.30"),
            date=date(2024, 1, 1),
            currency="BRL",
        )
    )
    event = CorporateEvent(
        asset_id=asset.id,
        ticker="AMOB3",
        event_type="GRUPAMENTO",
        event_date=date(2025, 1, 1),
        ratio=Decimal("0.02"),
        effective_date=date(2025, 1, 1),
        quantity_factor=Decimal("0.02"),
        portfolio_id=portfolio.id,
        source_provider="test",
    )
    db.add(event)
    await db.flush()

    report = await build_corporate_event_ledger_preflight_report(db, event)

    assert report.to_dict() == {
        "schema_version": "corporate-event-ledger-preflight.v3",
        "dry_run": True,
        "database_writes_executed": 0,
        "ready_for_execution": False,
        "projection_scope": "ADVISORY_FACTOR_ONLY",
        "projection_note": (
            "Acoes anteriores elegiveis foram projetadas; o fator do evento-alvo "
            "e aplicado sem resolver sua politica de fracao, custo ou caixa."
        ),
        "event_id": event.id,
        "event_type": "GRUPAMENTO",
        "quantity_factor": "0.02",
        "portfolio_id": portfolio.id,
        "ticker": "AMOB3",
        "as_of": "2025-01-01",
        "transaction_ids": [1],
        "transaction_count": 1,
        "first_transaction_date": "2024-01-01",
        "last_transaction_date": "2024-01-01",
        "buy_quantity": "300.00000000",
        "sell_quantity": "0",
        "net_quantity": "300.00000000",
        "pre_event_projected_quantity": "300.00000000",
        "projected_net_quantity": "6.0000000000",
        "projected_whole_quantity": "6",
        "projected_fractional_quantity": "0E-10",
        "component_bonus_projection": None,
    }


@pytest.mark.asyncio
async def test_reconciliation_dry_run_can_embed_ledger_preflight(db, portfolio) -> None:
    asset = Asset(ticker="AMOB3", name="Automob", asset_type="ACAO", currency="BRL")
    db.add(asset)
    await db.flush()
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="AMOB3",
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal("300"),
            price=Decimal("0.30"),
            date=date(2024, 1, 1),
            currency="BRL",
        )
    )
    event = CorporateEvent(
        asset_id=asset.id,
        ticker="AMOB3",
        event_type="GRUPAMENTO",
        event_date=date(2025, 1, 1),
        ratio=Decimal("0.02"),
        effective_date=date(2025, 1, 1),
        quantity_factor=Decimal("0.02"),
        portfolio_id=portfolio.id,
        source_provider="test",
        source_event_id="test:amob3",
    )
    db.add(event)
    await db.flush()

    report = await build_corporate_event_reconciliation_dry_run(
        db,
        event_ids=(event.id,),
        decision=CorporateEventReconciliationDecision.CONFLICT,
        reason="preflight read-only",
        ledger_preflight_event_id=event.id,
    )

    payload = report.to_dict()
    assert payload["dry_run"] is True
    assert payload["database_writes_executed"] == 0
    assert payload["ledger_preflight"]["ready_for_execution"] is False
    assert payload["ledger_preflight"]["projected_net_quantity"] == "6.0000000000"


@pytest.mark.asyncio
async def test_reconciliation_dry_run_embeds_global_event_preflight(
    db, portfolio
) -> None:
    asset = Asset(ticker="AMOB3", name="Automob", asset_type="ACAO", currency="BRL")
    db.add(asset)
    await db.flush()
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="AMOB3",
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal("300"),
            price=Decimal("0.30"),
            date=date(2024, 1, 1),
            currency="BRL",
        )
    )
    event = CorporateEvent(
        asset_id=asset.id,
        ticker="AMOB3",
        event_type="GRUPAMENTO",
        event_date=date(2025, 1, 1),
        ratio=Decimal("0.02"),
        effective_date=date(2025, 1, 1),
        quantity_factor=Decimal("0.02"),
        source_provider="test",
        source_event_id="test:amob3",
    )
    db.add(event)
    await db.flush()

    report = await build_corporate_event_reconciliation_dry_run(
        db,
        event_ids=(event.id,),
        decision=CorporateEventReconciliationDecision.CONFLICT,
        reason="preflight read-only",
        ledger_preflight_event_id=event.id,
        ledger_preflight_portfolio_id=portfolio.id,
    )

    payload = report.to_dict()
    assert payload["database_writes_executed"] == 0
    assert payload["ledger_preflight"]["portfolio_id"] == portfolio.id
    assert payload["ledger_preflight"]["projected_net_quantity"] == "6.0000000000"
