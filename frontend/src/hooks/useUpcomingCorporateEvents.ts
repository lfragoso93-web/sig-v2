import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export interface UpcomingCorporateEvent {
  event_id: number
  ticker: string
  event_type: string
  event_date: string
  description: string | null
}

export function useUpcomingCorporateEvents(portfolioId: number | null) {
  return useQuery<UpcomingCorporateEvent[]>({
    queryKey: ['upcoming-corporate-events', portfolioId],
    queryFn: () => api
      .get(`/portfolios/${portfolioId}/corporate-events/upcoming`)
      .then(response => response.data),
    enabled: !!portfolioId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}
