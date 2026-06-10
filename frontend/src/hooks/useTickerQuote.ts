import { useEffect, useState } from 'react'
import api from '@/services/api'

export interface TickerQuote {
  ticker:     string
  name:       string | null
  price:      number | null
  currency:   string
  asset_type: string | null
  source:     string
}

/**
 * Hook com debounce de 600 ms.
 * Quando o ticker tiver >= 2 caracteres, consulta /assets/quote/{ticker}.
 * Retorna { quote, loading, error }.
 */
export function useTickerQuote(ticker: string, enabled = true) {
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
        const res = await api.get<TickerQuote>(`/assets/quote/${t}`)
        setQuote(res.data)
      } catch (e: any) {
        setQuote(null)
        const status = e?.response?.status
        if (status === 404) {
          setError('Ticker não encontrado na BRAPI.')
        } else {
          setError(null) // erro de rede — não bloqueia o usuário
        }
      } finally {
        setLoading(false)
      }
    }, 600)

    return () => clearTimeout(timer)
  }, [ticker, enabled])

  return { quote, loading, error }
}
