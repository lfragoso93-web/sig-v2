import { describe, expect, it } from 'vitest'
import { mapPortfolioSummaryMetrics } from '../portfolioSummary'

describe('mapPortfolioSummaryMetrics', () => {
  it('preserves negative current variation and total profitability', () => {
    const metrics = mapPortfolioSummaryMetrics({
      total_patrimonio: 900,
      total_investido: 1000,
      lucro_total: -75,
      variacao_valor: -100,
      variacao_percentual: -10,
      rentabilidade_total: -7.5,
      dividendos_recebidos_12m: 25,
      total_proventos: 25,
    })

    expect(metrics.patrimonio).toBe(900)
    expect(metrics.aportado).toBe(1000)
    expect(metrics.variacaoValor).toBe(-100)
    expect(metrics.variacaoPct).toBe(-10)
    expect(metrics.rentabilidadePct).toBe(-7.5)
    expect(metrics.lucroTotal).toBe(-75)
  })

  it('does not fallback to legacy summary fields', () => {
    const metrics = mapPortfolioSummaryMetrics({
      // Campos legados simulados propositalmente via cast.
      current_value: 9999,
      total_gain: 8888,
    } as any)

    expect(metrics.patrimonio).toBe(0)
    expect(metrics.variacaoValor).toBe(0)
    expect(metrics.lucroTotal).toBe(0)
  })

  it('normalizes partial price metadata', () => {
    const metrics = mapPortfolioSummaryMetrics({
      has_partial_prices: true,
      assets_without_price: ['ABC3', 'XYZ11'],
    })

    expect(metrics.hasPartialPrices).toBe(true)
    expect(metrics.assetsWithoutPrice).toEqual(['ABC3', 'XYZ11'])
  })
})
