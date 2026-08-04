/**
 * Tipos TypeScript espelho dos schemas Pydantic do módulo IRPF.
 */

export interface BemDireito {
  ticker: string
  nome: string
  asset_type: string
  codigo_irpf: string
  grupo_irpf: string
  quantidade: number
  custo_medio: number
  custo_total: number
  moeda: string
  cnpj_fundo?: string | null
  country?: string | null
}

export interface VendaMensal {
  ticker: string
  asset_type: string
  data: string
  quantidade: number
  preco_venda: number
  custo_aquisicao: number
  lucro_bruto: number
  is_day_trade: boolean
  is_isento: boolean
  ir_retido: number
}

export interface GanhoCapitalMensal {
  mes: string
  total_vendas: number
  total_custo: number
  lucro_bruto: number
  lucro_day_trade: number
  lucro_swing_trade: number
  isencao_aplicada: number
  base_calculo: number
  aliquota_swing: number
  aliquota_day_trade: number
  ir_devido_swing: number
  ir_devido_day_trade: number
  ir_retido_fonte: number
  ir_a_recolher: number
  vendas: VendaMensal[]
}

export interface RendimentoIsento {
  ticker: string
  asset_type: string
  total_recebido: number
  quantidade_pgtos: number
}

export interface JCPItem {
  ticker: string
  total_bruto: number
  ir_retido: number
  total_liquido: number
}

export interface IRPFResumo {
  ano: number
  total_bens_direitos: number
  total_vendas_ano: number
  lucro_tributavel_swing: number
  lucro_tributavel_day_trade: number
  ir_swing_trade_devido: number
  ir_day_trade_devido: number
  ir_retido_fonte_total: number
  ir_a_recolher_total: number
  total_dividendos_isentos: number
  total_jcp_bruto: number
  total_jcp_ir_retido: number
  prejuizo_acumulado: number
}

export interface IRPFReportOut {
  portfolio_id: number
  ano: number
  bens_direitos: BemDireito[]
  ganhos_mensais: GanhoCapitalMensal[]
  dividendos: RendimentoIsento[]
  jcp: JCPItem[]
  resumo: IRPFResumo
}

export interface IRPFCanonicalMonthlyAssessment {
  competence_month: string
  swing_gross_tax_due_brl: string
  swing_withholding_brl: string
  swing_net_tax_due_brl: string
  day_trade_gross_tax_due_brl: string
  day_trade_withholding_brl: string
  day_trade_net_tax_due_brl: string
  total_net_tax_due_brl: string
  payment_due_brl: string
  closing_accumulated_tax_brl: string
}

export interface IRPFCanonicalAnnualAssessment {
  schema_version: 'irpf-annual-assessment.v1'
  portfolio_id: number
  year: number
  monthly: IRPFCanonicalMonthlyAssessment[]
  total_gross_tax_due_brl: string
  total_withholding_brl: string
  total_net_tax_due_brl: string
  total_payment_due_brl: string
  closing_accumulated_tax_brl: string
  closing_common_withholding_balance_brl: string
  closing_day_trade_withholding_balance_brl: string
  closing_day_trade_loss_carryforward_brl: string
}

export interface IRPFCanonicalAssetsAssessment {
  schema_version: 'irpf-assets-assessment.v1'
  portfolio_id: number
  year: number
  items: BemDireito[]
  total_cost_brl: string
}

export interface IRPFCanonicalCapitalGainsAssessment {
  schema_version: 'irpf-capital-gains-assessment.v1'
  portfolio_id: number
  year: number
  months: GanhoCapitalMensal[]
  total_sales_brl: string
  total_gross_profit_brl: string
  total_tax_due_brl: string
}

export interface IRPFCanonicalIncomeAssessment {
  schema_version: 'irpf-income-assessment.v1'
  portfolio_id: number
  year: number
  dividends: RendimentoIsento[]
  jcp: JCPItem[]
  total_dividends_brl: string
  total_jcp_gross_brl: string
  total_jcp_withholding_brl: string
  total_jcp_net_brl: string
}
