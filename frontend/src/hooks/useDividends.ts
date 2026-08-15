import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export interface Dividend {
  id: number
  portfolio_id: number
  ticker: string
  asset_type: string
  type: string
  amount: number
  quantity: number
  payment_date: string
  date: string
  created_at: string
}

export interface DividendMonthly {
  month: string   // 'YYYY-MM'
  amount: number
}

export interface DividendSummary {
  total_received: number
  total_projected: number
  monthly: DividendMonthly[]
}

const KEY = (pid: number | null) => ['dividends', pid]

export function useDividends(portfolioId: number | null) {
  return useQuery<Dividend[]>({
    queryKey: KEY(portfolioId),
    queryFn: () =>
      api.get('/dividends', { params: { portfolio_id: portfolioId } }).then((r) => r.data),
    enabled: !!portfolioId,
  })
}

/**
 * Resumo de dividendos: total recebido, projeção e breakdown mensal.
 */
export function useDividendSummary(portfolioId: number | null) {
  return useQuery<DividendSummary>({
    queryKey: ['dividends-summary', portfolioId],
    queryFn: () =>
      api.get(`/dividends/${portfolioId}/summary`).then((r) => r.data),
    enabled: !!portfolioId,
    retry: false,
  })
}
