/**
 * Hook para buscar dados do módulo IRPF.
 * Expõe: useIRPFAnos, useIRPFReport
 */
import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'
import type { IRPFReportOut } from '@/types/irpf'

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
