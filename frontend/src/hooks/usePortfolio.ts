import { useQuery } from '@tanstack/react-query'
import { portfolioService } from '@/services/portfolioService'

export function usePortfolioList() {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: portfolioService.listPortfolios,
  })
}

export function usePortfolioSummary(portfolioId: number) {
  return useQuery({
    queryKey: ['portfolio-summary', portfolioId],
    queryFn: () => portfolioService.getSummary(portfolioId),
    enabled: !!portfolioId,
  })
}

export function usePatrimonioHistory(portfolioId: number, months = 12) {
  return useQuery({
    queryKey: ['patrimonio-history', portfolioId, months],
    queryFn: () => portfolioService.getPatrimonioHistory(portfolioId, months),
    enabled: !!portfolioId,
  })
}

export function useAssetDistribution(portfolioId: number) {
  return useQuery({
    queryKey: ['asset-distribution', portfolioId],
    queryFn: () => portfolioService.getAssetDistribution(portfolioId),
    enabled: !!portfolioId,
  })
}

export function usePositions(portfolioId: number) {
  return useQuery({
    queryKey: ['positions', portfolioId],
    queryFn: () => portfolioService.getPositions(portfolioId),
    enabled: !!portfolioId,
    refetchInterval: 1000 * 60 * 5,
  })
}
