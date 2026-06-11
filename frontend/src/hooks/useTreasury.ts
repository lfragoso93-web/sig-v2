import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

// ── Tipos ───────────────────────────────────────────────────────────────────

export interface TreasuryInvestment {
  id: number
  portfolio_id: number
  brapi_name: string
  invested_value: number
  purchase_date: string
  maturity_date: string | null
  is_active: boolean
  created_at: string
  current_price: number | null
  valor_atual: number | null
  lucro_prejuizo: number | null
  rentabilidade_pct: number | null
}

export interface TreasuryCreatePayload {
  brapi_name: string
  invested_value: number
  purchase_date: string
  maturity_date?: string | null
  is_active?: boolean
}

export interface TreasuryUpdatePayload {
  brapi_name?: string
  invested_value?: number
  purchase_date?: string
  maturity_date?: string | null
  is_active?: boolean
}

// ── Query keys ──────────────────────────────────────────────────────────────

export const TREASURY_QUERY_KEY = (portfolioId: number) =>
  ['treasury', portfolioId] as const

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useTreasury(portfolioId: number | null, onlyActive = false) {
  return useQuery<TreasuryInvestment[]>({
    queryKey: [...(TREASURY_QUERY_KEY(portfolioId ?? 0)), onlyActive],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/treasury`, {
          params: { only_active: onlyActive },
        })
        .then(r => r.data),
    enabled: !!portfolioId,
    staleTime: 30_000,
  })
}

export function useCreateTreasury(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: TreasuryCreatePayload) =>
      api.post(`/portfolios/${portfolioId}/treasury`, payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TREASURY_QUERY_KEY(portfolioId) })
    },
  })
}

export function useUpdateTreasury(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TreasuryUpdatePayload }) =>
      api.patch(`/portfolios/${portfolioId}/treasury/${id}`, data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TREASURY_QUERY_KEY(portfolioId) })
    },
  })
}

export function useDeleteTreasury(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      api.delete(`/portfolios/${portfolioId}/treasury/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TREASURY_QUERY_KEY(portfolioId) })
    },
  })
}
