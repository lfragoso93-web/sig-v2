import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export interface PortfolioSummary {
  portfolio_id: number
  total_invested: number
  current_value: number
  total_gain: number
  total_gain_pct: number
  daily_change: number
  daily_change_pct: number
  positions: Position[]
}

export interface Position {
  asset_id: number
  ticker: string
  name: string
  asset_type: string
  quantity: number
  avg_price: number
  current_price: number
  invested: number
  current_value: number
  gain: number
  gain_pct: number
}

export interface EquityPoint {
  date: string
  value: number
}

export function usePortfolioSummary(portfolioId: number | null) {
  return useQuery<PortfolioSummary>({
    queryKey: ['performance', 'summary', portfolioId],
    queryFn: () =>
      api.get(`/performance/${portfolioId}/summary`).then((r) => r.data),
    enabled: !!portfolioId,
  })
}

export function useEquityHistory(
  portfolioId: number | null,
  period: '1m' | '3m' | '6m' | '1y' | 'all' = '1y',
) {
  return useQuery<EquityPoint[]>({
    queryKey: ['performance', 'equity', portfolioId, period],
    queryFn: () =>
      api
        .get(`/performance/${portfolioId}/equity`, { params: { period } })
        .then((r) => r.data),
    enabled: !!portfolioId,
  })
}
