"""Testes do endpoint publico da apuracao anual canonica de IRPF."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.routers.irpf import get_canonical_irpf_assessment
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_canonical_endpoint_authorizes_portfolio_and_returns_v1_contract() -> None:
    db = AsyncMock()
    user = SimpleNamespace(id=9)
    contract = MagicMock()
    contract.to_dict.return_value = {
        "schema_version": "irpf-annual-assessment.v1",
        "portfolio_id": 7,
        "year": 2024,
        "monthly": [],
        "total_gross_tax_due_brl": "0",
        "total_withholding_brl": "0",
        "total_net_tax_due_brl": "0",
        "total_payment_due_brl": "0",
        "closing_accumulated_tax_brl": "0",
        "closing_common_withholding_balance_brl": "0",
        "closing_day_trade_withholding_balance_brl": "0",
        "closing_day_trade_loss_carryforward_brl": "0",
    }

    with (
        patch(
            "app.routers.irpf._get_portfolio",
            new=AsyncMock(return_value=SimpleNamespace(id=7, user_id=9)),
        ) as authorize,
        patch(
            "app.routers.irpf.build_irpf_annual_assessment",
            new=AsyncMock(return_value=contract),
        ) as build,
    ):
        result = await get_canonical_irpf_assessment(7, 2024, db, user)

    authorize.assert_awaited_once_with(7, user, db)
    build.assert_awaited_once_with(db, 7, 2024)
    assert result.schema_version == "irpf-annual-assessment.v1"
    assert result.portfolio_id == 7
    assert result.year == 2024


@pytest.mark.asyncio
async def test_canonical_endpoint_does_not_build_for_unauthorized_portfolio() -> None:
    db = AsyncMock()
    user = SimpleNamespace(id=9)

    with (
        patch(
            "app.routers.irpf._get_portfolio",
            new=AsyncMock(
                side_effect=HTTPException(
                    status_code=404,
                    detail="Carteira nao encontrada.",
                )
            ),
        ),
        patch(
            "app.routers.irpf.build_irpf_annual_assessment",
            new=AsyncMock(),
        ) as build,
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_canonical_irpf_assessment(7, 2024, db, user)

    assert exc_info.value.status_code == 404
    build.assert_not_awaited()


@pytest.mark.asyncio
async def test_canonical_endpoint_propagates_invalid_year_without_legacy_fallback() -> None:
    db = AsyncMock()
    user = SimpleNamespace(id=9)

    with (
        patch(
            "app.routers.irpf._get_portfolio",
            new=AsyncMock(return_value=SimpleNamespace(id=7, user_id=9)),
        ),
        patch(
            "app.routers.irpf.build_irpf_annual_assessment",
            new=AsyncMock(side_effect=ValueError("ano fiscal inválido")),
        ) as build,
        pytest.raises(ValueError, match="ano fiscal inválido"),
    ):
        await get_canonical_irpf_assessment(7, 1899, db, user)

    build.assert_awaited_once_with(db, 7, 1899)
