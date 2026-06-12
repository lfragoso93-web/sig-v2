import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

// ── Tipos ─────────────────────────────────────────────────────────────────────

export interface TreasuryUpdatePayload {
  brapi_name?: string
  invested_value?: number
  purchase_date?: string
  maturity_date?: string | null
  is_active?: boolean
}

// ── Invalidação centralizada ──────────────────────────────────────────────────

const TREASURY_KEYS = (portfolioId: number) => [
  ['treasury', portfolioId],
  ['positions', portfolioId],
  ['portfolio-summary', portfolioId],
  ['asset-distribution', portfolioId],
]

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useTreasuryMutations(portfolioId: number) {
  const qc = useQueryClient()

  const invalidate = () =>
    Promise.all(TREASURY_KEYS(portfolioId).map(k => qc.invalidateQueries({ queryKey: k })))

  const update = useMutation({
    mutationFn: ({ id, data }: { id: number; data: TreasuryUpdatePayload }) =>
      api.patch(`/portfolios/${portfolioId}/treasury/${id}`, data).then(r => r.data),
    onSuccess: invalidate,
  })

  const remove = useMutation({
    mutationFn: (id: number) =>
      api.delete(`/portfolios/${portfolioId}/treasury/${id}`).then(r => r.data),
    onSuccess: invalidate,
  })

  return { update, remove }
}
