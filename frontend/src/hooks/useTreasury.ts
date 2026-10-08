import { useState, useEffect, useCallback } from 'react'
import api from '../services/api'
import { useAppStore } from '../store/appStore'
import { getApiErrorMessage } from '../utils/apiError'

export interface TreasuryItem {
  id: number
  portfolio_id: number
  brapi_name: string
  commercial_name?: string | null
  brapi_symbol?: string | null
  ticker?: string | null
  purchase_price?: number | null
  quantity?: number | null
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

  return { items, loading, error, refetch: fetchAll }
}
