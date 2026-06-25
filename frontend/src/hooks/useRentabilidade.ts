import { useQuery } from '@tanstack/react-query'
import {
  rentabilidadeService,
  RentabilidadeKpis,
  RentabilidadeAtivo,
  RentabilidadeClasse,
} from '@/services/rentabilidadeService'

// re-exporta tipos para componentes que importam daqui
export type { RentabilidadeKpis, RentabilidadeAtivo, RentabilidadeClasse }

export function useRentabilidadeKpis(portfolioId: number | null) {
  return useQuery<RentabilidadeKpis>({
    queryKey: ['rentabilidade-kpis', portfolioId],
    queryFn:  () => rentabilidadeService.getKpis(portfolioId!),
    enabled:  !!portfolioId,
  })
}

export function useRentabilidadeAtivos(portfolioId: number | null) {
  return useQuery<RentabilidadeAtivo[]>({
    queryKey:        ['rentabilidade-ativos', portfolioId],
    queryFn:         () => rentabilidadeService.getAtivos(portfolioId!),
    enabled:         !!portfolioId,
    placeholderData: [],
  })
}

export function useRentabilidadeClasses(portfolioId: number | null) {
  return useQuery<RentabilidadeClasse[]>({
    queryKey:        ['rentabilidade-classes', portfolioId],
    queryFn:         () => rentabilidadeService.getClasses(portfolioId!),
    enabled:         !!portfolioId,
    placeholderData: [],
  })
}
