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
