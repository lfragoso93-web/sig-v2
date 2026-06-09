import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface Provento {
  id: number
  portfolio_id: number
  ticker: string
  type: string
  amount: number
  date: string
  created_at: string
}

const KEY = (pid: number) => ['proventos', pid]

export function useProventos(portfolioId: number | null) {
  return useQuery<Provento[]>({
    queryKey: KEY(portfolioId!),
    queryFn: () =>
      api.get('/proventos', { params: { portfolio_id: portfolioId } }).then((r) => r.data),
    enabled: !!portfolioId,
  })
}

export function useCreateProvento() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<Provento, 'id' | 'created_at'>) =>
      api.post<Provento>('/proventos', data).then((r) => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: KEY(v.portfolio_id) }),
  })
}
