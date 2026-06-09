import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface Dividend {
  id: number
  portfolio_id: number
  ticker: string
  type: string
  amount: number
  date: string
  created_at: string
}

const KEY = (pid: number) => ['dividends', pid]

export function useDividends(portfolioId: number | null) {
  return useQuery<Dividend[]>({
    queryKey: KEY(portfolioId!),
    queryFn: () =>
      api.get('/dividends', { params: { portfolio_id: portfolioId } }).then((r) => r.data),
    enabled: !!portfolioId,
  })
}

export function useCreateDividend() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<Dividend, 'id' | 'created_at'>) =>
      api.post<Dividend>('/dividends', data).then((r) => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: KEY(v.portfolio_id) }),
  })
}
