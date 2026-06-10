import { useEffect, useState } from 'react'
import api from '@/services/api'

export interface TickerSuggestion {
  ticker: string
  name:   string
  type:   string | null
}

/**
 * Hook com debounce de 500 ms para buscar sugestoes de tickers da B3.
 * Chama GET /assets/suggest?q={q}&limit=10.
 * So dispara quando enabled=true e q tiver >= 2 chars.
 */
export function useTickerSuggest(q: string, enabled = true) {
  const [items,   setItems]   = useState<TickerSuggestion[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!enabled || q.trim().length < 2) {
      setItems([])
      return
    }

    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const res = await api.get<TickerSuggestion[]>(
          `/assets/suggest?q=${encodeURIComponent(q.trim())}&limit=10`
        )
        setItems(res.data)
      } catch {
        setItems([])
      } finally {
        setLoading(false)
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [q, enabled])

  return { items, loading }
}
