from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.main import app, lifespan


@pytest.mark.asyncio
async def test_lifespan_does_not_start_market_sync_by_default() -> None:
    assert settings.ENABLE_BOOT_MARKET_SYNC is False

    engine = SimpleNamespace(dispose=AsyncMock())
    with (
        patch("app.main.start_scheduler"),
        patch("app.main.asyncio.create_task") as create_task,
        patch("app.main.engine", new=engine),
    ):
        async with lifespan(app):
            pass

    create_task.assert_not_called()
    engine.dispose.assert_awaited_once()
