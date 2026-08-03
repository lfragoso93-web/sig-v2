"""Testes para goals_service — gerenciamento de metas financeiras."""
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.goals_service import (
    _calc_projection,
    _enrich,
    _get_proventos_mensais,
    _resolve_current_value,
    list_goals,
    get_goal,
    create_goal,
    update_goal,
    delete_goal,
)
from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.canonical_dividend_entitlement import (
    DividendEntitlement,
    DividendEvent,
    EntitlementReason,
)
from app.services.canonical_dividend_entitlement_reader import (
    PortfolioDividendEntitlement,
)


class TestCalcProjection:

    def test_calc_projection_already_completed(self):
        months, date = _calc_projection(current=1000, target=500, monthly=100)
        assert months == 0.0
        assert date is None

    def test_calc_projection_no_monthly_contribution(self):
        months, date = _calc_projection(current=500, target=1000, monthly=None)
        assert months is None
        assert date is None

    def test_calc_projection_zero_monthly_contribution(self):
        months, date = _calc_projection(current=500, target=1000, monthly=0)
        assert months is None
        assert date is None

    def test_calc_projection_valid(self):
        months, date = _calc_projection(current=500, target=1000, monthly=100)
        assert months == 5.0
        assert date is not None
        assert isinstance(date, datetime)

    def test_calc_projection_fractional_months(self):
        months, date = _calc_projection(current=0, target=1000, monthly=333)
        assert months == pytest.approx(3.0, rel=0.1)
        assert date is not None


class TestEnrich:

    def test_enrich_goal_basic(self):
        goal = MagicMock(spec=Goal)
        goal.id = 1
        goal.portfolio_id = 1
        goal.goal_type = "PATRIMONIO"
        goal.name = "Minha Meta"
        goal.target_value = 1000.0
        goal.current_value = 500.0
        goal.base_value = 500.0
        goal.monthly_contribution = 100.0
        goal.target_date = None
        goal.description = "Test goal"
        goal.created_at = datetime.now(timezone.utc)
        
        result = _enrich(goal)
        
        assert result["id"] == 1
        assert result["progress_pct"] == 50.0
        assert result["is_completed"] is False
        assert result["months_to_goal"] == 5.0

    def test_enrich_goal_completed(self):
        goal = MagicMock(spec=Goal)
        goal.id = 1
        goal.portfolio_id = 1
        goal.goal_type = "PATRIMONIO"
        goal.name = "Completed Goal"
        goal.target_value = 1000.0
        goal.current_value = 1200.0
        goal.base_value = 500.0
        goal.monthly_contribution = 100.0
        goal.target_date = None
        goal.description = "Done"
        goal.created_at = datetime.now(timezone.utc)
        
        result = _enrich(goal)
        
        assert result["is_completed"] is True
        assert result["progress_pct"] == 100.0
        assert result["months_to_goal"] == 0.0

    def test_enrich_goal_no_target(self):
        goal = MagicMock(spec=Goal)
        goal.id = 1
        goal.portfolio_id = 1
        goal.goal_type = "LIVRE"
        goal.name = "Free Goal"
        goal.target_value = None
        goal.current_value = 500.0
        goal.base_value = 500.0
        goal.monthly_contribution = 0.0
        goal.target_date = None
        goal.description = "Free"
        goal.created_at = datetime.now(timezone.utc)
        
        result = _enrich(goal)
        
        assert result["progress_pct"] == 0.0


@pytest.mark.asyncio
class TestResolveCurrentValue:

    async def test_resolve_patrimonio(self):
        db = AsyncMock(spec=AsyncSession)
        
        # Mock PortfolioPosition query
        position = MagicMock()
        position.market_value = 5000.0
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[position])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        value = await _resolve_current_value(db, 1, "PATRIMONIO", 0.0)
        
        assert value == 5000.0

    async def test_resolve_livre(self):
        db = AsyncMock(spec=AsyncSession)
        
        value = await _resolve_current_value(db, 1, "LIVRE", 1000.0)
        
        assert value == 1000.0


@pytest.mark.asyncio
async def test_get_proventos_mensais_uses_paid_canonical_net_brl():
    today = date.today()

    def right(
        event_id: int,
        net: str,
        *,
        currency: str = "BRL",
        payment_date: date | None = today,
    ) -> PortfolioDividendEntitlement:
        event = DividendEvent(
            event_id=event_id,
            record_date=today,
            ex_date=today,
            payment_date=payment_date,
            event_type="DIVIDENDO",
            value_per_unit=Decimal("1"),
            currency=currency,
        )
        entitlement = DividendEntitlement(
            event_id=event_id,
            reason=EntitlementReason.ELIGIBLE,
            entitlement_date=today,
            eligible_quantity=Decimal("1"),
            gross_amount=Decimal(net),
            withholding_tax=Decimal("0"),
            net_amount=Decimal(net),
            currency=currency,
        )
        return PortfolioDividendEntitlement(
            ticker="TEST3",
            asset_type="ACAO",
            event=event,
            entitlement=entitlement,
            approved_on=None,
            gross_value_per_unit=None,
            factor=None,
            complete_factor=None,
            isin_code=None,
            asset_issued=None,
            related_to=None,
            remarks=None,
        )

    rights = [
        right(1, "120"),
        right(2, "120", currency="USD"),
        right(3, "120", payment_date=None),
    ]
    with patch(
        "app.services.goals_service.load_portfolio_dividend_entitlements",
        new=AsyncMock(return_value=rights),
    ):
        monthly = await _get_proventos_mensais(
            AsyncMock(spec=AsyncSession),
            portfolio_id=1,
        )

    assert monthly == 10.0


