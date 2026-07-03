"""Testes para config_service — gerenciamento de configuracoes."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.config_service import (
    get_config,
    get_bool_config,
    set_config,
    get_all_configs,
    update_config,
    bulk_update_configs,
)
from app.models.config import AppConfig


@pytest.mark.asyncio
class TestGetConfig:

    async def test_get_config_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        config = MagicMock(spec=AppConfig)
        config.key = "test_key"
        config.value = "test_value"
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=config)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_config(db, "test_key")
        
        assert result == "test_value"

    async def test_get_config_not_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_config(db, "nonexistent_key")
        
        assert result is None


@pytest.mark.asyncio
class TestGetBoolConfig:

    async def test_get_bool_config_true_strings(self):
        db = AsyncMock(spec=AsyncSession)
        
        for true_val in ["true", "1", "yes"]:
            config = MagicMock(spec=AppConfig)
            config.value = true_val
            
            execute_result = MagicMock()
            execute_result.scalar_one_or_none = MagicMock(return_value=config)
            db.execute = AsyncMock(return_value=execute_result)
            
            result = await get_bool_config(db, "test_key")
            assert result is True

    async def test_get_bool_config_false_strings(self):
        db = AsyncMock(spec=AsyncSession)
        
        for false_val in ["false", "0", "no"]:
            config = MagicMock(spec=AppConfig)
            config.value = false_val
            
            execute_result = MagicMock()
            execute_result.scalar_one_or_none = MagicMock(return_value=config)
            db.execute = AsyncMock(return_value=execute_result)
            
            result = await get_bool_config(db, "test_key")
            assert result is False

    async def test_get_bool_config_not_found_default_false(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_bool_config(db, "nonexistent_key", default=False)
        
        assert result is False

    async def test_get_bool_config_not_found_default_true(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_bool_config(db, "nonexistent_key", default=True)
        
        assert result is True


@pytest.mark.asyncio
class TestSetConfig:

    async def test_set_config_existing_key(self):
        db = AsyncMock(spec=AsyncSession)
        
        config = MagicMock(spec=AppConfig)
        config.key = "test_key"
        config.value = "old_value"
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=config)
        db.execute = AsyncMock(return_value=execute_result)
        
        db.commit = AsyncMock()
        
        await set_config(db, "test_key", "new_value")
        
        assert config.value == "new_value"
        db.commit.assert_called_once()

    async def test_set_config_new_key(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        db.commit = AsyncMock()
        
        await set_config(db, "new_key", "new_value")
        
        db.add.assert_called_once()
        db.commit.assert_called_once()


@pytest.mark.asyncio
class TestGetAllConfigs:

    async def test_get_all_configs_public_only(self):
        db = AsyncMock(spec=AsyncSession)
        
        config1 = MagicMock(spec=AppConfig)
        config1.key = "key1"
        config1.is_public = True
        
        config2 = MagicMock(spec=AppConfig)
        config2.key = "key2"
        config2.is_public = True
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[config1, config2])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        configs = await get_all_configs(db, public_only=True)
        
        assert len(configs) == 2

    async def test_get_all_configs_including_private(self):
        db = AsyncMock(spec=AsyncSession)
        
        config1 = MagicMock(spec=AppConfig)
        config1.key = "public_key"
        config1.is_public = True
        
        config2 = MagicMock(spec=AppConfig)
        config2.key = "private_key"
        config2.is_public = False
        
        execute_result = MagicMock()
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[config1, config2])
        
        db.execute = AsyncMock(return_value=execute_result)
        
        configs = await get_all_configs(db, public_only=False)
        
        assert len(configs) == 2


@pytest.mark.asyncio
class TestUpdateConfig:

    async def test_update_config_existing(self):
        db = AsyncMock(spec=AsyncSession)
        
        config = MagicMock(spec=AppConfig)
        config.key = "test_key"
        config.value = "old_value"
        config.updated_at = None
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=config)
        
        db.execute = AsyncMock(return_value=execute_result)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        result = await update_config(db, "test_key", "new_value")
        
        assert result == config
        assert config.value == "new_value"
        db.commit.assert_called_once()

    async def test_update_config_new(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(return_value=execute_result)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        result = await update_config(db, "new_key", "new_value")
        
        assert result is not None
        db.add.assert_called_once()


@pytest.mark.asyncio
class TestBulkUpdateConfigs:

    async def test_bulk_update_configs(self):
        db = AsyncMock(spec=AsyncSession)
        
        config1 = MagicMock(spec=AppConfig)
        config1.key = "key1"
        config1.value = "old1"
        
        config2 = MagicMock(spec=AppConfig)
        config2.key = "key2"
        config2.value = "old2"
        
        execute_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=config1)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=config2)),
        ]
        
        db.execute = AsyncMock(side_effect=execute_results)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        configs_to_update = {"key1": "new1", "key2": "new2"}
        
        results = await bulk_update_configs(db, configs_to_update)
        
        assert len(results) == 2
        db.commit.assert_called_once()

    async def test_bulk_update_configs_mixed_new_existing(self):
        db = AsyncMock(spec=AsyncSession)
        
        existing_config = MagicMock(spec=AppConfig)
        existing_config.key = "existing_key"
        
        execute_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_config)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
        
        db.execute = AsyncMock(side_effect=execute_results)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        configs_to_update = {"existing_key": "value1", "new_key": "value2"}
        
        results = await bulk_update_configs(db, configs_to_update)
        
        assert len(results) == 2
        db.add.assert_called_once()
