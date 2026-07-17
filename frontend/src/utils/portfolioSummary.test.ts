import { describe, expect, it } from 'vitest'

import {
  formatReferenceDate,
  mapPortfolioSummaryMetrics,
} from './portfolioSummary'

describe('mapPortfolioSummaryMetrics', () => {
  it('maps intraday valuation and closed performance metadata separately', () => {
    const metrics = mapPortfolioSummaryMetrics({
      total_patrimonio: 12_800,
      total_investido: 10_200,
      lucro_total: 3_600,
      variacao_valor: 2_600,
      variacao_percentual: 25.4902,
      rentabilidade_total: 9.8765,
      rentabilidade_diaria: -0.123456,
      dividendos_recebidos_12m: 180,
      total_proventos: 700,
      valuation_mode: 'intraday',
      valuation_updated_at: '2026-07-16T14:30:00+00:00',
      performance_as_of: '2026-07-15',
      proventos_as_of: '2026-07-16',
      rentabilidade_source: 'snapshot_twr',
      return_is_estimated: true,
    })

    expect(metrics.patrimonio).toBe(12_800)
    expect(metrics.variacaoValor).toBe(2_600)
    expect(metrics.rentabilidadePct).toBe(9.8765)
    expect(metrics.rentabilidadeDiariaPct).toBe(-0.123456)
    expect(metrics.valuationMode).toBe('intraday')
    expect(metrics.performanceAsOf).toBe('2026-07-15')
    expect(metrics.proventosAsOf).toBe('2026-07-16')
    expect(metrics.rentabilidadeSource).toBe('snapshot_twr')
    expect(metrics.returnIsEstimated).toBe(true)
  })

  it('keeps absent daily return distinct from zero', () => {
    expect(mapPortfolioSummaryMetrics({ rentabilidade_diaria: null }).rentabilidadeDiariaPct).toBeNull()
    expect(mapPortfolioSummaryMetrics({ rentabilidade_diaria: 0 }).rentabilidadeDiariaPct).toBe(0)
  })

  it('normalizes invalid numeric values without using legacy aliases', () => {
    const metrics = mapPortfolioSummaryMetrics({
      total_patrimonio: Number.NaN,
      total_investido: null,
    })

    expect(metrics.patrimonio).toBe(0)
    expect(metrics.aportado).toBe(0)
  })
})

describe('formatReferenceDate', () => {
  it('formats canonical date-only references in pt-BR', () => {
    expect(formatReferenceDate('2026-07-15')).toBe('15/07/2026')
  })

  it('returns null for absent or invalid references', () => {
    expect(formatReferenceDate(null)).toBeNull()
    expect(formatReferenceDate('invalid-date')).toBeNull()
  })
})
