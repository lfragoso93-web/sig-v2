"""
Router IRPF — endpoints finos que delegam toda logica aos servicos de IRPF.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.irpf import (
    BemDireito,
    GanhoCapitalMensal,
    IrpfAnnualAssessmentOut,
    IrpfAssetsAssessmentOut,
    IrpfCapitalGainsAssessmentOut,
    IrpfIncomeAssessmentOut,
    IRPFReportOut,
)
from app.services.irpf_annual_assessment_service import build_irpf_annual_assessment
from app.services.irpf_access_service import (
    READ_PORTFOLIO_IRPF,
    require_irpf_access,
    read_irpf_assets,
    read_irpf_capital_gains,
    read_irpf_income,
)
from app.services.irpf_canonical_export_service import build_irpf_canonical_export
from app.services.irpf_export_service import generate_irpf_csv, generate_irpf_pdf
from app.services.irpf_report_service import generate_irpf_report

router = APIRouter(tags=["irpf"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _access_context(portfolio_id: int, user: User) -> PortfolioAccessContext:
    if portfolio_id <= 0:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")
    return PortfolioAccessContext.for_user(
        user_id=user.id,
        portfolio_id=portfolio_id,
        permissions=frozenset({READ_PORTFOLIO_IRPF}),
    )


@router.get("/{portfolio_id}/irpf/anos", response_model=list[int])
async def list_anos(
    portfolio_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna os anos com transacoes disponiveis na carteira."""
    access = _access_context(portfolio_id, current_user)
    await require_irpf_access(db, access)
    result = await db.execute(
        select(extract("year", Transaction.date).label("year"))
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
        .order_by(extract("year", Transaction.date).desc())
    )
    return [int(row[0]) for row in result.all()]


@router.get("/{portfolio_id}/irpf/{year}", response_model=IRPFReportOut)
async def get_irpf_report(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
    refresh: bool = False,
):
    """Retorna o relatorio IRPF completo, sempre projetado read-only em memoria."""
    access = _access_context(portfolio_id, current_user)
    _ = refresh  # Compatibilidade do contrato HTTP legado; nao existe cache persistido.
    return await generate_irpf_report(db, access, year)


@router.get(
    "/{portfolio_id}/irpf/{year}/canonical",
    response_model=IrpfAnnualAssessmentOut,
)
async def get_canonical_irpf_assessment(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna a apuracao anual canonica read-only da carteira autorizada."""
    access = _access_context(portfolio_id, current_user)
    contract = await build_irpf_annual_assessment(db, access, year)
    return IrpfAnnualAssessmentOut.model_validate(contract.to_dict())


@router.get(
    "/{portfolio_id}/irpf/{year}/canonical/assets",
    response_model=IrpfAssetsAssessmentOut,
)
async def get_canonical_irpf_assets(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna Bens e Direitos canônicos em envelope público versionado."""
    access = _access_context(portfolio_id, current_user)
    items = await read_irpf_assets(db, access, year)
    total_cost = sum(Decimal(str(item.custo_total)) for item in items)
    return IrpfAssetsAssessmentOut(
        schema_version="irpf-assets-assessment.v1",
        portfolio_id=portfolio_id,
        year=year,
        items=items,
        total_cost_brl=total_cost,
    )


@router.get(
    "/{portfolio_id}/irpf/{year}/canonical/capital-gains",
    response_model=IrpfCapitalGainsAssessmentOut,
)
async def get_canonical_irpf_capital_gains(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna Ganhos de Capital em envelope público versionado."""
    access = _access_context(portfolio_id, current_user)
    months = await read_irpf_capital_gains(db, access, year)
    return IrpfCapitalGainsAssessmentOut(
        schema_version="irpf-capital-gains-assessment.v1",
        portfolio_id=portfolio_id,
        year=year,
        months=months,
        total_sales_brl=sum(Decimal(str(item.total_vendas)) for item in months),
        total_gross_profit_brl=sum(
            Decimal(str(item.lucro_bruto)) for item in months
        ),
        total_tax_due_brl=sum(Decimal(str(item.ir_a_recolher)) for item in months),
    )


@router.get(
    "/{portfolio_id}/irpf/{year}/canonical/income",
    response_model=IrpfIncomeAssessmentOut,
)
async def get_canonical_irpf_income(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna dividendos e JCP canônicos em envelope público versionado."""
    access = _access_context(portfolio_id, current_user)
    dividends, jcp = await read_irpf_income(db, access, year)
    return IrpfIncomeAssessmentOut(
        schema_version="irpf-income-assessment.v1",
        portfolio_id=portfolio_id,
        year=year,
        dividends=dividends,
        jcp=jcp,
        total_dividends_brl=sum(
            Decimal(str(item.total_recebido)) for item in dividends
        ),
        total_jcp_gross_brl=sum(Decimal(str(item.total_bruto)) for item in jcp),
        total_jcp_withholding_brl=sum(
            Decimal(str(item.ir_retido)) for item in jcp
        ),
        total_jcp_net_brl=sum(Decimal(str(item.total_liquido)) for item in jcp),
    )


@router.get("/{portfolio_id}/irpf/{year}/pdf")
async def download_irpf_pdf(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Gera e retorna o relatorio IRPF canônico em PDF."""
    access = _access_context(portfolio_id, current_user)
    report = await build_irpf_canonical_export(db, access, year)

    try:
        pdf_bytes = generate_irpf_pdf(report)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="irpf_{year}_{portfolio_id}.pdf"'
        },
    )


@router.get("/{portfolio_id}/irpf/{year}/csv")
async def download_irpf_csv(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Gera e retorna o relatorio IRPF canônico em CSV."""
    access = _access_context(portfolio_id, current_user)
    report = await build_irpf_canonical_export(db, access, year)
    csv_content = generate_irpf_csv(report)

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="irpf_{year}_{portfolio_id}.csv"'
        },
    )


@router.get("/{portfolio_id}/irpf/{year}/bens", response_model=list[BemDireito])
async def get_bens_direitos(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna Bens e Direitos projetados canonicamente em 31/12."""
    access = _access_context(portfolio_id, current_user)
    return await read_irpf_assets(db, access, year)


@router.get(
    "/{portfolio_id}/irpf/{year}/ganhos",
    response_model=list[GanhoCapitalMensal],
)
async def get_ganhos_capital(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna ganhos de capital mensais com detalhamento por venda."""
    access = _access_context(portfolio_id, current_user)
    return await read_irpf_capital_gains(db, access, year)


@router.get("/{portfolio_id}/irpf/{year}/rendimentos")
async def get_rendimentos(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna dividendos e JCP do ano."""
    access = _access_context(portfolio_id, current_user)
    dividendos, jcp = await read_irpf_income(db, access, year)
    return {"dividendos": dividendos, "jcp": jcp}
