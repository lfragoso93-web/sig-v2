import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface Transaction {
  id: number
  portfolio_id: number
  ticker: string
  asset_type: string
  /** 'buy' | 'sell' */
  operation: 'buy' | 'sell'
  quantity: number
  price: number
  fees: number
  date: string
  currency: string
  notes?: string
  created_at: string
}

export interface TransactionCreate {
  ticker: string
  asset_type: string
  operation: 'buy' | 'sell'
  quantity: number
  price: number
  fees?: number
  date: string
  currency?: string
  notes?: string
}

const KEY = (pid: number | null) => ['transactions', pid]

export function useTransactions(portfolioId: number | null) {
  return useQuery<Transaction[]>({
    queryKey: KEY(portfolioId),
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/transactions`)
        .then((r) => r.data),
    enabled: !!portfolioId,
  })
}

export function useCreateTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ portfolioId, data }: { portfolioId: number; data: TransactionCreate }) =>
      api
        .post<Transaction>(`/portfolios/${portfolioId}/transactions`, data)
        .then((r) => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: KEY(v.portfolioId) }),
  })
}

export function useDeleteTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ portfolioId, id }: { portfolioId: number; id: number }) =>
      api
        .delete(`/portfolios/${portfolioId}/transactions/${id}`)
        .then((r) => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: KEY(v.portfolioId) }),
  })
}
