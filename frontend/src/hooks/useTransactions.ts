import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface Transaction {
  id: number
  portfolio_id: number
  ticker: string
  type: 'buy' | 'sell'
  quantity: number
  price: number
  date: string
  currency: string
  created_at: string
}

const KEY = (pid: number) => ['transactions', pid]

export function useTransactions(portfolioId: number | null) {
  return useQuery<Transaction[]>({
    queryKey: KEY(portfolioId!),
    queryFn: () =>
      api.get('/transactions', { params: { portfolio_id: portfolioId } }).then((r) => r.data),
    enabled: !!portfolioId,
  })
}

export function useCreateTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<Transaction, 'id' | 'created_at'>) =>
      api.post<Transaction>('/transactions', data).then((r) => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: KEY(v.portfolio_id) }),
  })
}
