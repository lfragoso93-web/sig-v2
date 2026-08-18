import { useState, useEffect, useCallback } from 'react'
import api from '../services/api'
import { useAppStore } from '../store/appStore'
import { getApiErrorMessage } from '../utils/apiError'

export interface TreasuryItem {
  id: number
  portfolio_id: number
  brapi_name: string
  invested_value: number
  purchase_date: string
  maturity_date: string | null
  is_active: boolean
  current_price: number | null
  valor_atual: number | null
  lucro_prejuizo: number | null
  rentabilidade_pct: number | null
  created_at: string | null
}

export interface TreasuryCreate {
  brapi_name: string
  invested_value: number
  purchase_date: string
  maturity_date?: string | null
  is_active?: boolean
}

export interface TreasuryUpdate {
  brapi_name?: string
  invested_value?: number
  purchase_date?: string
  maturity_date?: string | null
  is_active?: boolean
}

export function useTreasury() {
  const portfolioId = useAppStore((s) => s.selectedPortfolioId)
  const [items, setItems] = useState<TreasuryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    if (!portfolioId) { setItems([]); return }
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get<TreasuryItem[]>(
        `/portfolios/${portfolioId}/treasury`
      )
      setItems(data)
    } catch (error: unknown) {
      setError(getApiErrorMessage(error, 'Erro ao carregar Tesouro Direto'))
    } finally {
      setLoading(false)
    }
  }, [portfolioId])

  useEffect(() => { fetchAll() }, [fetchAll])

  const create = useCallback(async (payload: TreasuryCreate): Promise<TreasuryItem> => {
    const { data } = await api.post<TreasuryItem>(
      `/portfolios/${portfolioId}/treasury`,
      payload
    )
    await fetchAll()
    return data
  }, [portfolioId, fetchAll])

  const update = useCallback(async (id: number, payload: TreasuryUpdate): Promise<TreasuryItem> => {
    const { data } = await api.patch<TreasuryItem>(
      `/portfolios/${portfolioId}/treasury/${id}`,
      payload
    )
    setItems((prev) => prev.map((item) => item.id === id ? data : item))
    return data
  }, [portfolioId])

  const remove = useCallback(async (id: number): Promise<void> => {
    // optimistic update
    setItems((prev) => prev.filter((item) => item.id !== id))
    try {
      await api.delete(`/portfolios/${portfolioId}/treasury/${id}`)
    } catch (e) {
      await fetchAll() // reverte se falhar
      throw e
    }
  }, [portfolioId, fetchAll])

  return { items, loading, error, refetch: fetchAll, create, update, remove }
}
