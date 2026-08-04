"""Testes dos envelopes públicos canônicos de Bens e Rendimentos."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.routers.irpf import (
    get_canonical_irpf_assets,
    get_canonical_irpf_income,
)
from app.schemas.irpf import BemDireito, JCPItem, RendimentoIsento


@pytest.mark.asyncio
async def test_canonical_assets_endpoint_returns_versioned_envelope() -> None:
    db = AsyncMock()
    user = SimpleNamespace(id=9)
    items = [
        BemDireito(
            ticker="ABCD3",
            nome="ABCD3",
            asset_type="ACAO",
            codigo_irpf="31",
            grupo_irpf="03 - Participacoes Societarias",
            quantidade=10,
            custo_medio=12.34,
            custo_total=123.40,
            moeda="BRL",
        )
    ]

    with (
        patch(
            "app.routers.irpf._get_portfolio",
            new=AsyncMock(return_value=SimpleNamespace(id=7, user_id=9)),
        ) as authorize,
        patch(
            "app.routers.irpf.calc_bens_direitos",
            new=AsyncMock(return_value=items),
        ) as calculate,
    ):
        result = await get_canonical_irpf_assets(7, 2024, db, user)

    authorize.assert_awaited_once_with(7, user, db)
    calculate.assert_awaited_once_with(db, 7, 2024)
    assert result.schema_version == "irpf-assets-assessment.v1"
    assert result.total_cost_brl == Decimal("123.40")
    assert result.items == items


@pytest.mark.asyncio
async def test_canonical_income_endpoint_returns_versioned_envelope() -> None:
    db = AsyncMock()
    user = SimpleNamespace(id=9)
    dividends = [
        RendimentoIsento(
            ticker="ABCD3",
            asset_type="ACAO",
            total_recebido=80.25,
            quantidade_pgtos=2,
        )
    ]
    jcp = [
        JCPItem(
            ticker="EFGH4",
            total_bruto=100,
            ir_retido=15,
            total_liquido=85,
        )
    ]

    with (
        patch(
            "app.routers.irpf._get_portfolio",
            new=AsyncMock(return_value=SimpleNamespace(id=7, user_id=9)),
        ) as authorize,
        patch(
            "app.routers.irpf.calc_rendimentos",
            new=AsyncMock(return_value=(dividends, jcp)),
        ) as calculate,
    ):
        result = await get_canonical_irpf_income(7, 2024, db, user)

    authorize.assert_awaited_once_with(7, user, db)
    calculate.assert_awaited_once_with(db, 7, 2024)
    assert result.schema_version == "irpf-income-assessment.v1"
    assert result.total_dividends_brl == Decimal("80.25")
    assert result.total_jcp_gross_brl == Decimal("100.00")
    assert result.total_jcp_withholding_brl == Decimal("15.00")
    assert result.total_jcp_net_brl == Decimal("85.00")
    assert result.dividends == dividends
    assert result.jcp == jcp
