import api from './api'

export interface AssetPerf {
  ticker: string
  asset_type: string
  currency: 'BRL' | 'USD'
  quantity: number
  avg_price: number
  avg_price_brl: number
  current_price: number
  current_price_brl: number
  cost_basis: number
  current_value: number
  unrealized_pnl: number
  realized_pnl: number
  total_pnl: number
  return_pct: number
  fx_rate_avg: number | null
  fx_rate_current: number | null
  fx_variation_pct: number | null
  allocation_pct: number
}

export interface ByTypePerf {
  asset_type: string
  cost: number
  current: number
  pnl: number
  return_pct: number
  allocation_pct: number
  count: number
}

export interface HistoryPoint {
  period: string        // 'YYYY-MM'
  inflow: number
  outflow: number
  net_invested: number
}

export interface PortfolioPerf {
  portfolio_id: number
  portfolio_name: string
  total_cost: number
  total_current: number
  total_unrealized: number
  total_realized: number
  total_pnl: number
  return_pct: number
  assets: AssetPerf[]
  by_type: ByTypePerf[]
  history: HistoryPoint[]
}

export const performanceService = {
  getPortfolio: (portfolioId: number): Promise<PortfolioPerf> =>
    api.get(`/api/v1/portfolios/${portfolioId}/performance`).then(r => r.data),

  getAsset: (portfolioId: number, ticker: string): Promise<AssetPerf> =>
    api.get(`/api/v1/portfolios/${portfolioId}/performance/${ticker}`).then(r => r.data),
}
