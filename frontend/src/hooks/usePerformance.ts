import { useQuery } from '@tanstack/react-query'
import { performanceService } from '@/services/performanceService'

export function usePortfolioPerformance(portfolioId: number) {
  return useQuery({
    queryKey: ['performance', portfolioId],
    queryFn: () => performanceService.getPortfolio(portfolioId),
    staleTime: 3 * 60 * 1000,   // 3 minutos
    refetchInterval: 5 * 60 * 1000,
    enabled: !!portfolioId,
  })
}

export function useAssetPerformance(portfolioId: number, ticker: string) {
  return useQuery({
    queryKey: ['performance', portfolioId, ticker],
    queryFn: () => performanceService.getAsset(portfolioId, ticker),
    staleTime: 3 * 60 * 1000,
    enabled: !!portfolioId && !!ticker,
  })
}
