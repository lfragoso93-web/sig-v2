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

const QUERY_KEY = ['portfolios']

export function usePortfolios() {
  return useQuery<Portfolio[]>({
    queryKey: QUERY_KEY,
    queryFn: () => api.get('/portfolios').then((r) => r.data),
  })
}

export function useCreatePortfolio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      api.post<Portfolio>('/portfolios', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  })
}
