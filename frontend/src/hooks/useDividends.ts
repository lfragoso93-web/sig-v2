import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export interface Dividend {
  id: number
  portfolio_id: number
  ticker: string
  type: string
  amount: number
  payment_date: string
  date: string
}

interface DividendRead {
  id: number
  portfolio_id: number
  ticker: string
  ex_date: string
  payment_date: string | null
  dividend_type: string | null
  total_received: number | null
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
    queryFn: async () => {
      const { data } = await api.get<DividendRead[]>(`/portfolios/${portfolioId}/dividends`)
      return data.map(dividend => ({
        id: dividend.id,
        portfolio_id: dividend.portfolio_id,
        ticker: dividend.ticker,
        type: dividend.dividend_type ?? 'Provento',
        amount: dividend.total_received ?? 0,
        payment_date: dividend.payment_date ?? dividend.ex_date,
        date: dividend.ex_date,
      }))
    },
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
