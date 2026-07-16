import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export interface DailyPoint {
  date: string
  market_value: number
  cost_basis: number
  invested_total: number
  net_external_flow: number
  unrealized_pnl: number
  realized_pnl: number
  total_pnl: number
  return_pct: number
  daily_return_pct: number
  accumulated_return_pct: number
  dividends_day: number
  dividends_accumulated: number
  has_partial_prices: boolean
  return_is_estimated: boolean
  history_source: string
}

export interface MonthlyPoint extends DailyPoint {
  period: string
  value: number
  invested: number
  monthly_return_pct: number
}

export type PeriodOption = '6m' | '12m' | '24m' | 'all'

export const PERIOD_DAYS: Record<PeriodOption, number> = {
  '6m': 180,
  '12m': 365,
  '24m': 730,
  'all': 0,
}

export const PERIOD_MONTHS: Record<PeriodOption, number> = {
  '6m': 6,
  '12m': 12,
  '24m': 24,
  'all': 0,
}

export function useDailyEvolution(
  portfolioId: number | null,
  period: PeriodOption = '12m',
) {
  const days = PERIOD_DAYS[period]
  return useQuery<DailyPoint[]>({
    queryKey: ['evolution-daily', portfolioId, period],
    queryFn: () =>
      api
        .get(`/performance/${portfolioId}/evolution/daily`, { params: { days } })
        .then(r => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
    staleTime: 5 * 60 * 1000,
  })
}

export function useMonthlyEvolution(
  portfolioId: number | null,
  period: PeriodOption = '12m',
) {
  const months = PERIOD_MONTHS[period]
  return useQuery<MonthlyPoint[]>({
    queryKey: ['evolution-monthly', portfolioId, period],
    queryFn: () =>
      api
        .get(`/performance/${portfolioId}/evolution/monthly`, { params: { months } })
        .then(r => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
    staleTime: 5 * 60 * 1000,
  })
}
