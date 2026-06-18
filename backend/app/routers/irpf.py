"""
Router IRPF — endpoints finos que delegam toda logica ao irpf_service.

Endpoints:
  GET  /{portfolio_id}/irpf/anos          — anos com transacoes disponiveis
  GET  /{portfolio_id}/irpf/{year}        — relatorio IRPF completo (JSON)
  GET  /{portfolio_id}/irpf/{year}/pdf    — download do relatorio em PDF
  GET  /{portfolio_id}/irpf/{year}/bens   — so bens e direitos
  GET  /{portfolio_id}/irpf/{year}/ganhos — so ganhos de capital mensais
  GET  /{portfolio_id}/irpf/{year}/rendimentos — so proventos (dividendos + JCP)
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, extract
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.schemas.irpf import (
    IRPFReportOut,
    BemDireito,
    GanhoCapitalMensal,
    RendimentoIsento,
    JCPItem,
)
from app.services.irpf_service import (
    generate_irpf_report,
    calc_bens_direitos,
    calc_ganhos_capital,
    calc_rendimentos,
    generate_irpf_pdf,
)

router = APIRouter(tags=["irpf"])


async def _get_portfolio(portfolio_id: int, user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")
    return p


@router.get("/{portfolio_id}/irpf/anos", response_model=List[int])
async def list_anos(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna lista de anos com transacoes na carteira.
    Usado pelo dropdown de selecao de ano na pagina IRPF.
    """
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
    """
    Retorna relatorio IRPF completo para o ano.
    Se refresh=True ou nao houver relatorio salvo, recalcula e persiste.
    """
    await _get_portfolio(portfolio_id, current_user, db)

    if not refresh:
        from app.models.irpf import IRPFReport
        import json
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
    """
    Gera e retorna o relatorio IRPF em PDF para download.
    Content-Type: application/pdf
    Content-Disposition: attachment; filename="irpf_{year}_{portfolio_id}.pdf"
    """
    await _get_portfolio(portfolio_id, current_user, db)
    report = await generate_irpf_report(db, portfolio_id, year) if refresh else \
        await get_irpf_report(portfolio_id, year, False, db, current_user)

    try:
        pdf_bytes = generate_irpf_pdf(report)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="irpf_{year}_{portfolio_id}.pdf"'
        },
    )


@router.get("/{portfolio_id}/irpf/{year}/bens", response_model=List[BemDireito])
async def get_bens_direitos(
    portfolio_id: int,
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna apenas a lista de Bens e Direitos em 31/12 do ano."""
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
    """Retorna proventos do ano separados em dividendos isentos e JCP."""
    await _get_portfolio(portfolio_id, current_user, db)
    dividendos, jcp = await calc_rendimentos(db, portfolio_id, year)
    return {"dividendos": dividendos, "jcp": jcp}
