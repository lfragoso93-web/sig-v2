import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  proventosService,
  ProventoDistribution,
  ProventoItem,
  ProventosHistoricoMes,
  ProventosListResponse,
  ProventosSummary,
} from '@/services/proventosService'

// re-exporta tipos para componentes que importam daqui
export type {
  ProventoDistribution,
  ProventoItem,
  ProventosHistoricoMes,
  ProventosListResponse,
  ProventosSummary,
}

// ─── Summary ────────────────────────────────────────────────────────────

export function useProventosSummary(portfolioId: number | null) {
  return useQuery<ProventosSummary>({
    queryKey: ['proventos-summary', portfolioId],
    queryFn:  () => proventosService.getSummary(portfolioId!),
    enabled:  !!portfolioId,
  })
}

// ─── Distribuicao por ativo ──────────────────────────────────────────────

export function useProventosDistribuicao(portfolioId: number | null, months = 12) {
  return useQuery<ProventoDistribution[]>({
    queryKey:    ['proventos-distribuicao', portfolioId, months],
    queryFn:     () => proventosService.getDistribuicao(portfolioId!, months),
    enabled:     !!portfolioId,
    placeholderData: [],
  })
}

// ─── Historico mensal ──────────────────────────────────────────────────────

export function useProventosHistoricoMensal(
  portfolioId: number | null,
  status?:    string,
  assetType?: string,
) {
  return useQuery<ProventosHistoricoMes[]>({
    queryKey:    ['proventos-historico', portfolioId, status, assetType],
    queryFn:     () =>
      proventosService.getHistoricoMensal(portfolioId!, status, assetType),
    enabled:     !!portfolioId,
    placeholderData: [],
  })
}

// ─── Lista de proventos (recebidos + futuros) ────────────────────────────

export function useProventosList(
  portfolioId: number | null,
  params?: {
    status?:     string
    year?:       number
    asset_type?: string
    page?:       number
    page_size?:  number
  },
) {
  return useQuery<ProventosListResponse>({
    queryKey:    ['proventos-list', portfolioId, params],
    queryFn:     () => proventosService.getList(portfolioId!, params),
    enabled:     !!portfolioId,
    placeholderData: { total: 0, page: 1, page_size: 50, items: [] },
  })
}

// ─── Sync manual ──────────────────────────────────────────────────────────────

export function useSyncProventos(portfolioId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => proventosService.sync(portfolioId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['proventos-summary',    portfolioId] })
      qc.invalidateQueries({ queryKey: ['proventos-distribuicao', portfolioId] })
      qc.invalidateQueries({ queryKey: ['proventos-historico',  portfolioId] })
      qc.invalidateQueries({ queryKey: ['proventos-list',       portfolioId] })
    },
  })
}
