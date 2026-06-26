import api from './api'

export interface AssetListItem {
  id: number
  ticker: string
  name: string | null
  asset_type: string
  last_price: number | null
  last_price_updated_at: string | null
}

export interface AssetListResponse {
  items: AssetListItem[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AssetListParams {
  page?: number
  page_size?: number
  asset_type?: string
  q?: string
}

export async function fetchAssets(params: AssetListParams = {}): Promise<AssetListResponse> {
  const { data } = await api.get<AssetListResponse>('/assets/', { params })
  return data
}
