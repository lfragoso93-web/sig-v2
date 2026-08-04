"""Testes das exportações canônicas de IRPF."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.routers.irpf import download_irpf_csv, download_irpf_pdf
from app.services.irpf_canonical_export_service import IrpfCanonicalExport


def _canonical_export() -> IrpfCanonicalExport:
    return IrpfCanonicalExport(
        portfolio_id=7,
        year=2024,
        bens_direitos=[],
        ganhos_mensais=[],
        dividendos=[],
        jcp=[],
        total_bens_direitos_brl=Decimal(0),
        total_vendas_ano_brl=Decimal(0),
        total_gross_tax_due_brl=Decimal(0),
        total_withholding_brl=Decimal(0),
        total_payment_due_brl=Decimal(0),
        total_dividendos_brl=Decimal(0),
        total_jcp_bruto_brl=Decimal(0),
        total_jcp_ir_retido_brl=Decimal(0),
        closing_day_trade_loss_carryforward_brl=Decimal(0),
    )


@pytest.mark.asyncio
async def test_pdf_endpoint_uses_only_canonical_export_composition() -> None:
    db = AsyncMock()
    user = SimpleNamespace(id=9)
    export = _canonical_export()

    with (
        patch(
            "app.routers.irpf._get_portfolio",
            new=AsyncMock(return_value=SimpleNamespace(id=7, user_id=9)),
        ),
        patch(
            "app.routers.irpf.build_irpf_canonical_export",
            new=AsyncMock(return_value=export),
        ) as compose,
        patch("app.routers.irpf.generate_irpf_pdf", new=Mock(return_value=b"%PDF")) as generate,
        patch(
            "app.routers.irpf.generate_irpf_report",
            new=AsyncMock(side_effect=AssertionError("legacy report must not be used")),
        ),
    ):
        response = await download_irpf_pdf(7, 2024, db, user)

    compose.assert_awaited_once_with(db, 7, 2024)
    generate.assert_called_once_with(export)
    assert response.media_type == "application/pdf"
    assert response.body == b"%PDF"


@pytest.mark.asyncio
async def test_csv_endpoint_uses_only_canonical_export_composition() -> None:
    db = AsyncMock()
    user = SimpleNamespace(id=9)
    export = _canonical_export()

    with (
        patch(
            "app.routers.irpf._get_portfolio",
            new=AsyncMock(return_value=SimpleNamespace(id=7, user_id=9)),
        ),
        patch(
            "app.routers.irpf.build_irpf_canonical_export",
            new=AsyncMock(return_value=export),
        ) as compose,
        patch("app.routers.irpf.generate_irpf_csv", new=Mock(return_value="ok")) as generate,
        patch(
            "app.routers.irpf.generate_irpf_report",
            new=AsyncMock(side_effect=AssertionError("legacy report must not be used")),
        ),
    ):
        response = await download_irpf_csv(7, 2024, db, user)

    compose.assert_awaited_once_with(db, 7, 2024)
    generate.assert_called_once_with(export)
    assert response.media_type == "text/csv"
    assert response.body == b"ok"
