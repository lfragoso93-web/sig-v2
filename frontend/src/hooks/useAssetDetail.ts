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
