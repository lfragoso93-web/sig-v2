import api from './api'

export interface RentabilidadeKpis {
  contract_version: 'rentabilidade.v2'
  patrimonio_atual: number
  custo_posicoes_abertas: number
  resultado_nao_realizado: number
  resultado_realizado: number
  resultado_total: number
  proventos_total: number
  proventos_12m: number
  twr_dia_pct: number | null
  twr_mes_pct: number | null
  twr_12m_pct: number | null
  twr_desde_inicio_pct: number | null
  valuation_updated_at: string | null
  performance_as_of: string | null
  proventos_as_of: string | null
  return_is_estimated: boolean
  has_partial_prices: boolean
  price_coverage_pct: number
  performance_source: 'portfolio_snapshot_twr' | 'unavailable'
}

export interface RentabilidadeAtivo {
  ticker: string
  name: string
  asset_type: string | null
  quantity: number
  avg_price: number
  current_price: number | null
  total_invested: number
  current_value: number
  unrealized_pnl: number
  unrealized_pct: number | null
  realized_pnl: number
  total_pnl: number
  total_pnl_pct: number | null
  is_open: boolean
  result_source: 'canonical_positions_and_realized_pnl' | 'canonical_realized_pnl'
}

export type ClassValuationMethod =
  | 'intraday_market_valuation'
  | 'treasury_mark_to_market'
  | 'fixed_income_accrual'

export interface RentabilidadeClasse {
  asset_type: string
  current_value: number
  cost_basis: number
  capital_result_value: number | null
  capital_result_pct: number | null
  received_dividends: number
  total_result_value: number | null
  total_result_pct: number | null
  allocation_pct: number
  asset_count: number
  current_metrics_available: boolean
  valuation_method: ClassValuationMethod
  valuation_label: string
  result_label: string
  dedicated_history_required: boolean
  twr_available: boolean
  daily_twr_pct: number | null
  accumulated_twr_pct: number | null
  performance_as_of: string | null
  has_partial_prices: boolean | null
  return_is_estimated: boolean | null
  performance_status: string
  performance_reason: string | null
  performance_source: 'portfolio_class_snapshot' | null
}

export interface BenchmarkAvailability {
  available: boolean
  status: 'available' | 'awaiting_persisted_history'
}

export interface MonthlyBenchmarkPoint {
  period: string
  ibov_monthly_pct: number | null
  cdi_monthly_pct: number | null
  ipca_monthly_pct: number | null
}

export interface MonthlyBenchmarkResponse {
  source: 'persisted_benchmark_history'
  start_date: string | null
  end_date: string
  availability: Record<'IBOV' | 'CDI' | 'IPCA', BenchmarkAvailability>
  points: MonthlyBenchmarkPoint[]
}

export const rentabilidadeService = {
  getKpis: (portfolioId: number) =>
    api.get<RentabilidadeKpis>(`/portfolios/${portfolioId}/rentabilidade/kpis`).then(r => r.data),

  getAtivos: (portfolioId: number) =>
    api.get<RentabilidadeAtivo[]>(`/portfolios/${portfolioId}/rentabilidade/ativos`).then(r => r.data),

  getClasses: (portfolioId: number) =>
    api.get<RentabilidadeClasse[]>(`/portfolios/${portfolioId}/rentabilidade/classes`).then(r => r.data),

  getMonthlyBenchmarks: (portfolioId: number, months: number) =>
    api
      .get<MonthlyBenchmarkResponse>(`/portfolios/${portfolioId}/rentabilidade/benchmarks/monthly`, {
        params: { months },
      })
      .then(r => r.data),
}
