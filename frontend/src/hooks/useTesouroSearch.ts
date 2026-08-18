import { useEffect, useState } from 'react'
import api from '@/services/api'

export interface TreasuryItem {
  name:          string
  ticker:        string
  slug:          string | null   // adicionado: slug unico do titulo (ex: tesouro-selic-01032031)
  indexer:       string
  rate:          number | null
  maturity_date: string | null
  price:         number | null
}

/**
 * Hook com debounce de 500ms para buscar titulos do Tesouro Direto.
 * Dispara a partir de 2 chars (era 3, reduzido para melhor UX).
 */
export function useTesouroSearch(q: string, enabled = true) {
  const [items,   setItems]   = useState<TreasuryItem[]>([])
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
    const timer = setTimeout(async () => {
      try {
        const res = await api.get<TreasuryItem[]>(
          `/assets/tesouro/search?q=${encodeURIComponent(q.trim())}`
        )
        setItems(res.data)
      } catch {
        setItems([])
        setError('Não foi possível consultar os títulos. Tente novamente.')
      } finally {
        setLoading(false)
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [q, enabled])

  return { items, loading, error }
}
