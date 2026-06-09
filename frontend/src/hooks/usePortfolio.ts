import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export interface PortfolioDetail {
  id: number
  name: string
  description: string | null
  created_at: string
}

export function usePortfolio(id: number | null) {
  return useQuery<PortfolioDetail>({
    queryKey: ['portfolio', id],
    queryFn: () => api.get(`/portfolios/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}
