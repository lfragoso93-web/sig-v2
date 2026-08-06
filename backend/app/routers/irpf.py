"""
Router IRPF — endpoints finos que delegam toda logica aos servicos de IRPF.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.portfolio import Portfolio
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
from app.services.irpf_bens_direitos_service import calc_bens_direitos
from app.services.irpf_canonical_export_service import build_irpf_canonical_export
from app.services.irpf_export_service import generate_irpf_csv, generate_irpf_pdf
from app.services.irpf_report_service import generate_irpf_report
from app.services.irpf_tax_service import calc_ganhos_capital, calc_rendimentos

router = APIRouter(tags=["irpf"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def _get_portfolio(
    portfolio_id: int,
    user: User,
    db: AsyncSession,
) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")
    return portfolio


@router.get("/{portfolio_id}/irpf/anos", response_model=list[int])
async def list_anos(
    portfolio_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna os anos com transacoes disponiveis na carteira."""
    await _get_portfolio(portfolio_id, current_user, db)
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
    await _get_portfolio(portfolio_id, current_user, db)
    _ = refresh  # Compatibilidade do contrato HTTP legado; nao existe cache persistido.
    return await generate_irpf_report(db, portfolio_id, year)


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
    await _get_portfolio(portfolio_id, current_user, db)
    contract = await build_irpf_annual_assessment(db, portfolio_id, year)
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
    await _get_portfolio(portfolio_id, current_user, db)
    items = await calc_bens_direitos(db, portfolio_id, year)
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
    await _get_portfolio(portfolio_id, current_user, db)
    months = await calc_ganhos_capital(db, portfolio_id, year)
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
    await _get_portfolio(portfolio_id, current_user, db)
    dividends, jcp = await calc_rendimentos(db, portfolio_id, year)
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
    await _get_portfolio(portfolio_id, current_user, db)
    report = await build_irpf_canonical_export(db, portfolio_id, year)

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
    await _get_portfolio(portfolio_id, current_user, db)
    report = await build_irpf_canonical_export(db, portfolio_id, year)
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
    await _get_portfolio(portfolio_id, current_user, db)
    return await calc_bens_direitos(db, portfolio_id, year)


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
    await _get_portfolio(portfolio_id, current_user, db)
    return await calc_ganhos_capital(db, portfolio_id, year)


@router.get("/{portfolio_id}/irpf/{year}/rendimentos")
async def get_rendimentos(
    portfolio_id: int,
    year: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Retorna dividendos e JCP do ano."""
    await _get_portfolio(portfolio_id, current_user, db)
    dividendos, jcp = await calc_rendimentos(db, portfolio_id, year)
    return {"dividendos": dividendos, "jcp": jcp}
