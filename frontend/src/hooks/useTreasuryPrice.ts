import { useEffect, useState } from 'react'
import api from '@/services/api'

interface TreasuryPriceResponse {
  slug:       string
  price:      number | null
  price_date: string
  source:     string
}

/**
 * Busca o PU de um titulo do Tesouro Direto para uma data especifica.
 * Chama GET /assets/tesouro/price?slug={slug}&date={date}.
 * So dispara quando slug e date estao preenchidos.
 * Debounce de 400ms.
 */
export function useTreasuryPrice(slug: string, date: string, enabled = true) {
  const [price,   setPrice]   = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    if (!enabled || !slug || !date) {
      setPrice(null)
      setError(null)
      return
    }

    setLoading(true)
    setError(null)
    const timer = setTimeout(async () => {
      try {
        const res = await api.get<TreasuryPriceResponse>(
          `/assets/tesouro/price?slug=${encodeURIComponent(slug)}&date=${date}`
        )
        setPrice(res.data.price)
      } catch {
        setPrice(null)
        setError('Não foi possível consultar o preço do título. Informe-o manualmente.')
      } finally {
        setLoading(false)
      }
    }, 400)

    return () => clearTimeout(timer)
  }, [slug, date, enabled])

  return { price, loading, error }
}
