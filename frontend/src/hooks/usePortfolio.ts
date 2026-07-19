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
  total_invested: number
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

const SUMMARY_KEYS = new Set<keyof PortfolioSummary>([
  'summary_version',
  'total_patrimonio',
  'total_investido',
  'lucro_total',
  'variacao_valor',
  'variacao_percentual',
  'ganho_nao_realizado',
  'ganho_realizado',
  'rentabilidade_total',
  'rentabilidade_acumulada',
  'rentabilidade_diaria',
  'rentabilidade_source',
  'dividendos_recebidos_12m',
  'total_proventos',
  'proventos_as_of',
  'proventos_source',
  'has_partial_prices',
  'assets_without_price',
  'price_assets_total',
  'price_assets_covered',
  'price_coverage_pct',
  'usd_brl_rate',
  'valuation_mode',
  'valuation_updated_at',
  'performance_as_of',
  'snapshot_id',
  'snapshot_date',
  'summary_source',
  'return_is_estimated',
  'is_reconciled',
  'reconciliation',
])

const SUMMARY_NUMBER_KEYS: (keyof PortfolioSummary)[] = [
  'total_patrimonio',
  'total_investido',
  'lucro_total',
  'variacao_valor',
  'variacao_percentual',
  'ganho_nao_realizado',
  'ganho_realizado',
  'rentabilidade_total',
  'rentabilidade_acumulada',
  'dividendos_recebidos_12m',
  'total_proventos',
  'price_assets_total',
  'price_assets_covered',
  'price_coverage_pct',
  'usd_brl_rate',
]

function contractError(field: string): never {
  throw new Error(`Contrato summary.v2 inválido: ${field}`)
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === 'string'
}

export function parsePortfolioSummary(payload: unknown): PortfolioSummary {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    return contractError('payload')
  }

  const summary = payload as Record<string, unknown>
  const unexpectedKey = Object.keys(summary).find(key => !SUMMARY_KEYS.has(key as keyof PortfolioSummary))
  if (unexpectedKey) contractError(unexpectedKey)

  for (const key of SUMMARY_KEYS) {
    if (!(key in summary)) contractError(key)
  }
  for (const key of SUMMARY_NUMBER_KEYS) {
    if (typeof summary[key] !== 'number' || !Number.isFinite(summary[key])) contractError(key)
  }

  if (summary.summary_version !== 'summary.v2') contractError('summary_version')
  if (summary.rentabilidade_diaria !== null
    && (typeof summary.rentabilidade_diaria !== 'number' || !Number.isFinite(summary.rentabilidade_diaria))) {
    contractError('rentabilidade_diaria')
  }
  if (summary.rentabilidade_source !== 'snapshot_twr'
    && summary.rentabilidade_source !== 'valuation_fallback') contractError('rentabilidade_source')
  if (typeof summary.proventos_as_of !== 'string') contractError('proventos_as_of')
  if (summary.proventos_source !== 'received_cash_dividends') contractError('proventos_source')
  if (typeof summary.has_partial_prices !== 'boolean') contractError('has_partial_prices')
  if (!Array.isArray(summary.assets_without_price)
    || summary.assets_without_price.some(item => typeof item !== 'string')) contractError('assets_without_price')
  if (summary.valuation_mode !== 'intraday') contractError('valuation_mode')
  if (!isNullableString(summary.valuation_updated_at)) contractError('valuation_updated_at')
  if (!isNullableString(summary.performance_as_of)) contractError('performance_as_of')
  if (summary.snapshot_id !== null
    && (typeof summary.snapshot_id !== 'number' || !Number.isInteger(summary.snapshot_id))) contractError('snapshot_id')
  if (!isNullableString(summary.snapshot_date)) contractError('snapshot_date')
  if (summary.summary_source !== 'intraday_valuation_with_snapshot_twr'
    && summary.summary_source !== 'valuation_fallback') contractError('summary_source')
  if (typeof summary.return_is_estimated !== 'boolean') contractError('return_is_estimated')
  if (summary.is_reconciled !== null && typeof summary.is_reconciled !== 'boolean') contractError('is_reconciled')
  if (summary.reconciliation !== null
    && (typeof summary.reconciliation !== 'object' || Array.isArray(summary.reconciliation))) {
    contractError('reconciliation')
  }

  return summary as unknown as PortfolioSummary
}

const STALE_2MIN = 2 * 60 * 1000

export function usePositions(portfolioId: number | null) {
  return useQuery<PositionGroup[]>({
    queryKey: ['positions', portfolioId],
    queryFn: () => api.get(`/portfolios/${portfolioId}/positions`).then(r => r.data),
    enabled: !!portfolioId,
    staleTime: STALE_2MIN,
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
    queryFn: () => api
      .get(`/portfolios/${portfolioId}/summary`)
      .then(r => parsePortfolioSummary(r.data)),
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
