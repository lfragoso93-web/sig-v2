export interface PortfolioSummaryLike {
  total_patrimonio?: number | null
  total_investido?: number | null
  lucro_total?: number | null
  variacao_valor?: number | null
  variacao_percentual?: number | null
  rentabilidade_total?: number | null
  dividendos_recebidos_12m?: number | null
  total_proventos?: number | null
  has_partial_prices?: boolean | null
  assets_without_price?: string[] | null
}

export interface PortfolioSummaryMetrics {
  patrimonio: number
  aportado: number
  lucroTotal: number
  variacaoValor: number
  variacaoPct: number
  rentabilidadePct: number
  proventos12m: number
  proventosTotal: number
  hasPartialPrices: boolean
  assetsWithoutPrice: string[]
}

export function safeNum(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

/**
 * Mapeia exclusivamente o contrato consolidado usado por Patrimônio.
 * Não usa fallbacks legados como current_value/total_gain para evitar divergência
 * entre Resumo e Patrimônio.
 */
export function mapPortfolioSummaryMetrics(summary?: PortfolioSummaryLike | null): PortfolioSummaryMetrics {
  return {
    patrimonio: safeNum(summary?.total_patrimonio),
    aportado: safeNum(summary?.total_investido),
    lucroTotal: safeNum(summary?.lucro_total),
    variacaoValor: safeNum(summary?.variacao_valor),
    variacaoPct: safeNum(summary?.variacao_percentual),
    rentabilidadePct: safeNum(summary?.rentabilidade_total),
    proventos12m: safeNum(summary?.dividendos_recebidos_12m),
    proventosTotal: safeNum(summary?.total_proventos),
    hasPartialPrices: Boolean(summary?.has_partial_prices),
    assetsWithoutPrice: summary?.assets_without_price ?? [],
  }
}
