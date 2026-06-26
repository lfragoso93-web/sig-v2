import { useState, useCallback } from 'react'
import {
  fetchGoals,
  createGoal,
  updateGoal,
  deleteGoal,
  Goal,
  GoalCreate,
  GoalUpdate,
} from '@/services/goalsService'

interface UseGoalsReturn {
  goals: Goal[]
  loading: boolean
  error: string | null
  loadGoals: (portfolioId: number) => Promise<void>
  addGoal: (portfolioId: number, payload: GoalCreate) => Promise<void>
  editGoal: (portfolioId: number, goalId: number, payload: GoalUpdate) => Promise<void>
  removeGoal: (portfolioId: number, goalId: number) => Promise<void>
}

export function useGoals(): UseGoalsReturn {
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadGoals = useCallback(async (portfolioId: number) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchGoals(portfolioId)
      setGoals(data)
    } catch {
      setError('Erro ao carregar metas.')
    } finally {
      setLoading(false)
    }
  }, [])

  const addGoal = useCallback(async (portfolioId: number, payload: GoalCreate) => {
    const newGoal = await createGoal(portfolioId, payload)
    setGoals((prev) => [newGoal, ...prev])
  }, [])

  const editGoal = useCallback(async (portfolioId: number, goalId: number, payload: GoalUpdate) => {
    const updated = await updateGoal(portfolioId, goalId, payload)
    setGoals((prev) => prev.map((g) => (g.id === goalId ? updated : g)))
  }, [])

  const removeGoal = useCallback(async (portfolioId: number, goalId: number) => {
    await deleteGoal(portfolioId, goalId)
    setGoals((prev) => prev.filter((g) => g.id !== goalId))
  }, [])

  return { goals, loading, error, loadGoals, addGoal, editGoal, removeGoal }
}
