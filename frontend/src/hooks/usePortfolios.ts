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

export function useUpdatePortfolio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: number; name: string; description?: string }) =>
      api.put<Portfolio>(`/portfolios/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: PORTFOLIOS_QUERY_KEY }),
  })
}

export function useDeletePortfolio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete(`/portfolios/${id}`),
    onMutate: async (id: number) => {
      // Cancela refetches pendentes para evitar sobrescrever o optimistic update
      await qc.cancelQueries({ queryKey: PORTFOLIOS_QUERY_KEY })
      const previous = qc.getQueryData<Portfolio[]>(PORTFOLIOS_QUERY_KEY)
      // Remove otimisticamente da lista
      qc.setQueryData<Portfolio[]>(
        PORTFOLIOS_QUERY_KEY,
        (old) => (old ?? []).filter((p) => p.id !== id),
      )
      return { previous }
    },
    onError: (_err, _id, context) => {
      // Reverte em caso de erro
      if (context?.previous) {
        qc.setQueryData(PORTFOLIOS_QUERY_KEY, context.previous)
      }
    },
    onSettled: () => {
      // Garante sincronia final com o servidor
      qc.invalidateQueries({ queryKey: PORTFOLIOS_QUERY_KEY })
    },
  })
}
