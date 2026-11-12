from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.core.clock import FrozenClock
from app.core.database import Base
from app.models.asset import Asset
from app.models.corporate_event import CorporateEvent
from app.models.corporate_event_reconciliation_evidence import (
    CorporateEventReconciliationEvidence,
)
from app.models.portfolio import Portfolio
from app.models.portfolio_corporate_fraction_settlement import (
    PortfolioCorporateFractionSettlement,
)
from app.models.transaction import OperationType, Transaction
from app.models.user import User
from app.routers import transactions as transactions_router
from app.schemas.transaction import CorporateFractionSettlementUpsert
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.corporate_event_fractional_resolution import (
    FractionalResolution,
    FractionalResolutionPolicy,
)
from app.services.portfolio_asset_corporate_lifecycle_service import (
    READ_PORTFOLIO_CORPORATE_LIFECYCLE,
    load_portfolio_pending_corporate_fractions,
)
from app.services.portfolio_corporate_fraction_settlement_service import (
    PORTFOLIO_USER_CONFIRMED_AUCTION,
    WRITE_PORTFOLIO_CORPORATE_FRACTIONS,
    delete_portfolio_corporate_fraction_settlement,
    upsert_portfolio_corporate_fraction_settlement,
)
from app.services.position_timeline_projection import (
    PositionMovement,
    PositionMovementKind,
    project_position_timeline,
)


def test_position_timeline_cash_settlement_accepts_gross_amount_and_full_fractional_position() -> None:
    action = NormalizedCorporateAction(
        source="b3",
        source_event_id="b3:nike34-grupamento",
        ticker="NIKE34",
        event_date=date(2026, 10, 13),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=None,
            settlement_gross_amount_brl=Decimal("25.40"),
            cash_treatment=PORTFOLIO_USER_CONFIRMED_AUCTION,
        ),
    )
    timeline = project_position_timeline(
        movements=[
            PositionMovement(
                movement_date=date(2026, 1, 10),
                kind=PositionMovementKind.BUY,
                quantity=Decimal("1"),
                unit_price=Decimal("30.00"),
            )
        ],
        actions=[action],
    )

    assert timeline.quantity == Decimal("0")
    assert timeline.total_cost == Decimal("0")
    assert timeline.realized_pnl == Decimal("-4.60")
    assert len(timeline.pending_corporate_action_fractions) == 0
    assert len(timeline.corporate_action_cash_flows) == 1
    cash_flow = timeline.corporate_action_cash_flows[0]
    assert cash_flow.fractional_quantity == Decimal("0.2")
    assert cash_flow.gross_amount_brl == Decimal("25.40")
    assert cash_flow.unit_settlement_price_brl == Decimal("127")


