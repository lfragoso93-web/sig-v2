import { useEffect, useState } from 'react'
import api from '@/services/api'

export interface TreasuryItem {
  name:          string
  ticker:        string
  indexer:       string
  rate:          number | null
  maturity_date: string | null
  price:         number | null
}

/**
 * Hook com debounce de 700 ms para buscar titulos do Tesouro Direto via BRAPI.
 * So dispara quando enabled=true e q tiver >= 3 chars.
 */
export function useTesouroSearch(q: string, enabled = true) {
  const [items,   setItems]   = useState<TreasuryItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!enabled || q.trim().length < 3) {
      setItems([])
      return
    }

    setLoading(true)
    const timer = setTimeout(async () => {
      try {
        const res = await api.get<TreasuryItem[]>(`/assets/tesouro/search?q=${encodeURIComponent(q.trim())}`)
        setItems(res.data)
      } catch {
        setItems([])
      } finally {
        setLoading(false)
      }
    }, 700)

    return () => clearTimeout(timer)
  }, [q, enabled])

  return { items, loading }
}
