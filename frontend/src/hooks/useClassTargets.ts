/**
 * useClassTargets
 * Busca metas de alocacao por classe para um portfolio.
 * Retorna lista combinada: atual vs. alvo (via /portfolios/{id}/targets-with-current).
 *
 * Sprint 5E — Issue #79
 */
import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export interface ClassTargetRow {
  asset_type: string
  label: string
  target_pct: number
  current_pct: number
  delta_pct: number
  color: string
}

export function useClassTargets(portfolioId: number | null) {
  return useQuery<ClassTargetRow[]>({
    queryKey: ['class-targets', portfolioId],
    queryFn: async () => {
      if (!portfolioId) return []
      const res = await api.get<ClassTargetRow[]>(
        `/portfolios/${portfolioId}/targets-with-current`
      )
      return res.data
    },
    enabled: !!portfolioId,
    staleTime: 2 * 60 * 1000,
  })
}
