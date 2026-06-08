import { useQuery } from '@tanstack/react-query'
import { proventosService } from '@/services/proventosService'

export function useProventosSummary(portfolioId: number) {
  return useQuery({
    queryKey: ['proventos-summary', portfolioId],
    queryFn: () => proventosService.getSummary(portfolioId),
    enabled: !!portfolioId,
  })
}

export function useProventosDistribution(portfolioId: number, months = 12) {
  return useQuery({
    queryKey: ['proventos-distribution', portfolioId, months],
    queryFn: () => proventosService.getDistribution(portfolioId, months),
    enabled: !!portfolioId,
  })
}

export function useProventosEvolucao(portfolioId: number, tipo: 'mensal' | 'anual', period: string) {
  return useQuery({
    queryKey: ['proventos-evolucao', portfolioId, tipo, period],
    queryFn: () => proventosService.getEvolucao(portfolioId, tipo, period),
    enabled: !!portfolioId,
  })
}

export function useProventosHistoricoMensal(portfolioId: number, status: string, assetType: string) {
  return useQuery({
    queryKey: ['proventos-historico', portfolioId, status, assetType],
    queryFn: () => proventosService.getHistoricoMensal(portfolioId, status, assetType),
    enabled: !!portfolioId,
  })
}

export function useProventosList(portfolioId: number, year?: number, status?: string, assetType?: string) {
  return useQuery({
    queryKey: ['proventos-list', portfolioId, year, status, assetType],
    queryFn: () => proventosService.getList(portfolioId, year, status, assetType),
    enabled: !!portfolioId,
  })
}
