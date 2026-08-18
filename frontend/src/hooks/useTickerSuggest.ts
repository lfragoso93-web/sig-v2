import { useEffect, useState } from 'react'
import api from '@/services/api'

export interface TickerSuggestion {
  ticker: string
  name:   string
  type:   string | null
}

/**
 * Hook com debounce de 500ms para buscar sugestoes de tickers da B3.
 * Chama GET /assets/suggest?q={q}&limit=10&asset_type={assetType}.
 * assetType: 'stock' | 'fund' | 'etf' | 'bdr' | undefined (todos)
 * So dispara quando enabled=true e q tiver >= 2 chars.
 */
export function useTickerSuggest(
  q:         string,
  enabled  = true,
  assetType?: string,
) {
  const [items,   setItems]   = useState<TickerSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    if (!enabled || q.trim().length < 2) {
      setItems([])
      setError(null)
      return
    }

    setLoading(true)
    setError(null)
    const params = new URLSearchParams({
      q:     q.trim(),
      limit: '10',
      ...(assetType ? { asset_type: assetType } : {}),
    })

    const timer = setTimeout(async () => {
      try {
        const res = await api.get<TickerSuggestion[]>(`/assets/suggest?${params}`)
        setItems(res.data)
      } catch {
        setItems([])
        setError('Não foi possível consultar o catálogo de ativos. Tente novamente.')
      } finally {
        setLoading(false)
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [q, enabled, assetType])

  return { items, loading, error }
}
