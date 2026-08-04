"""Composição read-only das exportações canônicas de IRPF."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.irpf import BemDireito, GanhoCapitalMensal, JCPItem, RendimentoIsento
from app.services.irpf_annual_assessment_service import build_irpf_annual_assessment
from app.services.irpf_bens_direitos_service import calc_bens_direitos
from app.services.irpf_tax_service import calc_ganhos_capital, calc_rendimentos


@dataclass(frozen=True)
class IrpfCanonicalExport:
    portfolio_id: int
    year: int
    bens_direitos: list[BemDireito]
    ganhos_mensais: list[GanhoCapitalMensal]
    dividendos: list[RendimentoIsento]
    jcp: list[JCPItem]
    total_bens_direitos_brl: Decimal
    total_vendas_ano_brl: Decimal
    total_gross_tax_due_brl: Decimal
    total_withholding_brl: Decimal
    total_payment_due_brl: Decimal
    total_dividendos_brl: Decimal
    total_jcp_bruto_brl: Decimal
    total_jcp_ir_retido_brl: Decimal
    closing_day_trade_loss_carryforward_brl: Decimal


async def build_irpf_canonical_export(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> IrpfCanonicalExport:
    annual = await build_irpf_annual_assessment(db, portfolio_id, year)
    bens_direitos = await calc_bens_direitos(db, portfolio_id, year)
    ganhos_mensais = await calc_ganhos_capital(db, portfolio_id, year)
    dividendos, jcp = await calc_rendimentos(db, portfolio_id, year)

    return IrpfCanonicalExport(
        portfolio_id=portfolio_id,
        year=year,
        bens_direitos=bens_direitos,
        ganhos_mensais=ganhos_mensais,
        dividendos=dividendos,
        jcp=jcp,
        total_bens_direitos_brl=sum(
            Decimal(str(item.custo_total)) for item in bens_direitos
        ),
        total_vendas_ano_brl=sum(
            Decimal(str(item.total_vendas)) for item in ganhos_mensais
        ),
        total_gross_tax_due_brl=annual.total_gross_tax_due_brl,
        total_withholding_brl=annual.total_withholding_brl,
        total_payment_due_brl=annual.total_payment_due_brl,
        total_dividendos_brl=sum(
            Decimal(str(item.total_recebido)) for item in dividendos
        ),
        total_jcp_bruto_brl=sum(Decimal(str(item.total_bruto)) for item in jcp),
        total_jcp_ir_retido_brl=sum(Decimal(str(item.ir_retido)) for item in jcp),
        closing_day_trade_loss_carryforward_brl=(
            annual.closing_day_trade_loss_carryforward_brl
        ),
    )
