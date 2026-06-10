import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface Portfolio {
  id: number
  user_id: number
  name: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export const PORTFOLIOS_QUERY_KEY = ['portfolios'] as const

export function usePortfolios() {
  return useQuery<Portfolio[]>({
    queryKey: PORTFOLIOS_QUERY_KEY,
    queryFn: () => api.get('/portfolios').then((r) => r.data),
    // Evita refetch a cada re-render da Sidebar — lista de carteiras muda raramente
    staleTime: 30_000,
  })
}

export function useCreatePortfolio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      api.post<Portfolio>('/portfolios', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: PORTFOLIOS_QUERY_KEY }),
  })
}