@pytest.mark.asyncio
async def test_upsert_and_delete_portfolio_fraction_settlement_updates_lifecycle() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as db:
            owner = User(email="owner@example.com", hashed_password="x", name="Owner")
            other = User(email="other@example.com", hashed_password="y", name="Other")
            db.add_all([owner, other])
            await db.flush()

            portfolio = Portfolio(user_id=owner.id, name="Principal")
            asset = Asset(ticker="NIKE34", name="Nike BDR", asset_type="BDR")
            db.add_all([portfolio, asset])
            await db.flush()

            db.add(
                Transaction(
                    portfolio_id=portfolio.id,
                    ticker="NIKE34",
                    asset_type="BDR",
                    operation=OperationType.buy,
                    quantity=Decimal("6"),
                    price=Decimal("30.00"),
                    fees=Decimal("0"),
                    date=date(2026, 1, 10),
                    currency="BRL",
                )
            )
            event = CorporateEvent(
                asset_id=asset.id,
                ticker="NIKE34",
                event_type="GRUPAMENTO",
                status="PENDENTE",
                source_provider="b3",
                source_event_id="b3:nike34-rev-2026",
                is_canonical=True,
                reconciliation_status="MATCHED",
                requires_review=False,
                effective_date=date(2026, 10, 13),
                quantity_factor=Decimal("0.2"),
            )
            db.add(event)
            await db.flush()

            db.add(
                CorporateEventReconciliationEvidence(
                    corporate_event_id=event.id,
                    decision="MATCHED",
                    evidence_type="OFFICIAL_EXCHANGE_DOCUMENT",
                    evidence_reference="b3:nike34-test",
                    fractional_policy="PENDING_SETTLEMENT",
                )
            )
            await db.commit()

            write_access = PortfolioAccessContext.for_user(
                user_id=owner.id,
                portfolio_id=portfolio.id,
                permissions=frozenset({WRITE_PORTFOLIO_CORPORATE_FRACTIONS}),
            )
            read_access = PortfolioAccessContext.for_user(
                user_id=owner.id,
                portfolio_id=portfolio.id,
                permissions=frozenset({READ_PORTFOLIO_CORPORATE_LIFECYCLE}),
            )
            denied_access = PortfolioAccessContext.for_user(
                user_id=other.id,
                portfolio_id=portfolio.id,
                permissions=frozenset({WRITE_PORTFOLIO_CORPORATE_FRACTIONS}),
            )

            before = await load_portfolio_pending_corporate_fractions(
                db,
                access=read_access,
                clock=FrozenClock(datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)),
            )
            assert len(before) == 1
            assert before[0]["settlement_status"] == "PENDING_VALUE"
            assert before[0]["gross_amount_brl"] is None

            with pytest.raises(PortfolioAccessDenied):
                await upsert_portfolio_corporate_fraction_settlement(
                    db,
                    access=denied_access,
                    source_event_id="b3:nike34-rev-2026",
                    gross_amount_brl=Decimal("18.50"),
                )

            saved = await upsert_portfolio_corporate_fraction_settlement(
                db,
                access=write_access,
                source_event_id="b3:nike34-rev-2026",
                gross_amount_brl=Decimal("18.50"),
                settlement_date=date(2026, 10, 20),
                notes="Credito em conta",
            )
            assert saved["gross_amount_brl"] == Decimal("18.50")
            assert saved["cash_treatment"] == PORTFOLIO_USER_CONFIRMED_AUCTION

            # Idempotente ao editar valor
            updated = await upsert_portfolio_corporate_fraction_settlement(
                db,
                access=write_access,
                source_event_id="b3:nike34-rev-2026",
                gross_amount_brl=Decimal("20.00"),
                settlement_date=date(2026, 10, 21),
                notes="Ajustado",
            )
            assert updated["id"] == saved["id"]

            after = await load_portfolio_pending_corporate_fractions(
                db,
                access=read_access,
                clock=FrozenClock(datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)),
            )
            assert len(after) == 1
            assert after[0]["settlement_status"] == "SETTLED"
            assert after[0]["gross_amount_brl"] == Decimal("20.00")
            assert after[0]["cash_treatment"] == PORTFOLIO_USER_CONFIRMED_AUCTION
            assert after[0]["cost_basis_brl"].quantize(Decimal("0.01")) == Decimal("30.00")
            assert after[0]["realized_pnl_brl"].quantize(Decimal("0.01")) == Decimal("-10.00")

            rebuild_from = await delete_portfolio_corporate_fraction_settlement(
                db,
                access=write_access,
                source_event_id="b3:nike34-rev-2026",
            )
            assert rebuild_from == date(2026, 10, 21)
            reverted = await load_portfolio_pending_corporate_fractions(
                db,
                access=read_access,
                clock=FrozenClock(datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)),
            )
            assert reverted[0]["settlement_status"] == "PENDING_VALUE"
            remaining = (
                await db.execute(select(PortfolioCorporateFractionSettlement))
            ).scalars().all()
            assert remaining == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_fraction_settlement_router_triggers_snapshot_and_cache_invalidation() -> None:
    db = AsyncMock()
    current_user = SimpleNamespace(id=7)
    background_tasks = BackgroundTasks()
    expected = {
        "id": 1,
        "portfolio_id": 15,
        "source_event_id": "b3:nike34",
        "ticker": "NIKE34",
        "gross_amount_brl": Decimal("25.00"),
        "settlement_date": date(2026, 10, 20),
        "notes": "Leilao",
        "cash_treatment": PORTFOLIO_USER_CONFIRMED_AUCTION,
        "event_date": date(2026, 10, 13),
    }

    with (
        patch(
            "app.routers.transactions.upsert_portfolio_corporate_fraction_settlement",
            new=AsyncMock(return_value=expected),
        ),
        patch(
            "app.routers.transactions._run_snapshot_backfill",
            new=MagicMock(),
        ),
        patch(
            "app.routers.transactions.invalidate_portfolio_cache",
            new=MagicMock(),
        ),
    ):
        response = await transactions_router.upsert_portfolio_fraction_settlement_route(
            portfolio_id=15,
            payload=CorporateFractionSettlementUpsert(
                source_event_id="b3:nike34",
                gross_amount_brl=Decimal("25.00"),
                settlement_date=date(2026, 10, 20),
                notes="Leilao",
            ),
            background_tasks=background_tasks,
            db=db,
            current_user=current_user,
        )

    assert response == expected
    assert len(background_tasks.tasks) == 2


