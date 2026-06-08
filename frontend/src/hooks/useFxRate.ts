import { useQuery } from '@tanstack/react-query'
import { fxService } from '@/services/fxService'

export function useUsdBrl() {
  return useQuery({
    queryKey: ['fx-usd-brl'],
    queryFn: fxService.getUsdBrl,
    staleTime: 5 * 60 * 1000,  // 5 minutos
    refetchInterval: 5 * 60 * 1000,
  })
}
