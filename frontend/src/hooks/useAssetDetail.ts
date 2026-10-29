import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export interface PricePoint {
  date: string
  price: number
}

export interface AssetDetail {
  id: number
  ticker: string
  name: string | null
  asset_type: string
  last_price: number | null
  last_price_updated_at: string | null
  current_price: number | null
  price_history: PricePoint[]
}

export interface CorporateLifecycleEvent {
  source_event_id: string
  ticker: string
  event_date: string
  event_type: string
  quantity_factor: number
  fractional_quantity: number | null
  settlement_status: 'SETTLED' | 'PENDING_VALUE' | null
  unit_settlement_price_brl: number | null
  gross_amount_brl: number | null
  cost_basis_brl: number | null
  realized_pnl_brl: number | null
  cash_treatment: string | null
  message: string | null
}

const KEY = (ticker: string | null, days: number) =>
  ['asset-detail', ticker, days]

export function useAssetDetail(
  ticker: string | null,
  days: number = 90,
) {
  return useQuery<AssetDetail>({
    queryKey: KEY(ticker, days),
    queryFn: () =>
      api.get(`/assets/${ticker}/detail`, { params: { days } }).then(r => r.data),
    enabled: !!ticker,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAssetCorporateLifecycle(
  portfolioId: number | null,
  ticker: string | null,
) {
  return useQuery<CorporateLifecycleEvent[]>({
    queryKey: ['asset-corporate-lifecycle', portfolioId, ticker],
    queryFn: () => api
      .get(`/portfolios/${portfolioId}/assets/${ticker}/corporate-events`)
      .then(r => r.data),
    enabled: !!portfolioId && !!ticker,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export interface FIIIndicators {
  pvp: number | null
  dividend_yield: number | null
  dividend_yield_1m?: number | null
  net_worth: number | null
  nav_per_share?: number | null
  share_holders: number | null
  shares_outstanding?: number | null
  physical_vacancy: number | null
  financial_vacancy: number | null
  properties_count: number | null
  total_area_m2?: number | null
  segment: string | null
  segment_type?: string | null
  management_type?: string | null
  administrator_name?: string | null
  administrator_cnpj?: string | null
  cnpj?: string | null
}

export interface StockFundamentals {
  pe: number | null
  forward_pe?: number | null
  pb: number | null
  dividend_yield: number | null
  eps: number | null
  market_cap: number | null
  enterprise_value?: number | null
  enterprise_to_ebitda?: number | null
  net_revenue: number | null
  net_income: number | null
  ebitda: number | null
  net_margin: number | null
  operating_margin?: number | null
  gross_margin?: number | null
  roe: number | null
  roa?: number | null
  net_debt: number | null
  total_debt?: number | null
  free_cash_flow?: number | null
  book_value?: number | null
  peg_ratio?: number | null
  beta?: number | null
  sector?: string | null
  industry?: string | null
  description?: string | null
  website?: string | null
  employees?: number | null
  recommendation?: string | null
  target_price?: number | null
}

export interface CryptoIndicators {
  coin: string
  coin_name: string
  price_usd: number | null
  price_brl: number | null
  change_24h_pct: number | null
  volume_24h: number | null
  market_cap_brl: number | null
  market_cap_rank: number | null
  day_low: number | null
  day_high: number | null
  currency_rate_usd: number | null
  logo_url: string | null
}

export interface TreasuryIndicators {
  symbol: string
  bond_type: string
  name: string
  indexer: string | null
  coupon_type: string | null
  maturity_date: string | null
  duration_days: number | null
  buy_rate: number | null
  sell_rate: number | null
  buy_price: number | null
  sell_price: number | null
  base_price: number | null
}

export interface InternationalProfile {
  country: string | null
  currency: string | null
  exchange: string | null
  industry: string | null
  weburl: string | null
  logo: string | null
  market_cap_usd: number | null
  consensus: string | null
  strong_buy: number | null
  buy: number | null
  hold: number | null
  sell: number | null
  strong_sell: number | null
}

export interface AssetEnrichment {
  ticker: string
  coverage_status: string
  capabilities?: Record<string, boolean>
  fii_indicators: FIIIndicators | null
  stock_fundamentals: StockFundamentals | null
  crypto_indicators?: CryptoIndicators | null
  treasury_indicators?: TreasuryIndicators | null
  international_profile?: InternationalProfile | null
}

export interface AssetPortfolioPositionInsight {
  is_held: boolean
  quantity: number
  average_price: number
  invested_value: number
  current_price: number
  current_value: number
  capital_gain_value: number
  capital_gain_percent: number
  dividends_received: number
  total_return_value: number
  total_return_percent: number
  portfolio_weight_percent: number
  class_weight_percent: number
  class_name: string | null
  class_label: string | null
  class_current_allocation_percent: number
  class_target_percent: number | null
  yield_on_cost_percent: number | null
}

export interface AIAssetInsight {
  concentration_level: 'LOW' | 'BALANCED' | 'WARNING' | 'HIGH'
  concentration_message: string
  income_assessment: string
  rebalancing_guidance: string
  strategic_role: string
  explainable_summary: string
}

export interface AssetPortfolioInsightResponse {
  ticker: string
  portfolio_id: number
  position: AssetPortfolioPositionInsight
  enrichment: AssetEnrichment
  ai_insights: AIAssetInsight
}

export function useAssetEnrichment(ticker: string | null, assetType?: string | null) {
  return useQuery<AssetEnrichment>({
    queryKey: ['asset-enrichment', ticker, assetType],
    queryFn: () =>
      api
        .get(`/assets/${ticker}/enrichment`, { params: assetType ? { asset_type: assetType } : {} })
        .then(r => r.data),
    enabled: !!ticker,
    retry: false,
    staleTime: 10 * 60 * 1000,
  })
}

export function useAssetPortfolioInsights(portfolioId: number | null, ticker: string | null) {
  return useQuery<AssetPortfolioInsightResponse>({
    queryKey: ['asset-portfolio-insights', portfolioId, ticker],
    queryFn: () =>
      api.get(`/portfolios/${portfolioId}/assets/${ticker}/insights`).then(r => r.data),
    enabled: !!portfolioId && !!ticker,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}
