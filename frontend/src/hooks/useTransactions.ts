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
  currency: string
  notes?: string
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

const TX_KEY  = (pid: number | null) => ['transactions', pid]

// Todas as query keys que dependem de posições/resumo da carteira
function invalidatePortfolioKeys(qc: ReturnType<typeof useQueryClient>, portfolioId: number) {
  qc.invalidateQueries({ queryKey: ['transactions',       portfolioId] })
  qc.invalidateQueries({ queryKey: ['portfolio-summary',  portfolioId] })
  qc.invalidateQueries({ queryKey: ['positions',          portfolioId] })
  qc.invalidateQueries({ queryKey: ['asset-distribution', portfolioId] })
  qc.invalidateQueries({ queryKey: ['patrimonio-history', portfolioId] })
  // resumo usado no ResumePage (endpoint /portfolios/{id}/summary)
  qc.invalidateQueries({ queryKey: ['summary', portfolioId] })
}

export function useTransactions(portfolioId: number | null) {
  return useQuery<Transaction[]>({
    queryKey: TX_KEY(portfolioId),
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
    onSuccess: (_d, v) => invalidatePortfolioKeys(qc, v.portfolioId),
  })
}

export function useDeleteTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ portfolioId, id }: { portfolioId: number; id: number }) =>
      api
        .delete(`/portfolios/${portfolioId}/transactions/${id}`)
        .then((r) => r.data),
    onSuccess: (_d, v) => invalidatePortfolioKeys(qc, v.portfolioId),
  })
}
