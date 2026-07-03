"""Testes para class_target_service — alocacao por classe de ativo."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.class_target_service import (
    VALID_ASSET_CLASSES,
    get_targets,
    get_targets_map,
    get_targets_with_current,
    upsert_target,
    delete_target,
)
from app.models.portfolio_class_target import PortfolioClassTarget


class TestValidAssetClasses:

    def test_valid_asset_classes_contains_standard_types(self):
        assert "ACAO" in VALID_ASSET_CLASSES
        assert "FII" in VALID_ASSET_CLASSES
        assert "ETF_NACIONAL" in VALID_ASSET_CLASSES
        assert "RENDA_FIXA" in VALID_ASSET_CLASSES
        assert "BDR" in VALID_ASSET_CLASSES

    def test_valid_asset_classes_count(self):
        assert len(VALID_ASSET_CLASSES) == 10


@pytest.mark.asyncio
class TestGetTargets:

    async def test_get_targets_empty(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        targets = await get_targets(db, 1)
        
        assert targets == []

    async def test_get_targets_multiple(self):
        db = AsyncMock(spec=AsyncSession)
        
        target1 = MagicMock(spec=PortfolioClassTarget)
        target1.asset_type = "ACAO"
        target1.target_pct = Decimal("30.00")
        
        target2 = MagicMock(spec=PortfolioClassTarget)
        target2.asset_type = "FII"
        target2.target_pct = Decimal("20.00")
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[target1, target2])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        targets = await get_targets(db, 1)
        
        assert len(targets) == 2
        assert targets[0].asset_type == "ACAO"


@pytest.mark.asyncio
class TestGetTargetsMap:

    async def test_get_targets_map_empty(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        targets_map = await get_targets_map(db, 1)
        
        assert targets_map == {}

    async def test_get_targets_map_with_targets(self):
        db = AsyncMock(spec=AsyncSession)
        
        target1 = MagicMock(spec=PortfolioClassTarget)
        target1.asset_type = "ACAO"
        target1.target_pct = Decimal("30.00")
        
        target2 = MagicMock(spec=PortfolioClassTarget)
        target2.asset_type = "FII"
        target2.target_pct = Decimal("20.00")
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[target1, target2])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        targets_map = await get_targets_map(db, 1)
        
        assert targets_map["ACAO"] == 30.0
        assert targets_map["FII"] == 20.0


@pytest.mark.asyncio
class TestGetTargetsWithCurrent:

    async def test_get_targets_with_current_empty(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_targets_with_current(db, 1, [])
        
        assert result == []

    async def test_get_targets_with_current_only_targets(self):
        db = AsyncMock(spec=AsyncSession)
        
        target = MagicMock(spec=PortfolioClassTarget)
        target.asset_type = "ACAO"
        target.target_pct = Decimal("30.00")
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[target])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_targets_with_current(db, 1, [])
        
        assert len(result) == 1
        assert result[0]["asset_type"] == "ACAO"
        assert result[0]["target_pct"] == 30.0
        assert result[0]["current_pct"] == 0.0

    async def test_get_targets_with_current_both(self):
        db = AsyncMock(spec=AsyncSession)
        
        target = MagicMock(spec=PortfolioClassTarget)
        target.asset_type = "ACAO"
        target.target_pct = Decimal("30.00")
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[target])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        current_distribution = [
            {
                "asset_type": "ACAO",
                "label": "Ações",
                "value": 1000.0,
                "percentage": 40.0,
                "color": "#3b82f6",
            }
        ]
        
        result = await get_targets_with_current(db, 1, current_distribution)
        
        assert len(result) == 1
        assert result[0]["target_pct"] == 30.0
        assert result[0]["current_pct"] == 40.0
        assert result[0]["delta_pct"] == 10.0

    async def test_get_targets_with_current_ordering(self):
        db = AsyncMock(spec=AsyncSession)
        
        target_acao = MagicMock(spec=PortfolioClassTarget)
        target_acao.asset_type = "ACAO"
        target_acao.target_pct = Decimal("30.00")
        
        target_fii = MagicMock(spec=PortfolioClassTarget)
        target_fii.asset_type = "FII"
        target_fii.target_pct = Decimal("20.00")
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[target_acao, target_fii])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        current_distribution = [
            {
                "asset_type": "FII",
                "label": "FIIs",
                "value": 5000.0,
                "percentage": 50.0,
                "color": "#8b5cf6",
            },
            {
                "asset_type": "ACAO",
                "label": "Ações",
                "value": 5000.0,
                "percentage": 50.0,
                "color": "#3b82f6",
            },
        ]
        
        result = await get_targets_with_current(db, 1, current_distribution)
        
        assert len(result) == 2
        assert result[0]["current_pct"] == 50.0


@pytest.mark.asyncio
class TestUpsertTarget:

    async def test_upsert_target_create_new(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(return_value=execute_result)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        result = await upsert_target(db, 1, "ACAO", 30.0)
        
        assert result is not None
        db.add.assert_called_once()
        db.commit.assert_called_once()

    async def test_upsert_target_update_existing(self):
        db = AsyncMock(spec=AsyncSession)
        
        existing_target = MagicMock(spec=PortfolioClassTarget)
        existing_target.asset_type = "ACAO"
        existing_target.target_pct = Decimal("25.00")
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=existing_target)
        
        db.execute = AsyncMock(return_value=execute_result)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        result = await upsert_target(db, 1, "ACAO", 35.0)
        
        assert result == existing_target
        assert existing_target.target_pct == Decimal("35.00")
        db.commit.assert_called_once()

    async def test_upsert_target_rounding(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(return_value=execute_result)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        result = await upsert_target(db, 1, "ACAO", 33.333)
        
        assert result is not None
        db.commit.assert_called_once()


@pytest.mark.asyncio
class TestDeleteTarget:

    async def test_delete_target_success(self):
        db = AsyncMock(spec=AsyncSession)
        
        target = MagicMock(spec=PortfolioClassTarget)
        target.asset_type = "ACAO"
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=target)
        
        db.execute = AsyncMock(return_value=execute_result)
        db.delete = AsyncMock()
        db.commit = AsyncMock()
        
        result = await delete_target(db, 1, "ACAO")
        
        assert result is True
        db.delete.assert_called_once()
        db.commit.assert_called_once()

    async def test_delete_target_not_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await delete_target(db, 1, "NONEXISTENT")
        
        assert result is False
        db.delete.assert_not_called()