def test_position_timeline_preserves_adjusted_post_event_units_when_settled() -> None:
    action = NormalizedCorporateAction(
        source="b3",
        source_event_id="b3:reverse-split-adjusted-settled",
        ticker="NIKE34",
        event_date=date(2026, 10, 13),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=Decimal("1"),
            settlement_gross_amount_brl=Decimal("25.00"),
            cash_treatment=PORTFOLIO_USER_CONFIRMED_AUCTION,
            ledger_basis="ADJUSTED_POST_EVENT",
            fraction_is_post_event_quantity=True,
        ),
    )

    result = project_position_timeline(
        movements=[
            PositionMovement(
                movement_date=date(2026, 10, 1),
                kind=PositionMovementKind.BUY,
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
            )
        ],
        actions=[action],
    )

    assert result.quantity == Decimal("1")
    assert result.total_cost == Decimal("100")
    assert result.realized_pnl == Decimal("25.00")
    assert result.pending_corporate_action_fractions == ()
    assert len(result.corporate_action_cash_flows) == 1
    assert result.corporate_action_cash_flows[0].gross_amount_brl == Decimal("25.00")


def test_position_timeline_defers_cash_settlement_to_settlement_date() -> None:
    action = NormalizedCorporateAction(
        source="b3",
        source_event_id="b3:nike34-dated",
        ticker="NIKE34",
        event_date=date(2026, 10, 13),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=None,
            settlement_gross_amount_brl=Decimal("25.40"),
            settlement_date=date(2026, 10, 21),
            cash_treatment=PORTFOLIO_USER_CONFIRMED_AUCTION,
        ),
    )
    buy = PositionMovement(
        movement_date=date(2026, 1, 10),
        kind=PositionMovementKind.BUY,
        quantity=Decimal("6"),
        unit_price=Decimal("30.00"),
    )

    before_credit = project_position_timeline(
        movements=[buy],
        actions=[action],
        through_date=date(2026, 10, 15),
    )
    assert before_credit.quantity == Decimal("1")
    assert before_credit.realized_pnl == Decimal("0")
    assert before_credit.corporate_action_cash_flows == ()
    assert len(before_credit.pending_corporate_action_fractions) == 1

    on_credit = project_position_timeline(
        movements=[buy],
        actions=[action],
        through_date=date(2026, 10, 21),
    )
    assert on_credit.quantity == Decimal("1")
    assert on_credit.realized_pnl.quantize(Decimal("0.01")) == Decimal("-4.60")
    assert on_credit.pending_corporate_action_fractions == ()
    assert len(on_credit.corporate_action_cash_flows) == 1
    assert on_credit.corporate_action_cash_flows[0].event_date == date(2026, 10, 21)
    assert on_credit.corporate_action_cash_flows[0].gross_amount_brl == Decimal("25.40")


