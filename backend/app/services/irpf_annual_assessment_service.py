"""Serviço read-only que expõe a apuração anual no contrato canônico v1."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.services.irpf_annual_assessment_contract import IrpfAnnualAssessmentContract
from app.services.irpf_annual_assessment_contract_mapper import (
    build_irpf_annual_assessment_contract,
)
from app.services.irpf_annual_integrated_assessment_service import (
    assess_annual_integrated_operations,
)
from app.services.irpf_access_service import require_irpf_access


async def build_irpf_annual_assessment(
    db: AsyncSession,
    access: PortfolioAccessContext,
    year: int,
) -> IrpfAnnualAssessmentContract:
    """Executa a apuração integrada e devolve o contrato versionado."""

    await require_irpf_access(db, access)
    assessment = await assess_annual_integrated_operations(
        db,
        access.portfolio_id,
        year,
    )
    return build_irpf_annual_assessment_contract(assessment)
