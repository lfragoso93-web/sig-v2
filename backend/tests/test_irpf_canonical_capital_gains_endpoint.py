"""Teste do envelope público canônico de Ganhos de Capital."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.routers.irpf import get_canonical_irpf_capital_gains
from app.schemas.irpf import GanhoCapitalMensal


@pytest.mark.asyncio
async def test_canonical_capital_gains_endpoint_returns_versioned_envelope() -> None:
    db = AsyncMock()
    user = SimpleNamespace(id=9)
    months = [
        GanhoCapitalMensal(
            mes="2024-01",
            total_vendas=1000,
            total_custo=800,
            lucro_bruto=200,
            lucro_day_trade=0,
            lucro_swing_trade=200,
            isencao_aplicada=0,
            base_calculo=200,
            aliquota_swing=0.15,
            aliquota_day_trade=0.20,
            ir_devido_swing=30,
            ir_devido_day_trade=0,
            ir_retido_fonte=0,
            ir_a_recolher=30,
            vendas=[],
        )
    ]

    with (
        patch(
            "app.routers.irpf._get_portfolio",
            new=AsyncMock(return_value=SimpleNamespace(id=7, user_id=9)),
        ) as authorize,
        patch(
            "app.routers.irpf.calc_ganhos_capital",
            new=AsyncMock(return_value=months),
        ) as calculate,
    ):
        result = await get_canonical_irpf_capital_gains(7, 2024, db, user)

    authorize.assert_awaited_once_with(7, user, db)
    calculate.assert_awaited_once_with(db, 7, 2024)
    assert result.schema_version == "irpf-capital-gains-assessment.v1"
    assert result.total_sales_brl == Decimal(1000)
    assert result.total_gross_profit_brl == Decimal(200)
    assert result.total_tax_due_brl == Decimal(30)
    assert result.months == months
