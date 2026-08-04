"""Fachada temporária das regras fiscais e exportações do IRPF.

Bens e Direitos e a geração/persistência do relatório completo foram migrados
para serviços canônicos dedicados. Este módulo preserva imports históricos sem
reintroduzir consultas ou persistência legadas nos endpoints canônicos.
"""

from decimal import Decimal

from app.schemas.irpf import IRPFReportOut
from app.services.irpf_canonical_export_service import IrpfCanonicalExport
from app.services.irpf_export_service import (
    generate_irpf_csv as generate_canonical_irpf_csv,
)
from app.services.irpf_export_service import (
    generate_irpf_pdf as generate_canonical_irpf_pdf,
)
from app.services.irpf_tax_service import calc_ganhos_capital, calc_rendimentos


def _adapt_legacy_export(report: IRPFReportOut) -> IrpfCanonicalExport:
    """Converte o contrato legado em memória para o exportador canônico.

    Esta compatibilidade existe somente para consumidores Python históricos.
    Não consulta banco, não lê ``IRPFReport`` e não participa dos endpoints
    públicos PDF/CSV, que já constroem ``IrpfCanonicalExport`` diretamente.
    """

    summary = report.resumo
    return IrpfCanonicalExport(
        portfolio_id=report.portfolio_id,
        year=report.ano,
        bens_direitos=report.bens_direitos,
        ganhos_mensais=report.ganhos_mensais,
        dividendos=report.dividendos,
        jcp=report.jcp,
        total_bens_direitos_brl=Decimal(str(summary.total_bens_direitos)),
        total_vendas_ano_brl=Decimal(str(summary.total_vendas_ano)),
        total_gross_tax_due_brl=(
            Decimal(str(summary.ir_swing_trade_devido))
            + Decimal(str(summary.ir_day_trade_devido))
        ),
        total_withholding_brl=Decimal(str(summary.ir_retido_fonte_total)),
        total_payment_due_brl=Decimal(str(summary.ir_a_recolher_total)),
        total_dividendos_brl=Decimal(str(summary.total_dividendos_isentos)),
        total_jcp_bruto_brl=Decimal(str(summary.total_jcp_bruto)),
        total_jcp_ir_retido_brl=Decimal(str(summary.total_jcp_ir_retido)),
        closing_day_trade_loss_carryforward_brl=Decimal(
            str(summary.prejuizo_acumulado)
        ),
    )


def generate_irpf_pdf(report: IrpfCanonicalExport | IRPFReportOut) -> bytes:
    """Gera PDF canônico, adaptando somente contratos Python históricos."""

    canonical = (
        _adapt_legacy_export(report)
        if isinstance(report, IRPFReportOut)
        else report
    )
    return generate_canonical_irpf_pdf(canonical)


def generate_irpf_csv(report: IrpfCanonicalExport | IRPFReportOut) -> str:
    """Gera CSV canônico, adaptando somente contratos Python históricos."""

    canonical = (
        _adapt_legacy_export(report)
        if isinstance(report, IRPFReportOut)
        else report
    )
    return generate_canonical_irpf_csv(canonical)


__all__ = [
    "calc_ganhos_capital",
    "calc_rendimentos",
    "generate_irpf_csv",
    "generate_irpf_pdf",
]
