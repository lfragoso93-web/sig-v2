export interface PortfolioSummaryLike {
  total_patrimonio?: number | null
  total_investido?: number | null
  lucro_total?: number | null
  variacao_valor?: number | null
  variacao_percentual?: number | null
  rentabilidade_total?: number | null
  rentabilidade_diaria?: number | null
  dividendos_recebidos_12m?: number | null
  total_proventos?: number | null
  has_partial_prices?: boolean | null
  assets_without_price?: string[] | null
  valuation_mode?: string | null
  valuation_updated_at?: string | null
  performance_as_of?: string | null
  proventos_as_of?: string | null
  rentabilidade_source?: string | null
  return_is_estimated?: boolean | null
}

export interface PortfolioSummaryMetrics {
  patrimonio: number
  aportado: number
  lucroTotal: number
  variacaoValor: number
  variacaoPct: number
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

export function safeNum(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
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
export function mapPortfolioSummaryMetrics(summary?: PortfolioSummaryLike | null): PortfolioSummaryMetrics {
  return {
    patrimonio: safeNum(summary?.total_patrimonio),
    aportado: safeNum(summary?.total_investido),
    lucroTotal: safeNum(summary?.lucro_total),
    variacaoValor: safeNum(summary?.variacao_valor),
    variacaoPct: safeNum(summary?.variacao_percentual),
    rentabilidadePct: safeNum(summary?.rentabilidade_total),
    rentabilidadeDiariaPct: summary?.rentabilidade_diaria == null
      ? null
      : safeNum(summary.rentabilidade_diaria),
    proventos12m: safeNum(summary?.dividendos_recebidos_12m),
    proventosTotal: safeNum(summary?.total_proventos),
    hasPartialPrices: Boolean(summary?.has_partial_prices),
    assetsWithoutPrice: summary?.assets_without_price ?? [],
    valuationMode: summary?.valuation_mode ?? null,
    valuationUpdatedAt: summary?.valuation_updated_at ?? null,
    performanceAsOf: summary?.performance_as_of ?? null,
    proventosAsOf: summary?.proventos_as_of ?? null,
    rentabilidadeSource: summary?.rentabilidade_source ?? null,
    returnIsEstimated: Boolean(summary?.return_is_estimated),
  }
}
