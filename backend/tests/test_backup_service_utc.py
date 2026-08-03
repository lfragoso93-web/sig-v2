from datetime import UTC
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.services.backup_service import _utc_now, list_backups


def test_backup_utc_clock_is_timezone_aware() -> None:
    now = _utc_now()

    assert now.tzinfo is UTC
    assert now.utcoffset().total_seconds() == 0


@pytest.mark.asyncio
async def test_list_backups_serializes_created_at_with_utc_offset() -> None:
    backup_file = MagicMock()
    backup_file.name = "backup_20260802_120000.sql.gz"
    backup_file.stem = "backup_20260802_120000.sql"
    backup_file.stat.return_value = SimpleNamespace(
        st_size=1024,
        st_mtime=1_775_131_200,
    )

    with (
        patch("app.services.backup_service.Path.mkdir"),
        patch(
            "app.services.backup_service.Path.glob",
            return_value=[backup_file],
        ),
    ):
        result = await list_backups()

    assert result["success"] is True
    assert result["backups"][0]["created_at"].endswith("+00:00")