@pytest.mark.asyncio
class TestListGoals:

    async def test_list_goals_empty(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        goals = await list_goals(db, 1)
        
        assert goals == []

    async def test_list_goals_multiple(self):
        db = AsyncMock(spec=AsyncSession)
        
        goal1 = MagicMock(spec=Goal)
        goal1.id = 1
        goal1.portfolio_id = 1
        goal1.goal_type = "PATRIMONIO"
        goal1.name = "Goal 1"
        goal1.target_value = 1000.0
        goal1.current_value = 500.0
        goal1.base_value = 500.0
        goal1.monthly_contribution = 100.0
        goal1.target_date = None
        goal1.description = ""
        goal1.created_at = datetime.now(timezone.utc)
        
        goal2 = MagicMock(spec=Goal)
        goal2.id = 2
        goal2.portfolio_id = 1
        goal2.goal_type = "PROVENTOS"
        goal2.name = "Goal 2"
        goal2.target_value = 2000.0
        goal2.current_value = 1000.0
        goal2.base_value = 1000.0
        goal2.monthly_contribution = 200.0
        goal2.target_date = None
        goal2.description = ""
        goal2.created_at = datetime.now(timezone.utc)
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[goal1, goal2])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        goals = await list_goals(db, 1)
        
        assert len(goals) == 2


@pytest.mark.asyncio
class TestGetGoal:

    async def test_get_goal_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        goal = MagicMock(spec=Goal)
        goal.id = 1
        goal.portfolio_id = 1
        goal.goal_type = "PATRIMONIO"
        goal.name = "My Goal"
        goal.target_value = 1000.0
        goal.current_value = 500.0
        goal.base_value = 500.0
        goal.monthly_contribution = 100.0
        goal.target_date = None
        goal.description = ""
        goal.created_at = datetime.now(timezone.utc)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=goal)
        
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_goal(db, 1, 1)
        
        assert result is not None
        assert result["id"] == 1

    async def test_get_goal_not_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_goal(db, 999, 1)
        
        assert result is None


@pytest.mark.asyncio
class TestCreateGoal:

    async def test_create_goal_livre(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        data = GoalCreate(
            portfolio_id=1,
            goal_type="LIVRE",
            name="Free Goal",
            target_value=1000.0,
            current_value=500.0,
            monthly_contribution=100.0,
            description="Test",
        )
        
        result = await create_goal(db, data)
        
        assert result is not None
        db.add.assert_called_once()
        db.commit.assert_called_once()


@pytest.mark.asyncio
class TestUpdateGoal:

    async def test_update_goal_success(self):
        db = AsyncMock(spec=AsyncSession)
        
        goal = MagicMock(spec=Goal)
        goal.id = 1
        goal.portfolio_id = 1
        goal.goal_type = "PATRIMONIO"
        goal.name = "Old Name"
        goal.target_value = 1000.0
        goal.current_value = 500.0
        goal.base_value = 500.0
        goal.monthly_contribution = 100.0
        goal.target_date = None
        goal.description = ""
        goal.created_at = datetime.now(timezone.utc)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=goal)
        
        db.execute = AsyncMock(return_value=execute_result)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        data = GoalUpdate(name="New Name")
        
        result = await update_goal(db, 1, 1, data)
        
        assert result is not None
        db.commit.assert_called_once()

    async def test_update_goal_not_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(return_value=execute_result)
        
        data = GoalUpdate(name="New Name")
        
        result = await update_goal(db, 999, 1, data)
        
        assert result is None


@pytest.mark.asyncio
class TestDeleteGoal:

    async def test_delete_goal_success(self):
        db = AsyncMock(spec=AsyncSession)
        
        goal = MagicMock(spec=Goal)
        goal.id = 1
        goal.portfolio_id = 1
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=goal)
        
        db.execute = AsyncMock(return_value=execute_result)
        db.delete = AsyncMock()
        db.commit = AsyncMock()
        
        result = await delete_goal(db, 1, 1)
        
        assert result is True
        db.delete.assert_called_once()

    async def test_delete_goal_not_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await delete_goal(db, 999, 1)
        
        assert result is False
