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

export function formatFriendlyTreasuryTitle(name: string, ticker?: string | null): string {
  let cleaned = (name || ticker || '')
    .replace(/\s+aposentadoria\s+extra\b/gi, '')
    .replace(/\brenda\+/gi, 'Renda+')
    .replace(/\beduca\+/gi, 'Educa+')
    .replace(/\s+/g, ' ')
    .trim()

  let rawYear: number | null = null
  const dmyMatch = cleaned.match(/\b\d{1,2}\/\d{1,2}\/(20\d{2})\b/)
  if (dmyMatch) {
    rawYear = parseInt(dmyMatch[1], 10)
    cleaned = cleaned.replace(/\b\d{1,2}\/\d{1,2}\/20\d{2}\b/, '').trim()
  } else {
    const isoMatch = cleaned.match(/\b(20\d{2})[-/]\d{2}[-/]\d{2}\b/)
    if (isoMatch) {
      rawYear = parseInt(isoMatch[1], 10)
      cleaned = cleaned.replace(/\b20\d{2}[-/]\d{2}[-/]\d{2}\b/, '').trim()
    } else {
      const yearMatch = cleaned.match(/\b(20\d{2})\b/)
      if (yearMatch) {
        rawYear = parseInt(yearMatch[1], 10)
        cleaned = cleaned.replace(/\b20\d{2}\b/, '').trim()
      }
    }
  }

  const tickerClean = (ticker || '').toLowerCase()
  let tickerCommercialYear: number | null = null
  if (tickerClean) {
    const tm = tickerClean.match(/20\d{2}/)
    if (tm) {
      tickerCommercialYear = parseInt(tm[0], 10)
    }
  }

  const norm = cleaned.toLowerCase()
  if (norm.includes('renda')) {
    let finalYear: number | null = null
    if (tickerCommercialYear && tickerCommercialYear >= 2030 && tickerCommercialYear <= 2065 && tickerCommercialYear % 5 === 0) {
      finalYear = tickerCommercialYear
    } else if (rawYear) {
      finalYear = rawYear >= 2049 ? rawYear - 19 : rawYear
    } else if (tickerCommercialYear) {
      finalYear = tickerCommercialYear >= 2049 ? tickerCommercialYear - 19 : tickerCommercialYear
    }
    return finalYear ? `Tesouro Renda+ ${finalYear}` : 'Tesouro Renda+'
  }

  if (norm.includes('educa')) {
    let finalYear: number | null = null
    if (tickerCommercialYear && tickerCommercialYear >= 2026 && tickerCommercialYear <= 2042) {
      finalYear = tickerCommercialYear
    } else if (rawYear) {
      if (rawYear >= 2030 && (rawYear > 2042 || (tickerCommercialYear && tickerCommercialYear === rawYear - 4))) {
        finalYear = rawYear - 4
      } else {
        finalYear = rawYear
      }
    } else if (tickerCommercialYear) {
      finalYear = tickerCommercialYear
    }
    return finalYear ? `Tesouro Educa+ ${finalYear}` : 'Tesouro Educa+'
  }

  const finalYear = rawYear || tickerCommercialYear
  cleaned = cleaned.replace(/\s+/g, ' ').trim()
  return finalYear ? `${cleaned} ${finalYear}` : cleaned
}

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
        const items = res.data.map(item => ({
          ...item,
          name: formatFriendlyTreasuryTitle(item.name, item.ticker),
        }))
        setItems(items)
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
