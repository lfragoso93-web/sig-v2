import { useQuery, useMutation } from '@tanstack/react-query'
import api from '@/services/api'

export interface RecommendedAsset {
  ticker: string
  name: string
  asset_type: string
  current_price: number
  target_weight_pct: number
  reason: string
  expected_yield_pct?: number | null
  risk_level: string
}

export interface RecommendedClass {
  asset_type: string
  label: string
  target_weight_pct: number
  description: string
  assets: RecommendedAsset[]
}

export interface RecommendedPortfolio {
  id: string
  title: string
  subtitle: string
  strategy: 'patrimonio' | 'proventos' | 'performance'
  thesis: string
  risk_profile: string
  expected_annual_return: string
  expected_dividend_yield: string
  suggested_time_horizon: string
  diversification_score: number
  classes: RecommendedClass[]
}

export interface SimulatedAssetAllocation {
  ticker: string
  name: string
  asset_type: string
  current_price: number
  weight_in_portfolio_pct: number
  allocated_amount: number
  suggested_quantity: number
  reason: string
}

export interface SimulatedClassAllocation {
  asset_type: string
  label: string
  target_weight_pct: number
  allocated_amount: number
  assets: SimulatedAssetAllocation[]
}

export interface RecommendedPortfolioSimulationRequest {
  strategy: string
  total_amount: number
  custom_class_weights?: Record<string, number>
}

export interface RecommendedPortfolioSimulationResponse {
  strategy: string
  total_amount: number
  classes: SimulatedClassAllocation[]
  summary: string
}

export function useRecommendedPortfolios() {
  return useQuery<RecommendedPortfolio[]>({
    queryKey: ['recommended-portfolios'],
    queryFn: () => api.get<RecommendedPortfolio[]>('/recommended-portfolios').then(r => r.data),
    staleTime: 1000 * 60 * 15, // 15 minutos
  })
}

export function useSimulateRecommendedPortfolio() {
  return useMutation<
    RecommendedPortfolioSimulationResponse,
    Error,
    RecommendedPortfolioSimulationRequest
  >({
    mutationFn: (data) =>
      api.post<RecommendedPortfolioSimulationResponse>('/recommended-portfolios/simulate', data).then(r => r.data),
  })
}
