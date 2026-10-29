import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_read_db, get_db


@pytest.mark.asyncio
async def test_get_read_db_does_not_commit():
    mock_session = AsyncMock(spec=AsyncSession)

    with patch("app.core.database.AsyncSessionLocal") as mock_session_maker:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_session_maker.return_value = mock_ctx

        gen = get_read_db()
        session = await anext(gen)
        assert session is mock_session
        assert mock_session.commit.call_count == 0

        # Generator finishes
        with pytest.raises(StopAsyncIteration):
            await anext(gen)

        # Confirm commit was never called
        assert mock_session.commit.call_count == 0
        assert mock_session.close.call_count == 1


@pytest.mark.asyncio
async def test_get_db_commits_on_success():
    mock_session = AsyncMock(spec=AsyncSession)

    with patch("app.core.database.AsyncSessionLocal") as mock_session_maker:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_session_maker.return_value = mock_ctx

        gen = get_db()
        session = await anext(gen)
        assert session is mock_session

        with pytest.raises(StopAsyncIteration):
            await anext(gen)

        assert mock_session.commit.call_count == 1
        assert mock_session.close.call_count == 1
