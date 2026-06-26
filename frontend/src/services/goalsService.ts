import api from '@/lib/api'

export interface Goal {
  id: number
  portfolio_id: number
  name: string
  target_value: number
  current_value: number
  target_date: string | null
  description: string | null
  created_at: string
  progress_pct: number
  is_completed: boolean
}

export interface GoalCreate {
  name: string
  target_value: number
  current_value?: number
  target_date?: string | null
  description?: string | null
}

export interface GoalUpdate {
  name?: string
  target_value?: number
  current_value?: number
  target_date?: string | null
  description?: string | null
}

export async function fetchGoals(portfolioId: number): Promise<Goal[]> {
  const { data } = await api.get<Goal[]>(`/portfolios/${portfolioId}/goals`)
  return data
}

export async function createGoal(portfolioId: number, payload: GoalCreate): Promise<Goal> {
  const { data } = await api.post<Goal>(`/portfolios/${portfolioId}/goals`, payload)
  return data
}

export async function updateGoal(portfolioId: number, goalId: number, payload: GoalUpdate): Promise<Goal> {
  const { data } = await api.put<Goal>(`/portfolios/${portfolioId}/goals/${goalId}`, payload)
  return data
}

export async function deleteGoal(portfolioId: number, goalId: number): Promise<void> {
  await api.delete(`/portfolios/${portfolioId}/goals/${goalId}`)
}
