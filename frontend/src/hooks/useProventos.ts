import { useQuery } from '@tanstack/react-query'
import {
  proventosService,
  ProventoDistribution,
  ProventoItem,
  ProventosFilters,
  ProventosHistoricoMes,
  ProventosListResponse,
  ProventosSummary,
} from '@/services/proventosService'

// re-exporta tipos para componentes que importam daqui
export type {
  ProventoDistribution,
  ProventoItem,
  ProventosFilters,
  ProventosHistoricoMes,
  ProventosListResponse,
  ProventosSummary,
}

// ─── Summary ────────────────────────────────────────────────────────────

export function useProventosSummary(portfolioId: number | null, params?: ProventosFilters) {
  return useQuery<ProventosSummary>({
    queryKey: ['proventos-summary', portfolioId, params],
    queryFn:  () => proventosService.getSummary(portfolioId!, params),
    enabled:  !!portfolioId,
  })
}

// ─── Distribuicao por ativo ──────────────────────────────────────────────

export function useProventosDistribuicao(
  portfolioId: number | null,
  months = 12,
  params?: ProventosFilters,
) {
  return useQuery<ProventoDistribution[]>({
    queryKey:    ['proventos-distribuicao', portfolioId, months, params],
    queryFn:     () => proventosService.getDistribuicao(portfolioId!, months, params),
    enabled:     !!portfolioId,
    placeholderData: [],
  })
}

// ─── Historico mensal ──────────────────────────────────────────────────────

export function useProventosHistoricoMensal(
  portfolioId: number | null,
  params?: ProventosFilters,
) {
  return useQuery<ProventosHistoricoMes[]>({
    queryKey:    ['proventos-historico', portfolioId, params],
    queryFn:     () => proventosService.getHistoricoMensal(portfolioId!, params),
    enabled:     !!portfolioId,
    placeholderData: [],
  })
}

// ─── Lista de proventos (recebidos + futuros) ────────────────────────────

export function useProventosList(
  portfolioId: number | null,
  params?: ProventosFilters & {
    page?:          number
    page_size?:     number
  },
) {
  return useQuery<ProventosListResponse>({
    queryKey:    ['proventos-list', portfolioId, params],
    queryFn:     () => proventosService.getList(portfolioId!, params),
    enabled:     !!portfolioId,
    placeholderData: { total: 0, page: 1, page_size: 50, items: [] },
  })
}
