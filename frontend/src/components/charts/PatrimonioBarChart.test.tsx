import { describe, expect, it } from 'vitest'

import { buildPatrimonioChartData, getSymmetricAxisLimit } from './PatrimonioBarChart'


describe('buildPatrimonioChartData', () => {
  it('preserves a negative capital result below zero', () => {
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

  it('preserves a positive result above zero', () => {
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

  it('preserves zero TWR and zero capital result', () => {
    const [point] = buildPatrimonioChartData([
      {
        date: '2026-05-30',
        value: 1000,
        invested: 1000,
        accumulated_return_pct: 0,
        history_source: 'db_derived_class_history',
      },
    ])

    expect(point.resultado).toBe(0)
    expect(point.twr).toBe(0)
    expect(point.source).toBe('db_derived_class_history')
  })
})

describe('getSymmetricAxisLimit', () => {
  it('creates the same distance above and below zero', () => {
    const points = buildPatrimonioChartData([
      {
        date: '2026-06-30',
        value: 19486.43,
        invested: 21338.20,
        capital_result: -1851.77,
      },
      {
        date: '2026-07-31',
        value: 23000,
        invested: 21500,
        capital_result: 1500,
      },
    ])

    const limit = getSymmetricAxisLimit(points)

    expect(limit).toBeGreaterThan(23000)
    expect([-limit, limit]).toEqual([-limit, limit])
  })

  it('uses a safe domain for a zeroed portfolio', () => {
    const points = buildPatrimonioChartData([
      { date: '2026-07-31', value: 0, invested: 0 },
    ])

    expect(getSymmetricAxisLimit(points)).toBe(1)
  })
})
