import { describe, expect, it } from 'vitest'

import { buildPatrimonioChartData } from './PatrimonioBarChart'


describe('buildPatrimonioChartData', () => {
  it('derives patrimonio, applied capital and a negative capital result', () => {
    const [point] = buildPatrimonioChartData([
      {
        date: '2026-07-31',
        period: '2026-07',
        value: 20739.67,
        invested: 22149.25,
        capital_result: -1409.58,
        accumulated_return_pct: 8.7654,
        return_is_estimated: true,
        has_partial_prices: false,
        history_source: 'portfolio_snapshot',
      },
    ])

    expect(point).toEqual({
      name: '07/26',
      date: '2026-07-31',
      patrimonio: 20739.67,
      aplicado: 22149.25,
      resultado: -1409.58,
      twr: 8.7654,
      partial: false,
      estimated: true,
      source: 'portfolio_snapshot',
    })
  })

  it('derives capital result when the backend omits the convenience field', () => {
    const [point] = buildPatrimonioChartData([
      {
        date: '2026-06-30',
        value: 1250,
        invested: 1000,
      },
    ])

    expect(point.resultado).toBe(250)
    expect(point.twr).toBeNull()
    expect(point.source).toBe('unknown')
  })

  it('preserves zero TWR instead of treating it as missing', () => {
    const [point] = buildPatrimonioChartData([
      {
        date: '2026-05-30',
        value: 1000,
        invested: 1000,
        accumulated_return_pct: 0,
        history_source: 'db_derived_class_history',
      },
    ])

    expect(point.twr).toBe(0)
    expect(point.source).toBe('db_derived_class_history')
  })
})
