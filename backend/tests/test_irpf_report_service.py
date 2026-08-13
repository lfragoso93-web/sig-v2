from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.schemas.irpf import BemDireito
from app.services.irpf_report_service import generate_irpf_report
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_generate_irpf_report_uses_canonical_bens_read_only() -> None:
    db = AsyncMock(spec=AsyncSession)
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = None
    db.execute.return_value = query_result

    bens = [
        BemDireito(
            ticker="PETR4",
            nome="PETR4",
            asset_type="ACAO",
            codigo_irpf="31",
            grupo_irpf="03 - Participacoes Societarias",
            quantidade=10,
            custo_medio=30,
            custo_total=300,
            moeda="BRL",
        )
    ]

    with (
        patch(
            "app.services.irpf_report_service.calc_bens_direitos",
            new=AsyncMock(return_value=bens),
        ) as load_bens,
        patch(
            "app.services.irpf_report_service.calc_ganhos_capital",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.irpf_report_service.calc_rendimentos",
            new=AsyncMock(return_value=([], [])),
        ),
    ):
        report = await generate_irpf_report(db, portfolio_id=7, year=2024)

    load_bens.assert_awaited_once_with(db, 7, 2024)
    assert report.bens_direitos == bens
    assert report.resumo.total_bens_direitos == 300
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_irpf_report_does_not_query_or_persist_legacy_row() -> None:
    db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "app.services.irpf_report_service.calc_bens_direitos",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.irpf_report_service.calc_ganhos_capital",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.irpf_report_service.calc_rendimentos",
            new=AsyncMock(return_value=([], [])),
        ),
    ):
        report = await generate_irpf_report(db, portfolio_id=7, year=2024)

    assert report.portfolio_id == 7
    assert report.ano == 2024
    db.execute.assert_not_awaited()
    db.add.assert_not_called()
    db.commit.assert_not_awaited()
