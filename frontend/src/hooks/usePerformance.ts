import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export interface PerformanceSummary {
  total_invested: number
  current_value: number
  total_return: number
  total_return_pct: number
}

export function usePerformance(portfolioId: number | null) {
  return useQuery<PerformanceSummary>({
    queryKey: ['performance', portfolioId],
    queryFn: () =>
      api.get('/performance', { params: { portfolio_id: portfolioId } }).then((r) => r.data),
    enabled: !!portfolioId,
  })
}
