"""Fachada temporária das regras fiscais e exportações do IRPF.

Bens e Direitos e a geração/persistência do relatório completo foram migrados
para serviços canônicos dedicados. Este módulo permanece apenas para preservar
imports dos cálculos fiscais e exportadores durante a próxima etapa da #56.
"""

from app.services.irpf_export_service import generate_irpf_csv, generate_irpf_pdf
from app.services.irpf_tax_service import calc_ganhos_capital, calc_rendimentos

__all__ = [
    "calc_ganhos_capital",
    "calc_rendimentos",
    "generate_irpf_csv",
    "generate_irpf_pdf",
]
