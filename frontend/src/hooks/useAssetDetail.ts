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
