import api from './api'

export interface PortfolioSummary {
  total_patrimonio: number
  total_investido: number
  lucro_total: number
  ganho_capital: number
  dividendos_recebidos_12m: number
  total_proventos: number
  variacao_valor: number
  variacao_percentual: number
  rentabilidade_total: number
}

export interface PatrimonioHistorico {
  month: string
  valor_aplicado: number
  ganho_capital: number
}

export interface AssetTypeDistribution {
  type: string
  label: string
  value: number
  percentage: number
  color: string
}

export interface PositionItem {
  id: number
  ticker: string
  name: string
  asset_type: string
  logo_url?: string
  quantity: number
  average_price: number
  current_price: number
  current_value: number
  variation_value: number
  variation_percent: number
  rentability_percent: number
  portfolio_percent: number
  ideal_percent?: number
  should_buy?: boolean
  score?: number
}

export interface PositionGroup {
  asset_type: string
  label: string
  count: number
  total_value: number
  variation_percent: number
  rentability_percent: number
  portfolio_percent: number
  ideal_percent?: number
  positions: PositionItem[]
}

// Nota: baseURL do axios já inclui /api/v1 — não repetir o prefixo aqui
export const portfolioService = {
  getSummary: (portfolioId: number) =>
    api.get<PortfolioSummary>(`/portfolios/${portfolioId}/summary`).then(r => r.data),

  getPatrimonioHistory: (portfolioId: number, months = 12) =>
    api.get<PatrimonioHistorico[]>(`/portfolios/${portfolioId}/patrimonio-history`, {
      params: { months },
    }).then(r => r.data),

  getAssetDistribution: (portfolioId: number) =>
    api.get<AssetTypeDistribution[]>(`/portfolios/${portfolioId}/asset-distribution`).then(r => r.data),

  getPositions: (portfolioId: number) =>
    api.get<PositionGroup[]>(`/portfolios/${portfolioId}/positions`).then(r => r.data),

  listPortfolios: () =>
    api.get<{ id: number; name: string }[]>('/portfolios').then(r => r.data),
}
