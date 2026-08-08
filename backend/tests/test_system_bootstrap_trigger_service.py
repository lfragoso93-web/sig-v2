from unittest.mock import AsyncMock, patch

import pytest

from app.services.system_bootstrap_trigger_service import (
    bootstrap_launch_reserved,
    reserve_system_bootstrap_launch,
    reset_bootstrap_launch_reservation_for_tests,
    run_reserved_system_bootstrap,
)
from app.services.system_readiness_service import (
    BootstrapReadinessState,
    get_bootstrap_readiness,
    reset_bootstrap_readiness_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_state():
    reset_bootstrap_readiness_for_tests()
    reset_bootstrap_launch_reservation_for_tests()
    yield
    reset_bootstrap_readiness_for_tests()
    reset_bootstrap_launch_reservation_for_tests()


def test_reservation_blocks_duplicate_launches() -> None:
    assert reserve_system_bootstrap_launch() is True
    assert bootstrap_launch_reserved() is True
    assert reserve_system_bootstrap_launch() is False


def test_running_readiness_blocks_new_reservation() -> None:
    readiness = get_bootstrap_readiness()
    readiness.state = BootstrapReadinessState.RUNNING
    assert reserve_system_bootstrap_launch() is False


@pytest.mark.asyncio
async def test_reserved_runner_releases_reservation() -> None:
    assert reserve_system_bootstrap_launch() is True
    report = object()
    with patch(
        "app.services.system_bootstrap_trigger_service.run_system_bootstrap",
        new=AsyncMock(return_value=report),
    ) as runner:
        result = await run_reserved_system_bootstrap()

    assert result is report
    runner.assert_awaited_once_with()
    assert bootstrap_launch_reserved() is False
