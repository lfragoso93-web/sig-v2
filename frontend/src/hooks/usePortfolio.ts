import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

// ── Tipos ─────────────────────────────────────────────────────────────────────────────────────────

export interface PositionItem {
  id: number
  ticker: string
  asset_type: string
  asset_label: string
  quantity: number
  average_price: number
  current_price: number
  current_value: number
  invested_value: number
  variation_value: number
  variation_percent: number
  allocation_pct: number
  logo_url?: string | null   // URL do logo coletado pelo onboarding (null = ainda nao disponivel)
}

export interface PositionGroup {
  label: string
  count: number
  total_value: number
  positions: PositionItem[]
}

/** Distribuição por tipo de ativo */
export interface AssetDistribution {
  asset_type: string
  label: string
  value: number
  percentage: number
  color?: string
}

/** @deprecated use AssetDistribution */
export type AssetTypeDistribution = AssetDistribution

export interface PortfolioSummary {
  total_invested: number
  current_value: number
  total_gain: number
  total_gain_pct: number
  daily_change?: number
  daily_change_pct?: number
  total_patrimonio?: number
  total_investido?: number
  lucro_total?: number
  variacao_valor?: number
  variacao_percentual?: number
  rentabilidade_total?: number
  dividendos_recebidos_12m?: number
  total_proventos?: number
}

export interface PortfolioListItem {
  id: number
  name: string
  description?: string
}

/** Ponto de histórico de patrimônio */
export interface PatrimonioHistoryPoint {
  date: string
  value: number
  invested?: number
}

// ── Hooks ─────────────────────────────────────────────────────────────────────────────────────────

export function usePositions(portfolioId: number | null) {
  return useQuery<PositionGroup[]>({
    queryKey: ['positions', portfolioId],
    queryFn: () =>
      api.get(`/portfolios/${portfolioId}/positions`).then(r => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
  })
}

export function useAssetDistribution(portfolioId: number | null) {
  return useQuery<AssetDistribution[]>({
    queryKey: ['asset-distribution', portfolioId],
    queryFn: () =>
      api.get(`/portfolios/${portfolioId}/asset-distribution`).then(r => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
  })
}

export function usePortfolioSummaryData(portfolioId: number | null) {
  return useQuery<PortfolioSummary>({
    queryKey: ['summary', portfolioId],
    queryFn: () =>
      api.get(`/portfolios/${portfolioId}/summary`).then(r => r.data),
    enabled: !!portfolioId,
  })
}

/** Alias para componentes que importam usePortfolioSummary */
export const usePortfolioSummary = usePortfolioSummaryData

/** Lista todas as carteiras do usuário */
export function usePortfolioList() {
  return useQuery<PortfolioListItem[]>({
    queryKey: ['portfolio-list'],
    queryFn: () => api.get('/portfolios').then(r => r.data),
  })
}

/** Histórico de patrimônio mensal (total ou por classe de ativo) */
export function usePatrimonioHistory(
  portfolioId: number | null,
  months = 12,
  assetType?: string | null,
) {
  return useQuery<PatrimonioHistoryPoint[]>({
    queryKey: ['patrimonio-history', portfolioId, months, assetType ?? 'all'],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/patrimonio-history`, {
          params: {
            months,
            ...(assetType ? { asset_type: assetType } : {}),
          },
        })
        .then(r => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
  })
}
