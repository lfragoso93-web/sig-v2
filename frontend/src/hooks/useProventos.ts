import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

// ─── Tipos base ───────────────────────────────────────────────────────────────

export interface Provento {
  id: number
  portfolio_id: number
  ticker: string
  asset_type: string
  type: string
  amount: number
  total_value: number
  status: 'RECEBIDO' | 'A_RECEBER'
  date: string
  created_at: string
}

export interface ProventoSummary {
  media_mensal: number
  total_12m: number
  total_carteira: number
  meta_mensal: number
  meta_percent: number
}

export interface ProventoDistribution {
  label: string
  value: number
  pct: number
}

export interface ProventoEvolucao {
  period: string
  total: number
}

export interface ProventoHistoricoMensal {
  period: string
  total: number
  count: number
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

export function useProventos(portfolioId: number | null) {
  return useQuery<Provento[]>({
    queryKey: ['proventos', portfolioId],
    queryFn: () =>
      api.get('/proventos', { params: { portfolio_id: portfolioId } }).then((r) => r.data),
    enabled: !!portfolioId,
  })
}

export function useProventosSummary(portfolioId: number | null) {
  return useQuery<ProventoSummary>({
    queryKey: ['proventos-summary', portfolioId],
    queryFn: () =>
      api.get(`/proventos/${portfolioId}/summary`).then((r) => r.data),
    enabled: !!portfolioId,
  })
}

export function useProventosDistribution(portfolioId: number | null) {
  return useQuery<ProventoDistribution[]>({
    queryKey: ['proventos-distribution', portfolioId],
    queryFn: () =>
      api.get(`/proventos/${portfolioId}/distribution`).then((r) => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
  })
}

export function useProventosEvolucao(
  portfolioId: number | null,
  tipo: 'mensal' | 'anual' = 'mensal',
  period = '12m',
) {
  return useQuery<ProventoEvolucao[]>({
    queryKey: ['proventos-evolucao', portfolioId, tipo, period],
    queryFn: () =>
      api
        .get(`/proventos/${portfolioId}/evolucao`, { params: { tipo, period } })
        .then((r) => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
  })
}

export function useProventosHistoricoMensal(
  portfolioId: number | null,
  status = '',
  assetType = '',
) {
  return useQuery<ProventoHistoricoMensal[]>({
    queryKey: ['proventos-historico', portfolioId, status, assetType],
    queryFn: () =>
      api
        .get(`/proventos/${portfolioId}/historico-mensal`, {
          params: { status: status || undefined, asset_type: assetType || undefined },
        })
        .then((r) => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
  })
}

export function useProventosList(
  portfolioId: number | null,
  year?: number,
  status?: string,
  assetType?: string,
) {
  return useQuery<Provento[]>({
    queryKey: ['proventos-list', portfolioId, year, status, assetType],
    queryFn: () =>
      api
        .get('/proventos', {
          params: {
            portfolio_id: portfolioId,
            year: year || undefined,
            status: status || undefined,
            asset_type: assetType || undefined,
          },
        })
        .then((r) => r.data),
    enabled: !!portfolioId,
    placeholderData: [],
  })
}

export function useCreateProvento() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<Provento, 'id' | 'created_at'>) =>
      api.post<Provento>('/proventos', data).then((r) => r.data),
    onSuccess: (_d, v) => {
      qc.invalidateQueries({ queryKey: ['proventos', v.portfolio_id] })
      qc.invalidateQueries({ queryKey: ['proventos-summary', v.portfolio_id] })
    },
  })
}
