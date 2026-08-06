"""Orquestração read-only do relatório IRPF sobre contratos canônicos."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.irpf import IRPFReportOut, IRPFResumo
from app.services.irpf_bens_direitos_service import calc_bens_direitos
from app.services.irpf_service import calc_ganhos_capital, calc_rendimentos


async def generate_irpf_report(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> IRPFReportOut:
    """Gera o relatório exclusivamente em memória usando leitores canônicos."""

    bens = await calc_bens_direitos(db, portfolio_id, year)
    ganhos = await calc_ganhos_capital(db, portfolio_id, year)
    dividendos, jcp = await calc_rendimentos(db, portfolio_id, year)

    total_ir_swing = sum(item.ir_devido_swing for item in ganhos)
    total_ir_day_trade = sum(item.ir_devido_day_trade for item in ganhos)
    total_ir_retido = sum(item.ir_retido_fonte for item in ganhos)
    prejuizo = sum(
        item.lucro_swing_trade
        for item in ganhos
        if item.lucro_swing_trade < 0
    )

    resumo = IRPFResumo(
        ano=year,
        total_bens_direitos=round(sum(item.custo_total for item in bens), 2),
        total_vendas_ano=round(sum(item.total_vendas for item in ganhos), 2),
        lucro_tributavel_swing=round(sum(item.base_calculo for item in ganhos), 2),
        lucro_tributavel_day_trade=round(
            sum(
                item.lucro_day_trade
                for item in ganhos
                if item.lucro_day_trade > 0
            ),
            2,
        ),
        ir_swing_trade_devido=round(total_ir_swing, 2),
        ir_day_trade_devido=round(total_ir_day_trade, 2),
        ir_retido_fonte_total=round(total_ir_retido, 2),
        ir_a_recolher_total=round(
            total_ir_swing + total_ir_day_trade - total_ir_retido,
            2,
        ),
        total_dividendos_isentos=round(
            sum(item.total_recebido for item in dividendos),
            2,
        ),
        total_jcp_bruto=round(sum(item.total_bruto for item in jcp), 2),
        total_jcp_ir_retido=round(sum(item.ir_retido for item in jcp), 2),
        prejuizo_acumulado=round(prejuizo, 2),
    )

    return IRPFReportOut(
        portfolio_id=portfolio_id,
        ano=year,
        bens_direitos=bens,
        ganhos_mensais=ganhos,
        dividendos=dividendos,
        jcp=jcp,
        resumo=resumo,
    )
