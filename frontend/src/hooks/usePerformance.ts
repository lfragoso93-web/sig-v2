import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

// ─── Tipos ────────────────────────────────────────────────────────────────────

export interface Position {
  ticker: string
  quantity: number
  avg_price: number
  current_price: number
  current_value: number
  invested: number
  gain: number
  gain_pct: number
  allocation_pct: number
}

export interface PortfolioSummaryData {
  portfolio_id: number
  total_invested: number
  current_value: number
  total_gain: number
  total_gain_pct: number
  daily_change: number
  daily_change_pct: number
  positions: Position[]
}

export interface EquityPoint {
  date: string
  value: number
}

export type EquityPeriod = '1m' | '3m' | '6m' | '1y' | 'all'

// ─── Hooks ────────────────────────────────────────────────────────────────────

/** Resumo geral da carteira (posições, ganhos, alocação) */
export function usePortfolioSummary(portfolioId: number | null) {
  return useQuery<PortfolioSummaryData>({
    queryKey: ['portfolio-summary', portfolioId],
    queryFn: () =>
      api.get(`/portfolios/${portfolioId}/summary`).then((r) => r.data),
    enabled: !!portfolioId,
  })
}

/**
 * Histórico de evolução do patrimônio para o gráfico de linha.
 * Endpoint: GET /portfolios/{id}/equity-history?period={period}
 * Retorna: EquityPoint[]
 */
export function useEquityHistory(
  portfolioId: number | null,
  period: EquityPeriod = '1y',
) {
  return useQuery<EquityPoint[]>({
    queryKey: ['equity-history', portfolioId, period],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/equity-history`, { params: { period } })
        .then((r) => r.data),
    enabled: !!portfolioId,
    // Se o endpoint ainda não existir no backend, retorna array vazio
    // em vez de quebrar a UI
    retry: false,
    placeholderData: [],
  })
}

/** @deprecated use usePortfolioSummary */
export function usePerformance(portfolioId: number | null) {
  return usePortfolioSummary(portfolioId)
}
