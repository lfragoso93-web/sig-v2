import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'

export type RebalanceAction = 'buy' | 'hold' | 'reduce'
export type ConcentrationRiskLevel = 'low' | 'balanced' | 'warning' | 'critical'

export interface TopAssetConcentration {
  ticker: string
  name: string | null
  current_value: number
  weight_in_class_pct: number
  weight_in_portfolio_pct: number
}

export interface ClassAllocationAnalysis {
  current_value: number
  current_weight_pct: number
  target_weight_pct: number | null
  target_value: number | null
  gap_weight_pct: number | null
  gap_value: number | null
  rebalance_action: RebalanceAction
  suggested_action_label: string
}

export interface ClassConcentrationAnalysis {
  asset_count: number
  top_asset: TopAssetConcentration | null
  hhi_score: number | null
  risk_level: ConcentrationRiskLevel
  risk_label: string
  status_message: string
}

export interface ClassIncomeAnalysis {
  is_applicable: boolean
  total_proventos: number
  weighted_dy_pct: number | null
  top_income_asset: string | null
  status_label: string
}

export interface ClassFixedIncomeAnalysis {
  is_applicable: boolean
  cdi_allocation_pct: number | null
  ipca_allocation_pct: number | null
  pre_allocation_pct: number | null
  maturing_next_12m_value: number | null
  maturing_next_12m_pct: number | null
}

export interface ClassAnalysisDetail {
  asset_type: string
  label: string
  health_score: number
  allocation: ClassAllocationAnalysis
  concentration: ClassConcentrationAnalysis
  income: ClassIncomeAnalysis
  fixed_income: ClassFixedIncomeAnalysis
  key_findings: string[]
}

export interface PortfolioConsolidatedAnalysisResponse {
  portfolio_id: number
  portfolio_name: string
  reference_date: string
  total_value: number
  overall_health_score: number
  max_divergence_class: string | null
  classes_analyzed_count: number
  rebalance_priority_classes: string[]
  classes: ClassAnalysisDetail[]
  provenance: Record<string, string>
}

export function usePortfolioAnalysis(portfolioId?: number | null) {
  return useQuery<PortfolioConsolidatedAnalysisResponse>({
    queryKey: ['portfolio-analysis', portfolioId],
    queryFn: async () => {
      const { data } = await api.get<PortfolioConsolidatedAnalysisResponse>(
        `/portfolios/${portfolioId}/analysis`,
      )
      return data
    },
    enabled: Boolean(portfolioId),
    staleTime: 1000 * 60 * 5,
  })
}
