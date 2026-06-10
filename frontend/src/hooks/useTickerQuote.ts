import { useEffect, useState } from 'react'
import api from '@/services/api'

export interface TickerQuote {
  ticker:      string
  name:        string | null
  price:       number | null
  currency:    string
  asset_type:  string | null
  source:      string
  price_date:  string | null
}

/**
 * Hook com debounce de 600 ms.
 * Consulta /assets/quote/{ticker}?date=YYYY-MM-DD quando a data nao for hoje.
 */
export function useTickerQuote(ticker: string, enabled = true, date?: string) {
  const [quote,   setQuote]   = useState<TickerQuote | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    const t = ticker.trim().toUpperCase()
    if (!enabled || t.length < 2) {
      setQuote(null)
      setError(null)
      return
    }

    setLoading(true)
    setError(null)

    const timer = setTimeout(async () => {
      try {
        const today   = new Date().toISOString().split('T')[0]
        const useDate = date && date !== today ? date : undefined
        const params  = useDate ? `?date=${useDate}` : ''
        const res     = await api.get<TickerQuote>(`/assets/quote/${t}${params}`)
        setQuote(res.data)
      } catch (e: any) {
        setQuote(null)
        const status = e?.response?.status
        if (status === 404) {
          setError('Ticker nao encontrado na BRAPI.')
        } else {
          setError(null)
        }
      } finally {
        setLoading(false)
      }
    }, 600)

    return () => clearTimeout(timer)
  }, [ticker, enabled, date])

  return { quote, loading, error }
}
