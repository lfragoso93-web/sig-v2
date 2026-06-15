import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

export function useFxRate(from: string, to: string) {
  return useQuery<{ rate: number }>({
    queryKey: ['fxrate', from, to],
    queryFn: () =>
      api.get('/fxrate', { params: { from, to } }).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  })
}

/** Alias conveniente para o par USD/BRL */
export function useUsdBrl() {
  return useFxRate('USD', 'BRL')
}
