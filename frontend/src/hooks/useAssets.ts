import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { fetchAssets, AssetListParams } from '@/services/assetService'

/**
 * Hook para listagem paginada de ativos.
 *
 * keepPreviousData: a UI não pisca ao trocar de página —
 * mantém os dados anteriores visíveis enquanto a próxima página carrega.
 */
export function useAssets(params: AssetListParams = {}) {
  const { page = 1, page_size = 50, asset_type, q } = params

  return useQuery({
    queryKey: ['assets', { page, page_size, asset_type, q }],
    queryFn: () => fetchAssets({ page, page_size, asset_type: asset_type || undefined, q: q || undefined }),
    placeholderData: keepPreviousData,
    staleTime: 60_000, // 1 min — ativos mudam pouco
  })
}
