import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export type GoalType = 'PATRIMONIO' | 'PROVENTOS' | 'RENTABILIDADE' | 'LIVRE'

export interface Goal {
  id:                   number
  portfolio_id:         number
  goal_type:            GoalType
  name:                 string
  description?:         string
  target_value:         number
  current_value:        number
  base_value:           number
  monthly_contribution: number | null
  target_date:          string | null
  created_at:           string
  // calculados pelo backend
  progress_pct:         number
  is_completed:         boolean
  months_to_goal:       number | null
  projected_date:       string | null
}

export interface GoalCreate {
  portfolio_id:         number
  goal_type:            GoalType
  name:                 string
  target_value:         number
  current_value?:       number     // obrigatório somente para LIVRE
  monthly_contribution?: number
  target_date?:         string | null
  description?:         string
}

export type GoalUpdate = Partial<Omit<GoalCreate, 'portfolio_id' | 'goal_type'>>

const GOALS_KEY = (pid: number | null) => ['goals', pid]

export function useGoals(portfolioId: number | null) {
  return useQuery<Goal[]>({
    queryKey: GOALS_KEY(portfolioId),
    queryFn: () =>
      api.get<Goal[]>(`/portfolios/${portfolioId}/goals`).then(r => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
  })
}

export function useCreateGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GoalCreate) =>
      api.post<Goal>(`/portfolios/${data.portfolio_id}/goals`, data).then(r => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: GOALS_KEY(v.portfolio_id) }),
  })
}

export function useUpdateGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ portfolioId, id, data }: { portfolioId: number; id: number; data: GoalUpdate }) =>
      api.patch<Goal>(`/portfolios/${portfolioId}/goals/${id}`, data).then(r => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: GOALS_KEY(v.portfolioId) }),
  })
}

export function useDeleteGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ portfolioId, id }: { portfolioId: number; id: number }) =>
      api.delete(`/portfolios/${portfolioId}/goals/${id}`).then(r => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: GOALS_KEY(v.portfolioId) }),
  })
}