def test_project_snapshot_positions_retains_zero_qty_cash_flow_and_confirmed_component_bonus() -> None:
    from app.services.snapshot_position_projection import project_snapshot_positions

    tx_nike = SimpleNamespace(
        id=1,
        ticker="NIKE34",
        asset_type="BDR",
        operation=OperationType.buy,
        quantity=Decimal("1"),
        price=Decimal("30.00"),
        fees=Decimal("0"),
        date=date(2026, 1, 10),
        currency="BRL",
        fx_rate=None,
    )
    tx_klbn = SimpleNamespace(
        id=2,
        ticker="KLBN11",
        asset_type="ACAO",
        operation=OperationType.buy,
        quantity=Decimal("10"),
        price=Decimal("20.00"),
        fees=Decimal("0"),
        date=date(2025, 12, 1),
        currency="BRL",
        fx_rate=None,
    )
    nike_action = NormalizedCorporateAction(
        source="b3",
        source_event_id="b3:nike34-full-frac",
        ticker="NIKE34",
        event_date=date(2026, 10, 13),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=None,
            settlement_gross_amount_brl=Decimal("25.40"),
            settlement_date=date(2026, 10, 20),
            cash_treatment=PORTFOLIO_USER_CONFIRMED_AUCTION,
        ),
    )
    klbn_action = NormalizedCorporateAction(
        source="brapi",
        source_event_id="brapi:klbn-bonus-2025",
        ticker="KLBN11",
        event_date=date(2025, 12, 18),
        kind=CorporateActionKind.STOCK_BONUS,
        quantity_factor=Decimal("1.01"),
        raw_payload={},
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            settlement_gross_amount_brl=Decimal("2.50"),
            settlement_date=date(2026, 2, 24),
            cash_treatment=PORTFOLIO_USER_CONFIRMED_AUCTION,
        ),
        component_bonus={
            "model": "COMPONENT_BONUS_FRACTIONS_V1",
            "evidence_reference": "issuer:klbn:bonus-and-auction:2025",
            "record_date": "2025-12-17",
            "credit_date": "2025-12-22",
            "settlement_date": "2026-02-24",
            "bonus_factor": "0.01",
            "bonus_cost_per_share_brl": "12.94564988922",
            "cash_treatment": "PRO_RATA_AUCTION_RIGHT",
            "unit_ticker": "KLBN11",
            "unit_asset_type": "ACAO",
            "unit_isin_code": "BRKLBNCDAM18",
            "unit_composition": {"ON": "1", "PN": "4"},
            "components": [
                {
                    "component": "ON",
                    "ticker": "KLBN3",
                    "asset_type": "ACAO",
                    "isin_code": "BRKLBNACNOR2",
                    "units_per_position": "1",
                    "settlement_price_brl": "3.942352337",
                },
                {
                    "component": "PN",
                    "ticker": "KLBN4",
                    "asset_type": "ACAO",
                    "isin_code": "BRKLBNACNPR9",
                    "units_per_position": "4",
                    "settlement_price_brl": "3.942611212",
                },
            ],
        },
    )

    projected = project_snapshot_positions(
        transactions=[tx_nike, tx_klbn],
        actions_by_ticker={"NIKE34": (nike_action,), "KLBN11": (klbn_action,)},
        target_date=date(2026, 11, 11),
        include_corporate_action_cash_flows=True,
    )

    assert "NIKE34" in projected
    nike_proj = projected["NIKE34"][0]
    assert nike_proj.quantity == Decimal("0")
    assert nike_proj.corporate_action_cash_flows[0].gross_amount_brl == Decimal("25.40")
    assert nike_proj.realized_pnl == Decimal("-4.60")

    assert "KLBN11" in projected
    klbn_proj = projected["KLBN11"][0]
    assert len(klbn_proj.corporate_action_cash_flows) == 1
    assert klbn_proj.corporate_action_cash_flows[0].gross_amount_brl == Decimal("2.50")
    assert all(r.status == "CONFIRMED" for r in klbn_proj.component_bonus_cash_rights)


