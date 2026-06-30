/**
 * useClassTargets
 * Busca e mutacoes de metas de alocacao por classe para um portfolio.
 *
 * Exports:
 *   useClassTargets        — leitura (query)
 *   useUpsertClassTarget   — criacao/atualizacao (mutation)
 *   useDeleteClassTarget   — remocao (mutation)
 *
 * Sprint 5E — Issue #79
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface ClassTargetRow {
  asset_type: string
  label: string
  target_pct: number
  current_pct: number
  delta_pct: number
  color: string
}

export interface ClassTargetUpsertPayload {
  asset_type: string
  target_pct: number
}

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Mutation: upsert (cria ou atualiza meta por asset_type)
// ---------------------------------------------------------------------------
export function useUpsertClassTarget(portfolioId: number | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: ClassTargetUpsertPayload) => {
      if (!portfolioId) throw new Error('portfolioId requerido')
      const res = await api.put(
        `/portfolios/${portfolioId}/targets`,
        payload
      )
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['class-targets', portfolioId] })
    },
  })
}

// ---------------------------------------------------------------------------
// Mutation: delete (remove meta de um asset_type)
// ---------------------------------------------------------------------------
export function useDeleteClassTarget(portfolioId: number | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (assetType: string) => {
      if (!portfolioId) throw new Error('portfolioId requerido')
      const res = await api.delete(
        `/portfolios/${portfolioId}/targets/${assetType}`
      )
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['class-targets', portfolioId] })
    },
  })
}
