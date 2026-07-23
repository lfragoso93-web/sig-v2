import type { PortfolioSummary } from '@/hooks/usePortfolio'

export interface PortfolioSummaryMetrics {
  patrimonio: number
  aportado: number
  lucroTotal: number
  variacaoValor: number
  variacaoPct: number
  ganhoNaoRealizado: number
  ganhoRealizado: number
  rentabilidadePct: number
  rentabilidadeDiariaPct: number | null
  proventos12m: number
  proventosTotal: number
  hasPartialPrices: boolean
  assetsWithoutPrice: string[]
  valuationMode: string | null
  valuationUpdatedAt: string | null
  performanceAsOf: string | null
  proventosAsOf: string | null
  rentabilidadeSource: string | null
  returnIsEstimated: boolean
}

export function formatReferenceDate(value?: string | null): string | null {
  if (!value) return null
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value)
  const parsed = new Date(dateOnly ? `${value}T12:00:00` : value)
  if (Number.isNaN(parsed.getTime())) return null
  return new Intl.DateTimeFormat('pt-BR', dateOnly
    ? { day: '2-digit', month: '2-digit', year: 'numeric' }
    : { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }
  ).format(parsed)
}

/**
 * Mapeia exclusivamente o contrato consolidado usado pelo Resumo.
 * Valores intradiários e performance fechada mantêm referências temporais distintas.
 */
export function mapPortfolioSummaryMetrics(summary: PortfolioSummary): PortfolioSummaryMetrics {
  return {
    patrimonio: summary.total_patrimonio ?? 0,
    aportado: summary.total_investido ?? 0,
    lucroTotal: summary.lucro_total ?? 0,
    variacaoValor: summary.variacao_valor ?? 0,
    variacaoPct: summary.variacao_percentual ?? 0,
    ganhoNaoRealizado: summary.ganho_nao_realizado ?? 0,
    ganhoRealizado: summary.ganho_realizado ?? 0,
    rentabilidadePct: summary.rentabilidade_total ?? 0,
    rentabilidadeDiariaPct: summary.rentabilidade_diaria ?? null,
    proventos12m: summary.dividendos_recebidos_12m ?? 0,
    proventosTotal: summary.total_proventos ?? 0,
    hasPartialPrices: summary.has_partial_prices ?? false,
    assetsWithoutPrice: summary.assets_without_price ?? [],
    valuationMode: summary.valuation_mode ?? null,
    valuationUpdatedAt: summary.valuation_updated_at ?? null,
    performanceAsOf: summary.performance_as_of ?? null,
    proventosAsOf: summary.proventos_as_of ?? null,
    rentabilidadeSource: summary.rentabilidade_source ?? null,
    returnIsEstimated: summary.return_is_estimated ?? false,
  }
}

export function getPortfolioReturnPresentation(
  metrics: PortfolioSummaryMetrics | null,
): { isEstimated: boolean; label: 'Retorno estimado' | 'Rentabilidade (TWR)' } {
  const isEstimated = Boolean(
    metrics?.returnIsEstimated || metrics?.rentabilidadeSource === 'valuation_fallback',
  )
  return {
    isEstimated,
    label: isEstimated ? 'Retorno estimado' : 'Rentabilidade (TWR)',
  }
}