def test_class_snapshot_projection_carries_corporate_action_cash_flow_total() -> None:
    from app.models.asset import AssetType
    from app.services.class_snapshot_position_projection import (
        project_class_positions_at,
    )

    tx = SimpleNamespace(
        id=10,
        ticker="NIKE34",
        asset_type="BDR",
        operation=OperationType.buy,
        quantity=Decimal("1"),
        price=Decimal("30.00"),
        fees=Decimal("0"),
        date=date(2026, 1, 10),
        currency="BRL",
        fx_rate=None,
    )
    action = NormalizedCorporateAction(
        source="b3",
        source_event_id="b3:nike34-bdr-cash",
        ticker="NIKE34",
        event_date=date(2026, 10, 13),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=None,
            settlement_gross_amount_brl=Decimal("25.40"),
            settlement_date=date(2026, 10, 21),
            cash_treatment=PORTFOLIO_USER_CONFIRMED_AUCTION,
        ),
    )

    before_credit = project_class_positions_at(
        [tx],
        {"NIKE34": (action,)},
        target_date=date(2026, 10, 15),
    )
    assert before_credit["NIKE34"].asset_type == AssetType.BDR
    assert before_credit["NIKE34"].corporate_action_cash_flow_total == Decimal("0")

    on_credit = project_class_positions_at(
        [tx],
        {"NIKE34": (action,)},
        target_date=date(2026, 10, 21),
    )
    assert on_credit["NIKE34"].quantity == Decimal("0")
    assert on_credit["NIKE34"].corporate_action_cash_flow_total == Decimal("25.40")
    assert on_credit["NIKE34"].realized_pnl == Decimal("-4.60")

    breakeven_action = NormalizedCorporateAction(
        source="b3",
        source_event_id="b3:nike34-bdr-breakeven",
        ticker="NIKE34",
        event_date=date(2026, 10, 13),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=None,
            settlement_gross_amount_brl=Decimal("30.00"),
            settlement_date=date(2026, 10, 21),
            cash_treatment=PORTFOLIO_USER_CONFIRMED_AUCTION,
        ),
    )
    breakeven_on_credit = project_class_positions_at(
        [tx],
        {"NIKE34": (breakeven_action,)},
        target_date=date(2026, 10, 21),
    )
    assert breakeven_on_credit["NIKE34"].quantity == Decimal("0")
    assert breakeven_on_credit["NIKE34"].cost == Decimal("0")
    assert breakeven_on_credit["NIKE34"].realized_pnl == Decimal("0")
    assert breakeven_on_credit["NIKE34"].quantity == Decimal("0")
    assert breakeven_on_credit["NIKE34"].cost == Decimal("0")
    assert breakeven_on_credit["NIKE34"].realized_pnl == Decimal("0")
    assert breakeven_on_credit["NIKE34"].corporate_action_cash_flow_total == Decimal("30.00")


def test_user_confirmed_auction_with_disappeared_fraction_does_not_crash() -> None:
    action = NormalizedCorporateAction(
        source="b3",
        source_event_id="b3:nike34-disappeared-frac",
        ticker="NIKE34",
        event_date=date(2026, 10, 13),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor=Decimal("0.2"),
        raw_payload={},
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=None,
            settlement_gross_amount_brl=Decimal("25.40"),
            settlement_date=date(2026, 10, 21),
            cash_treatment=PORTFOLIO_USER_CONFIRMED_AUCTION,
        ),
    )

    result = project_position_timeline(
        movements=[
            PositionMovement(
                movement_date=date(2026, 10, 1),
                kind=PositionMovementKind.BUY,
                quantity=Decimal("5"),
                unit_price=Decimal("30"),
            )
        ],
        actions=[action],
        through_date=date(2026, 11, 11),
    )

    assert result.quantity == Decimal("1")
    assert result.total_cost == Decimal("150")
    assert result.realized_pnl == Decimal("0")
    assert result.corporate_action_cash_flows == ()


