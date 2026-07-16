import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'
import { PORTFOLIOS_QUERY_KEY } from '@/hooks/usePortfolios'

export interface PositionItem {
  id: number
  ticker: string
  asset_type: string
  asset_label: string
  quantity: number
  average_price: number
  current_price: number | null
  current_value: number | null
  invested_value: number
  variation_value: number | null
  variation_percent: number | null
  allocation_pct: number
  logo_url?: string | null
  quote_updated_at?: string | null
}

export interface PositionGroup {
  label: string
  count: number
  total_value: number
  total_invested?: number
  variation_pct?: number | null
  daily_variation_value?: number | null
  daily_variation_pct?: number | null
  variation_reference_date?: string | null
  capital_result_value?: number
  capital_result_pct?: number | null
  received_dividends?: number
  total_result_value?: number
  total_result_pct?: number | null
  performance_source?: string
  proventos_as_of?: string | null
  /** @deprecated retorno simples legado; não representa TWR */
  rentabilidade_pct?: number
  target_pct?: number
  positions: PositionItem[]
}

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
  summary_version: 'summary.v2'
  total_patrimonio: number
  total_investido: number
  lucro_total: number
  variacao_valor: number
  variacao_percentual: number
  ganho_nao_realizado: number
  ganho_realizado: number
  rentabilidade_total: number
  rentabilidade_acumulada: number
  rentabilidade_diaria: number | null
  rentabilidade_source: 'snapshot_twr' | 'valuation_fallback'
  dividendos_recebidos_12m: number
  total_proventos: number
  proventos_as_of: string
  proventos_source: 'received_cash_dividends'
  has_partial_prices: boolean
  assets_without_price: string[]
  price_assets_total: number
  price_assets_covered: number
  price_coverage_pct: number
  usd_brl_rate: number
  valuation_mode: 'intraday'
  valuation_updated_at: string | null
  performance_as_of: string | null
  snapshot_id: number | null
  snapshot_date: string | null
  summary_source: 'intraday_valuation_with_snapshot_twr' | 'valuation_fallback'
  return_is_estimated: boolean
  is_reconciled: boolean | null
  reconciliation: Record<string, unknown> | null
}

export interface PortfolioListItem {
  id: number
  name: string
  description?: string
}

export interface PatrimonioHistoryPoint {
  date: string
  period?: string
  value: number
  invested?: number
  capital_result?: number
  accumulated_return_pct?: number
  has_partial_prices?: boolean
  return_is_estimated?: boolean
  history_source?: 'portfolio_snapshot' | 'db_derived_class_history' | string
}

const STALE_2MIN = 2 * 60 * 1000

export function usePositions(portfolioId: number | null) {
  return useQuery<PositionGroup[]>({
    queryKey: ['positions', portfolioId],
    queryFn: () => api.get(`/portfolios/${portfolioId}/positions`).then(r => r.data),
    enabled: !!portfolioId,
    staleTime: STALE_2MIN,
    placeholderData: [],
  })
}

export function useAssetDistribution(portfolioId: number | null) {
  return useQuery<AssetDistribution[]>({
    queryKey: ['asset-distribution', portfolioId],
    queryFn: () => api.get(`/portfolios/${portfolioId}/asset-distribution`).then(r => r.data),
    enabled: !!portfolioId,
    staleTime: STALE_2MIN,
    placeholderData: [],
  })
}

export function usePortfolioSummaryData(portfolioId: number | null) {
  return useQuery<PortfolioSummary>({
    queryKey: ['summary', portfolioId],
    queryFn: () => api.get(`/portfolios/${portfolioId}/summary`).then(r => r.data),
    enabled: !!portfolioId,
    staleTime: STALE_2MIN,
  })
}

export const usePortfolioSummary = usePortfolioSummaryData

export function usePortfolioList() {
  return useQuery<PortfolioListItem[]>({
    queryKey: PORTFOLIOS_QUERY_KEY,
    queryFn: () => api.get('/portfolios').then(r => r.data),
    staleTime: 30_000,
  })
}

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
            months: months >= 60 ? 0 : months,
            ...(assetType ? { asset_type: assetType } : {}),
          },
        })
        .then(r => r.data),
    enabled: !!portfolioId,
    staleTime: STALE_2MIN,
    placeholderData: [],
  })
}
