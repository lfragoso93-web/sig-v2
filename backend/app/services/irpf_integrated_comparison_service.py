"""Orquestra comparação anual integrada read-only contra o legado fiscal."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.irpf_annual_integrated_assessment_service import (
    assess_annual_integrated_operations,
)
from app.services.irpf_integrated_legacy_comparison import (
    IntegratedFiscalAnnualComparison,
    build_integrated_annual_comparison,
)
from app.services.irpf_tax_service import calc_ganhos_capital


async def compare_annual_integrated_with_legacy(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> IntegratedFiscalAnnualComparison:
    """Executa os caminhos integrado e legado uma vez e compara por competência."""

    canonical = await assess_annual_integrated_operations(db, portfolio_id, year)
    legacy = await calc_ganhos_capital(db, portfolio_id, year)
    return build_integrated_annual_comparison(
        portfolio_id=portfolio_id,
        year=year,
        canonical=canonical,
        legacy_months=legacy,
    )
