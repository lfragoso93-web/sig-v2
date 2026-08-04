"""
Schemas do modulo IRPF.

Cobre:
  - Bens e Direitos (posicao em 31/12)
  - Ganhos de Capital mensais (BR + internacionais)
  - Rendimentos Isentos (dividendos)
  - JCP (tributavel na fonte)
  - Resumo anual consolidado
  - Envelope de resposta IRPFReportOut
  - Contrato canonico anual versionado
"""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Bens e Direitos
# ---------------------------------------------------------------------------

class BemDireito(BaseModel):
    """
    Posicao de um ativo em 31/12 do ano-base para declaracao.
    codigo_irpf segue tabela RFB: 31=acoes, 73=FIIs, 74=ETFs, 99=outros.
    """
    ticker:          str
    nome:            str
    asset_type:      str
    codigo_irpf:     str           # ex: "31", "73", "74"
    grupo_irpf:      str           # ex: "03 - Participacoes Societarias"
    quantidade:      float
    custo_medio:     float         # preco medio de aquisicao em BRL
    custo_total:     float         # quantidade * custo_medio
    moeda:           str = "BRL"
    cnpj_fundo:      Optional[str] = None
    country:         Optional[str] = None


# ---------------------------------------------------------------------------
# Ganhos de Capital
# ---------------------------------------------------------------------------

class VendaMensal(BaseModel):
    """
    Venda individual dentro de um mes para calculo de ganho de capital.
    """
    ticker:          str
    asset_type:      str
    data:             str           # "YYYY-MM-DD"
    quantidade:      float
    preco_venda:     float          # por unidade em BRL
    custo_aquisicao: float          # custo medio na data da venda em BRL
    lucro_bruto:     float          # (preco_venda - custo_aquisicao) * quantidade
    is_day_trade:    bool = False
    is_isento:       bool = False   # True quando total vendas do mes <= R$20k (so acoes)
    ir_retido:       float = 0.0    # IR ja retido na fonte (ex: FIIs 0.005)


class GanhoCapitalMensal(BaseModel):
    """
    Consolidado de ganhos/perdas de capital em um mes.
    """
    mes:                   str      # "YYYY-MM"
    total_vendas:          float
    total_custo:           float
    lucro_bruto:           float
    lucro_day_trade:       float
    lucro_swing_trade:     float
    isencao_aplicada:      float    # valor isento (vendas <= 20k ações)
    base_calculo:          float    # lucro tributavel apos isencoes
    aliquota_swing:        float    # 0.15 acoes/FIIs, 0.20 ETFs/intl
    aliquota_day_trade:    float    # 0.20
    ir_devido_swing:       float
    ir_devido_day_trade:   float
    ir_retido_fonte:       float
    ir_a_recolher:         float    # ir_devido - ir_retido
    vendas:                list[VendaMensal] = []


# ---------------------------------------------------------------------------
# Rendimentos
# ---------------------------------------------------------------------------

class RendimentoIsento(BaseModel):
    """
    Dividendo recebido no ano (isento de IR para pessoa fisica BR).
    """
    ticker:            str
    asset_type:        str
    total_recebido:    float
    quantidade_pgtos:  int


class JCPItem(BaseModel):
    """
    Juros sobre Capital Proprio: tributado 15% na fonte.
    """
    ticker:         str
    total_bruto:    float
    ir_retido:      float   # 15% do bruto
    total_liquido:  float


# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------

class IRPFResumo(BaseModel):
    """
    Totais anuais consolidados para o quadro-resumo da declaracao.
    """
    ano:                           int
    total_bens_direitos:           float   # custo total dos ativos em 31/12
    total_vendas_ano:              float
    lucro_tributavel_swing:        float
    lucro_tributavel_day_trade:    float
    ir_swing_trade_devido:         float
    ir_day_trade_devido:           float
    ir_retido_fonte_total:         float
    ir_a_recolher_total:           float   # saldo a pagar
    total_dividendos_isentos:      float
    total_jcp_bruto:               float
    total_jcp_ir_retido:           float
    prejuizo_acumulado:            float   # prejuizo a compensar em meses futuros


# ---------------------------------------------------------------------------
# Envelope de resposta
# ---------------------------------------------------------------------------

class IRPFReportOut(BaseModel):
    """
    Resposta completa do endpoint GET /{portfolio_id}/irpf/{year}.
    """
    portfolio_id:    int
    ano:             int
    bens_direitos:   list[BemDireito] = []
    ganhos_mensais:  list[GanhoCapitalMensal] = []
    dividendos:      list[RendimentoIsento] = []
    jcp:             list[JCPItem] = []
    resumo:          IRPFResumo


# ---------------------------------------------------------------------------
# Apuracao anual canonica
# ---------------------------------------------------------------------------

class IrpfMonthlyAssessmentOut(BaseModel):
    competence_month: str
    swing_gross_tax_due_brl: Decimal
    swing_withholding_brl: Decimal
    swing_net_tax_due_brl: Decimal
    day_trade_gross_tax_due_brl: Decimal
    day_trade_withholding_brl: Decimal
    day_trade_net_tax_due_brl: Decimal
    total_net_tax_due_brl: Decimal
    payment_due_brl: Decimal
    closing_accumulated_tax_brl: Decimal


class IrpfAnnualAssessmentOut(BaseModel):
    schema_version: str
    portfolio_id: int
    year: int
    monthly: list[IrpfMonthlyAssessmentOut]
    total_gross_tax_due_brl: Decimal
    total_withholding_brl: Decimal
    total_net_tax_due_brl: Decimal
    total_payment_due_brl: Decimal
    closing_accumulated_tax_brl: Decimal
    closing_common_withholding_balance_brl: Decimal
    closing_day_trade_withholding_balance_brl: Decimal
    closing_day_trade_loss_carryforward_brl: Decimal
