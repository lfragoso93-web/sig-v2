import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface Transaction {
  id:         number
  ticker:     string
  asset_type: string
  operation:  'buy' | 'sell'
  quantity:   number
  price:      number
  fees:       number
  date:       string
  notes?:     string
}

export interface CreateTransactionPayload {
  ticker:     string
  asset_type: string
  operation:  'buy' | 'sell'
  quantity:   number
  price:      number
  fees:       number
  date:       string
  notes?:     string
}

export function useTransactions(portfolioId?: number | null) {
  return useQuery<Transaction[]>({
    queryKey: ['transactions', portfolioId],
    queryFn:  () => api.get(`/portfolios/${portfolioId}/transactions`).then(r => r.data),
    enabled:  !!portfolioId,
    staleTime: 30_000,
  })
}

export function useCreateTransaction(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateTransactionPayload) =>
      api.post(`/portfolios/${portfolioId}/transactions`, payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions', portfolioId] })
      qc.invalidateQueries({ queryKey: ['positions',   portfolioId] })
      qc.invalidateQueries({ queryKey: ['summary',     portfolioId] })
      qc.invalidateQueries({ queryKey: ['performance', portfolioId] })
    },
  })
}

export function useDeleteTransaction(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      api.delete(`/portfolios/${portfolioId}/transactions/${id}`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions', portfolioId] })
      qc.invalidateQueries({ queryKey: ['positions',   portfolioId] })
      qc.invalidateQueries({ queryKey: ['summary',     portfolioId] })
      qc.invalidateQueries({ queryKey: ['performance', portfolioId] })
    },
  })
}
