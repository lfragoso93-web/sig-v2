import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface Transaction {
  id: number
  portfolio_id: number
  ticker: string
  asset_type: string
  operation: 'buy' | 'sell'
  quantity: number
  price: number
  fees: number
  date: string
  notes: string | null
}

export interface CreateTransactionPayload {
  ticker: string
  asset_type: string
  operation: 'buy' | 'sell'
  quantity: number
  price: number
  fees?: number
  date: string
  notes?: string
}

export function useTransactions(portfolioId: number | null) {
  return useQuery<Transaction[]>({
    queryKey: ['transactions', portfolioId],
    queryFn: () =>
      api.get(`/portfolios/${portfolioId}/transactions`).then((r) => r.data),
    enabled: !!portfolioId,
  })
}

export function useCreateTransaction(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateTransactionPayload) =>
      api
        .post(`/portfolios/${portfolioId}/transactions`, data)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions', portfolioId] })
      qc.invalidateQueries({ queryKey: ['performance', 'summary', portfolioId] })
    },
  })
}

export function useDeleteTransaction(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (transactionId: number) =>
      api.delete(`/transactions/${transactionId}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions', portfolioId] })
      qc.invalidateQueries({ queryKey: ['performance', 'summary', portfolioId] })
    },
  })
}
