"""Serviço read-only que expõe a apuração anual no contrato canônico v1."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.irpf_annual_assessment_contract import IrpfAnnualAssessmentContract
from app.services.irpf_annual_assessment_contract_mapper import (
    build_irpf_annual_assessment_contract,
)
from app.services.irpf_annual_integrated_assessment_service import (
    assess_annual_integrated_operations,
)


async def build_irpf_annual_assessment(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> IrpfAnnualAssessmentContract:
    """Executa a apuração integrada e devolve o contrato versionado."""

    assessment = await assess_annual_integrated_operations(
        db,
        portfolio_id,
        year,
    )
    return build_irpf_annual_assessment_contract(assessment)
