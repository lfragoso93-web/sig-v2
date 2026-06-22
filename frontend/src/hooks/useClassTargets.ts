/**
 * Hook para buscar e atualizar metas de alocação por classe de ativo.
 *
 * GET  /portfolios/{id}/class-targets          -> lista [{asset_type, target_pct}]
 * PUT  /portfolios/{id}/class-targets/{type}   -> upsert de uma meta
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface ClassTarget {
  asset_type: string
  target_pct: number
}

export function useClassTargets(portfolioId: number | null) {
  return useQuery<ClassTarget[]>({
    queryKey: ['class-targets', portfolioId],
    queryFn: () =>
      api.get(`/portfolios/${portfolioId}/class-targets`).then(r => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
  })
}

export function useSetClassTarget(portfolioId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ asset_type, target_pct }: ClassTarget) =>
      api
        .put(`/portfolios/${portfolioId}/class-targets/${asset_type}`, { target_pct })
        .then(r => r.data),
    onSuccess: () => {
      // Invalida tanto as metas quanto as posições (que agora trazem target_pct)
      qc.invalidateQueries({ queryKey: ['class-targets', portfolioId] })
      qc.invalidateQueries({ queryKey: ['positions', portfolioId] })
    },
  })
}