@pytest.mark.asyncio
async def test_reconcile_settlements_removes_stale_rows_after_tx_edit() -> None:
    from app.services.portfolio_corporate_fraction_settlement_service import (
        reconcile_portfolio_corporate_fraction_settlements,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as db:
            user = User(name="Reconcile", email="reconcile@test.dev", hashed_password="x")
            db.add(user)
            await db.flush()
            portfolio = Portfolio(user_id=user.id, name="Reconcile")
            asset = Asset(ticker="NIKE34", name="Nike BDR", asset_type="BDR")
            db.add_all([portfolio, asset])
            await db.flush()
            tx = Transaction(
                portfolio_id=portfolio.id,
                ticker="NIKE34",
                asset_type="BDR",
                operation=OperationType.buy,
                quantity=Decimal("6"),
                price=Decimal("30.00"),
                fees=Decimal("0"),
                date=date(2026, 1, 10),
                currency="BRL",
            )
            ev = CorporateEvent(
                asset_id=asset.id,
                ticker="NIKE34",
                event_type="GRUPAMENTO",
                status="PENDENTE",
                source_provider="b3",
                source_event_id="b3:nike34-reconcile",
                is_canonical=True,
                reconciliation_status="MATCHED",
                requires_review=False,
                effective_date=date(2026, 10, 13),
                quantity_factor=Decimal("0.2"),
            )
            db.add_all([tx, ev])
            await db.flush()
            db.add(
                CorporateEventReconciliationEvidence(
                    corporate_event_id=ev.id,
                    decision="MATCHED",
                    evidence_type="OFFICIAL_EXCHANGE_DOCUMENT",
                    evidence_reference="b3:nike34-reconcile-ev",
                    fractional_policy="PENDING_SETTLEMENT",
                )
            )
            await db.commit()

            write_access = PortfolioAccessContext.for_user(
                user_id=user.id,
                portfolio_id=portfolio.id,
                permissions=frozenset({WRITE_PORTFOLIO_CORPORATE_FRACTIONS}),
            )
            await upsert_portfolio_corporate_fraction_settlement(
                db,
                access=write_access,
                source_event_id="b3:nike34-reconcile",
                gross_amount_brl=Decimal("25.40"),
                settlement_date=date(2026, 10, 21),
                notes="Leilao antigo",
            )

            # Edit purchase quantity 6 -> 5 so 5 * 0.2 = 1.0 leaves no fraction.
            tx.quantity = Decimal("5")
            await db.commit()

            stale_ids, earliest_date = await reconcile_portfolio_corporate_fraction_settlements(
                db,
                portfolio_id=portfolio.id,
                tickers=["NIKE34"],
                commit=True,
                clock=FrozenClock(datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)),
            )
            assert stale_ids == ["b3:nike34-reconcile"]
            assert earliest_date == date(2026, 10, 21)

            remaining = (
                await db.execute(select(PortfolioCorporateFractionSettlement))
            ).scalars().all()
            assert remaining == []

            read_access = PortfolioAccessContext.for_user(
                user_id=user.id,
                portfolio_id=portfolio.id,
                permissions=frozenset({READ_PORTFOLIO_CORPORATE_LIFECYCLE}),
            )
            fractions = await load_portfolio_pending_corporate_fractions(
                db,
                access=read_access,
                clock=FrozenClock(datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)),
            )
            assert len(fractions) == 1
            assert fractions[0]["fractional_quantity"] is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_rejects_component_bonus_without_fractional_entitlement() -> None:
    access = PortfolioAccessContext.for_user(
        user_id=7,
        portfolio_id=19,
        permissions=frozenset({WRITE_PORTFOLIO_CORPORATE_FRACTIONS}),
    )
    ownership = MagicMock()
    ownership.scalar_one_or_none.return_value = SimpleNamespace(id=19, user_id=7)
    db = AsyncMock()
    db.execute.return_value = ownership

    whole_only_right = {
        "event_id": 88,
        "source_event_id": "b3:klbn-whole-only",
        "ticker": "KLBN11",
        "event_type": "BONIFICACAO",
        "record_date": date(2025, 12, 17),
        "settlement_date": date(2026, 2, 24),
        "base_position": Decimal("100"),
        "settlement_status": "AVAILABLE",
        "components": [
            {"component": "ON", "fractional_quantity": Decimal("0")},
            {"component": "PN", "fractional_quantity": Decimal("0")},
        ],
        "gross_amount_brl": Decimal("0"),
        "calculated_gross_amount_brl": Decimal("0"),
        "has_fractional_entitlement": False,
    }

    with (
        patch(
            "app.services.portfolio_asset_corporate_lifecycle_service."
            "load_portfolio_pending_corporate_fractions",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.portfolio_corporate_rights_service."
            "load_portfolio_corporate_rights",
            new=AsyncMock(return_value=[whole_only_right]),
        ),
    ):
        with pytest.raises(LookupError):
            await upsert_portfolio_corporate_fraction_settlement(
                db,
                access=access,
                source_event_id="b3:klbn-whole-only",
                gross_amount_brl=Decimal("5.00"),
            )


