import { useQuery, useMutation } from '@tanstack/react-query'
import api from '@/services/api'

export interface AiExplanationMetadata {
  provider: string
  model: string
  is_mock_or_deterministic: boolean
  execution_time_ms: number
  disclaimer: string
}

export interface ContributionScenarioDto {
  amount: number
  description: string
  priority_class: string
  estimated_gap_reduction: string
}

export interface PortfolioAiAnalysisResponse {
  portfolio_id: number
  portfolio_name: string
  reference_date: string
  overall_health_score: number
  posture_label: string
  posture_summary: string
  executive_summary: string
  key_strengths: string[]
  attention_points: string[]
  rebalancing_strategy: string
  contribution_scenarios: ContributionScenarioDto[]
  metadata: AiExplanationMetadata
}

export interface ClassContributionAllocation {
  asset_type: string
  label: string
  current_value: number
  current_weight_pct: number
  target_weight_pct: number | null
  allocated_amount: number
  projected_value: number
  projected_weight_pct: number
  action_explanation: string
}

export interface ContributionSimulationResponse {
  portfolio_id: number
  contribution_amount: number
  current_total_value: number
  projected_total_value: number
  suggested_allocations: ClassContributionAllocation[]
  overall_impact_summary: string
  metadata: AiExplanationMetadata
}

export interface AiQuestionResponse {
  portfolio_id: number
  question: string
  answer: string
  key_metrics_referenced: string[]
  metadata: AiExplanationMetadata
}

export function usePortfolioAiAnalysis(portfolioId: number | null) {
  return useQuery<PortfolioAiAnalysisResponse>({
    queryKey: ['portfolio-ai-analysis', portfolioId],
    queryFn: async () => {
      const response = await api.get<PortfolioAiAnalysisResponse>(
        `/portfolios/${portfolioId}/ai-analysis`
      )
      return response.data
    },
    enabled: !!portfolioId,
    staleTime: 60 * 1000,
  })
}

export function useSimulateContribution(portfolioId: number | null) {
  return useMutation<ContributionSimulationResponse, Error, number>({
    mutationFn: async (amount: number) => {
      if (!portfolioId) throw new Error('Carteira não selecionada')
      const response = await api.post<ContributionSimulationResponse>(
        `/portfolios/${portfolioId}/ai-analysis/simulate-contribution`,
        { contribution_amount: amount }
      )
      return response.data
    },
  })
}

export function useAskPortfolioAi(portfolioId: number | null) {
  return useMutation<AiQuestionResponse, Error, string>({
    mutationFn: async (question: string) => {
      if (!portfolioId) throw new Error('Carteira não selecionada')
      const response = await api.post<AiQuestionResponse>(
        `/portfolios/${portfolioId}/ai-analysis/ask`,
        { question }
      )
      return response.data
    },
  })
}
