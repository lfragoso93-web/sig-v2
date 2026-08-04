/**
 * Hooks para buscar dados do módulo IRPF.
 * Expõe contratos legados e contratos canônicos versionados.
 */
import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'
import type {
  IRPFCanonicalAnnualAssessment,
  IRPFCanonicalAssetsAssessment,
  IRPFCanonicalCapitalGainsAssessment,
  IRPFCanonicalIncomeAssessment,
  IRPFReportOut,
} from '@/types/irpf'

export interface IRPFReportView
  extends Omit<IRPFReportOut, 'ganhos_mensais' | 'dividendos'> {
  ganhos_capital: IRPFReportOut['ganhos_mensais']
  rendimentos_isentos: IRPFReportOut['dividendos']
}

export function toIRPFReportView(report: IRPFReportOut): IRPFReportView {
  const { ganhos_mensais, dividendos, ...rest } = report
  return {
    ...rest,
    ganhos_capital: ganhos_mensais,
    rendimentos_isentos: dividendos,
  }
}

export function useIRPFAnos(portfolioId: number | null) {
  return useQuery<number[]>({
    queryKey: ['irpf-anos', portfolioId],
    queryFn: async () => {
      const res = await api.get(`/portfolios/${portfolioId}/irpf/anos`)
      return res.data
    },
    enabled: !!portfolioId,
    staleTime: 1000 * 60 * 5,
  })
}

export function useIRPFReport(
  portfolioId: number | null,
  year: number | null,
  refresh = false,
) {
  return useQuery<IRPFReportView>({
    queryKey: ['irpf-report', portfolioId, year, refresh],
    queryFn: async () => {
      const res = await api.get<IRPFReportOut>(
        `/portfolios/${portfolioId}/irpf/${year}`,
        { params: { refresh } },
      )
      return toIRPFReportView(res.data)
    },
    enabled: !!portfolioId && !!year,
    staleTime: 1000 * 60 * 5,
  })
}

export function useIRPFCanonicalAnnualAssessment(
  portfolioId: number | null,
  year: number | null,
) {
  return useQuery<IRPFCanonicalAnnualAssessment>({
    queryKey: ['irpf-canonical-annual-assessment', portfolioId, year],
    queryFn: async () => {
      const res = await api.get<IRPFCanonicalAnnualAssessment>(
        `/portfolios/${portfolioId}/irpf/${year}/canonical`,
      )
      return res.data
    },
    enabled: !!portfolioId && !!year,
    staleTime: 1000 * 60 * 5,
  })
}

export function useIRPFCanonicalAssetsAssessment(
  portfolioId: number | null,
  year: number | null,
) {
  return useQuery<IRPFCanonicalAssetsAssessment>({
    queryKey: ['irpf-canonical-assets-assessment', portfolioId, year],
    queryFn: async () => {
      const res = await api.get<IRPFCanonicalAssetsAssessment>(
        `/portfolios/${portfolioId}/irpf/${year}/canonical/assets`,
      )
      return res.data
    },
    enabled: !!portfolioId && !!year,
    staleTime: 1000 * 60 * 5,
  })
}

export function useIRPFCanonicalCapitalGainsAssessment(
  portfolioId: number | null,
  year: number | null,
) {
  return useQuery<IRPFCanonicalCapitalGainsAssessment>({
    queryKey: ['irpf-canonical-capital-gains-assessment', portfolioId, year],
    queryFn: async () => {
      const res = await api.get<IRPFCanonicalCapitalGainsAssessment>(
        `/portfolios/${portfolioId}/irpf/${year}/canonical/capital-gains`,
      )
      return res.data
    },
    enabled: !!portfolioId && !!year,
    staleTime: 1000 * 60 * 5,
  })
}

export function useIRPFCanonicalIncomeAssessment(
  portfolioId: number | null,
  year: number | null,
) {
  return useQuery<IRPFCanonicalIncomeAssessment>({
    queryKey: ['irpf-canonical-income-assessment', portfolioId, year],
    queryFn: async () => {
      const res = await api.get<IRPFCanonicalIncomeAssessment>(
        `/portfolios/${portfolioId}/irpf/${year}/canonical/income`,
      )
      return res.data
    },
    enabled: !!portfolioId && !!year,
    staleTime: 1000 * 60 * 5,
  })
}