@pytest.mark.asyncio
async def test_deferred_full_position_settlement_preserves_twr_return_base_in_both_chains() -> None:
    from app.models.asset_price import AssetPrice
    from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
    from app.models.portfolio_snapshot import PortfolioSnapshot
    from app.services.portfolio_class_snapshot_service import rebuild_class_snapshots
    from app.services.portfolio_snapshot_canonical_twr_service import (
        backfill_canonical_snapshots_with_returns,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as db:
            user = User(name="TwrBase", email="twrbase@test.dev", hashed_password="x")
            db.add(user)
            await db.flush()
            portfolio = Portfolio(user_id=user.id, name="TwrBase")
            asset = Asset(ticker="NIKE34", name="Nike BDR", asset_type="BDR")
            db.add_all([portfolio, asset])
            await db.flush()

            db.add(
                AssetPrice(
                    asset_id=asset.id,
                    timestamp=datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc),
                    open=Decimal("30.00"),
                    high=Decimal("30.00"),
                    low=Decimal("30.00"),
                    close=Decimal("30.00"),
                    volume=100,
                    source="test",
                )
            )
            db.add(
                Transaction(
                    portfolio_id=portfolio.id,
                    ticker="NIKE34",
                    asset_type="BDR",
                    operation=OperationType.buy,
                    quantity=Decimal("1"),
                    price=Decimal("30.00"),
                    fees=Decimal("0"),
                    date=date(2026, 10, 12),
                    currency="BRL",
                )
            )
            ev = CorporateEvent(
                asset_id=asset.id,
                ticker="NIKE34",
                event_type="GRUPAMENTO",
                status="PENDENTE",
                source_provider="b3",
                source_event_id="b3:nike34-twr-deferred",
                is_canonical=True,
                reconciliation_status="MATCHED",
                requires_review=False,
                effective_date=date(2026, 10, 13),
                quantity_factor=Decimal("0.2"),
            )
            db.add(ev)
            await db.flush()
            db.add(
                CorporateEventReconciliationEvidence(
                    corporate_event_id=ev.id,
                    decision="MATCHED",
                    evidence_type="OFFICIAL_EXCHANGE_DOCUMENT",
                    evidence_reference="b3:nike34-twr-ev",
                    fractional_policy="PENDING_SETTLEMENT",
                )
            )
            await db.commit()

            write_access = PortfolioAccessContext.for_user(
                user_id=user.id,
                portfolio_id=portfolio.id,
                permissions=frozenset({WRITE_PORTFOLIO_CORPORATE_FRACTIONS}),
            )
            await upsert_portfolio_corporate_fraction_settlement(
                db,
                access=write_access,
                source_event_id="b3:nike34-twr-deferred",
                gross_amount_brl=Decimal("25.40"),
                settlement_date=date(2026, 10, 21),
                notes="Credito em conta",
            )

            await backfill_canonical_snapshots_with_returns(
                db,
                portfolio.id,
                end_date=date(2026, 10, 22),
            )
            await rebuild_class_snapshots(
                db,
                portfolio.id,
            )

            port_snaps = {
                s.snapshot_date: s
                for s in (
                    await db.execute(
                        select(PortfolioSnapshot).where(
                            PortfolioSnapshot.portfolio_id == portfolio.id
                        )
                    )
                ).scalars().all()
            }
            class_snaps = {
                s.snapshot_date: s
                for s in (
                    await db.execute(
                        select(PortfolioClassSnapshot).where(
                            PortfolioClassSnapshot.portfolio_id == portfolio.id
                        )
                    )
                ).scalars().all()
            }

            assert Decimal(str(port_snaps[date(2026, 10, 13)].daily_return_pct)) == Decimal("0")
            assert Decimal(str(port_snaps[date(2026, 10, 20)].accumulated_return_pct)) == Decimal("0")
            assert Decimal(str(port_snaps[date(2026, 10, 21)].accumulated_return_pct)).quantize(
                Decimal("0.01")
            ) == Decimal("-15.33")
            assert Decimal(str(port_snaps[date(2026, 10, 22)].accumulated_return_pct)).quantize(
                Decimal("0.01")
            ) == Decimal("-15.33")

            assert Decimal(str(class_snaps[date(2026, 10, 13)].daily_return_pct)) == Decimal("0")
            assert Decimal(str(class_snaps[date(2026, 10, 20)].accumulated_return_pct)) == Decimal("0")
            assert Decimal(str(class_snaps[date(2026, 10, 21)].accumulated_return_pct)).quantize(
                Decimal("0.01")
            ) == Decimal("-15.33")
            assert Decimal(str(class_snaps[date(2026, 10, 22)].accumulated_return_pct)).quantize(
                Decimal("0.01")
            ) == Decimal("-15.33")
    finally:
        await engine.dispose()
