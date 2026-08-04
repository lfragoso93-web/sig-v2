"""Testes do serviço read-only da apuração anual canônica."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.irpf_annual_assessment_service import (
    build_irpf_annual_assessment,
)


@pytest.mark.asyncio
async def test_service_builds_versioned_contract_from_integrated_assessment() -> None:
    session = AsyncMock()
    integrated = MagicMock()
    contract = MagicMock()

    with (
        patch(
            "app.services.irpf_annual_assessment_service.assess_annual_integrated_operations",
            new=AsyncMock(return_value=integrated),
        ) as assess,
        patch(
            "app.services.irpf_annual_assessment_service.build_irpf_annual_assessment_contract",
            return_value=contract,
        ) as map_contract,
    ):
        result = await build_irpf_annual_assessment(session, 7, 2024)

    assess.assert_awaited_once_with(session, 7, 2024)
    map_contract.assert_called_once_with(integrated)
    assert result is contract
