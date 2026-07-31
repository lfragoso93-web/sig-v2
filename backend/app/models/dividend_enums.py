"""Public dividend enums independent from the legacy portfolio-right ORM."""

from enum import Enum


class DividendType(str, Enum):
    DIVIDENDO = "DIVIDENDO"
    JCP = "JCP"
    RENDIMENTO = "RENDIMENTO"
    AMORTIZACAO = "AMORTIZACAO"
    BONIFICACAO = "BONIFICACAO"
    SUBSCRICAO = "SUBSCRICAO"
    OUTROS = "OUTROS"


class DividendStatus(str, Enum):
    RECEBIDO = "RECEBIDO"
    PENDENTE = "PENDENTE"
    CANCELADO = "CANCELADO"
    A_RECEBER = "A_RECEBER"
