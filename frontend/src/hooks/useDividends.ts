import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface Dividend {
  id:           number
  ticker:       string
  asset_type:   string
  type:         'dividendo' | 'jcp' | 'rendimento' | 'amortizacao' | 'outro'
  amount:       number
  quantity:     number
  payment_date: string
  ex_date?:     string | null
}

export interface DividendSummary {
  total_received:  number
  total_projected: number
  monthly: { month: string; amount: number }[]
}

export interface CreateDividendPayload {
  ticker:       string
  asset_type:   string
  type:         Dividend['type']
  amount:       number
  quantity:     number
  payment_date: string
  ex_date?:     string | null
}

export function useDividends(portfolioId?: number | null) {
  return useQuery<Dividend[]>({
    queryKey: ['dividends', portfolioId],
    queryFn:  () => api.get(`/portfolios/${portfolioId}/dividends`).then(r => r.data),
    enabled:  !!portfolioId,
    staleTime: 60_000,
  })
}

export function useDividendSummary(portfolioId?: number | null) {
  return useQuery<DividendSummary>({
    queryKey: ['dividends-summary', portfolioId],
    queryFn:  () => api.get(`/portfolios/${portfolioId}/dividends/summary`).then(r => r.data),
    enabled:  !!portfolioId,
    staleTime: 60_000,
  })
}

export function useCreateDividend(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateDividendPayload) =>
      api.post(`/portfolios/${portfolioId}/dividends`, payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dividends',         portfolioId] })
      qc.invalidateQueries({ queryKey: ['dividends-summary', portfolioId] })
      qc.invalidateQueries({ queryKey: ['summary',           portfolioId] })
    },
  })
}
