"""
Router IRPF — endpoints finos que delegam toda logica aos serviços de IRPF.

Endpoints:
  GET  /{portfolio_id}/irpf/anos          — anos com transacoes disponiveis
  GET  /{portfolio_id}/irpf/{year}        — relatorio IRPF completo (JSON)
  GET  /{portfolio_id}/irpf/{year}/pdf    — download do relatorio em PDF
  GET  /{portfolio_id}/irpf/{year}/bens   — so bens e direitos
  GET  /{portfolio_id}/irpf/{year}/ganhos — so ganhos de capital mensais
  GET  /{portfolio_id}/irpf/{year}/rendimentos — so proventos (dividendos + JCP)
"""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.irpf import BemDireito, GanhoCapitalMensal, IRPFReportOut
from app.services.irpf_bens_direitos_service import calc_bens_direitos
from app.services.irpf_service import (
    calc_ganhos_capital,
    calc_rendimentos,
    generate_irpf_csv,
    generate_irpf_pdf,
    generate_irpf_report,
)

router = APIRouter(tags=["irpf"])


async def _get_portfolio(portfolio_id: int, user: User, db: AsyncSession) -> Portfolio:
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


@router.get("/{portfolio_id}/irpf/anos", response_model=List[int])
async def list_anos(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna os anos com transações disponíveis na carteira."""
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
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna o relatório IRPF completo para o ano."""
    await _get_portfolio(portfolio_id, current_user, db)

    if not refresh:
        from app.models.irpf import IRPFReport

        existing = await db.execute(
            select(IRPFReport).where(
                IRPFReport.portfolio_id == portfolio_id,
                IRPFReport.year == year,
            )
        )
        row = existing.scalar_one_or_none()
        if row and row.data:
            return IRPFReportOut.model_validate(json.loads(row.data))

    return await generate_irpf_report(db, portfolio_id, year)


@router.get("/{portfolio_id}/irpf/{year}/pdf")
async def download_irpf_pdf(
    portfolio_id: int,
    year: int,
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera e retorna o relatório IRPF em PDF."""
    await _get_portfolio(portfolio_id, current_user, db)
    report = (
        await generate_irpf_report(db, portfolio_id, year)
        if refresh
        else await get_irpf_report(portfolio_id, year, False, db, current_user)
    )

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
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera e retorna o relatório IRPF em CSV."""
    await _get_portfolio(portfolio_id, current_user, db)
    report = (
        await generate_irpf_report(db, portfolio_id, year)
        if refresh
        else await get_irpf_report(portfolio_id, year, False, db, current_user)
    )
    csv_content = generate_irpf_csv(report)

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="irpf_{year}_{portfolio_id}.csv"'
        },
    )


@router.get("/{portfolio_id}/irpf/{year}/bens", response_model=List[BemDireito])
async def get_bens_direitos(
    portfolio_id: int,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna Bens e Direitos projetados canonicamente em 31/12."""
    await _get_portfolio(portfolio_id, current_user, db)
    return await calc_bens_direitos(db, portfolio_id, year)


@router.get("/{portfolio_id}/irpf/{year}/ganhos", response_model=List[GanhoCapitalMensal])
async def get_ganhos_capital(
    portfolio_id: int,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna ganhos de capital mensais com detalhamento por venda."""
    await _get_portfolio(portfolio_id, current_user, db)
    return await calc_ganhos_capital(db, portfolio_id, year)


@router.get("/{portfolio_id}/irpf/{year}/rendimentos")
async def get_rendimentos(
    portfolio_id: int,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna dividendos e JCP do ano."""
    await _get_portfolio(portfolio_id, current_user, db)
    dividendos, jcp = await calc_rendimentos(db, portfolio_id, year)
    return {"dividendos": dividendos, "jcp": jcp}
