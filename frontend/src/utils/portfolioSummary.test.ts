import { describe, expect, it } from 'vitest'

import { makePortfolioSummary } from '@/test/fixtures/portfolioSummary'
import {
  formatReferenceDate,
  getPortfolioReturnPresentation,
  mapPortfolioSummaryMetrics,
} from './portfolioSummary'

describe('portfolioSummary', () => {
  it('projeta os valores canônicos sem alterar sinais', () => {
    const metrics = mapPortfolioSummaryMetrics(makePortfolioSummary())

    expect(metrics).toMatchObject({
      patrimonio: 900,
      aportado: 1000,
      lucroTotal: -75,
      variacaoValor: -100,
      variacaoPct: -10,
      ganhoNaoRealizado: -100,
      ganhoRealizado: 5,
      rentabilidadePct: -7.5,
      proventos12m: 20,
      proventosTotal: 25,
    })
  })

  it('identifica TWR fechado', () => {
    const metrics = mapPortfolioSummaryMetrics(makePortfolioSummary())

    expect(getPortfolioReturnPresentation(metrics)).toEqual({
      isEstimated: false,
      label: 'Rentabilidade (TWR)',
    })
  })

  it('não apresenta fallback do valuation como TWR', () => {
    const metrics = mapPortfolioSummaryMetrics(makePortfolioSummary({
      rentabilidade_source: 'valuation_fallback',
      return_is_estimated: true,
      summary_source: 'valuation_fallback',
    }))

    expect(getPortfolioReturnPresentation(metrics)).toEqual({
      isEstimated: true,
      label: 'Retorno estimado',
    })
  })
})

describe('formatReferenceDate', () => {
  it('formata referências canônicas em pt-BR', () => {
    expect(formatReferenceDate('2026-07-15')).toBe('15/07/2026')
  })

  it('mantém ausência e data inválida distintas', () => {
    expect(formatReferenceDate(null)).toBeNull()
    expect(formatReferenceDate('invalid-date')).toBeNull()
  })
})
