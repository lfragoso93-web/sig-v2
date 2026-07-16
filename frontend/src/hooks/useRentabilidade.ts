import { useQuery } from '@tanstack/react-query'
import {
  rentabilidadeService,
  RentabilidadeKpis,
  RentabilidadeAtivo,
  RentabilidadeClasse,
  MonthlyBenchmarkResponse,
} from '@/services/rentabilidadeService'

export type {
  RentabilidadeKpis,
  RentabilidadeAtivo,
  RentabilidadeClasse,
  MonthlyBenchmarkResponse,
}

const STALE_2MIN = 2 * 60 * 1000
const STALE_30MIN = 30 * 60 * 1000

export function useRentabilidadeKpis(portfolioId: number | null) {
  return useQuery<RentabilidadeKpis>({
    queryKey: ['rentabilidade-kpis', portfolioId],
    queryFn: () => rentabilidadeService.getKpis(portfolioId!),
    enabled: !!portfolioId,
    staleTime: STALE_2MIN,
  })
}

export function useRentabilidadeAtivos(portfolioId: number | null) {
  return useQuery<RentabilidadeAtivo[]>({
    queryKey: ['rentabilidade-ativos', portfolioId],
    queryFn: () => rentabilidadeService.getAtivos(portfolioId!),
    enabled: !!portfolioId,
    staleTime: STALE_2MIN,
    placeholderData: [],
  })
}

export function useRentabilidadeClasses(portfolioId: number | null) {
  return useQuery<RentabilidadeClasse[]>({
    queryKey: ['rentabilidade-classes', portfolioId],
    queryFn: () => rentabilidadeService.getClasses(portfolioId!),
    enabled: !!portfolioId,
    staleTime: STALE_2MIN,
    placeholderData: [],
  })
}

export function useMonthlyBenchmarks(portfolioId: number | null, months: number) {
  return useQuery<MonthlyBenchmarkResponse>({
    queryKey: ['rentabilidade-benchmarks-monthly', portfolioId, months],
    queryFn: () => rentabilidadeService.getMonthlyBenchmarks(portfolioId!, months),
    enabled: !!portfolioId,
    staleTime: STALE_30MIN,
  })
}
