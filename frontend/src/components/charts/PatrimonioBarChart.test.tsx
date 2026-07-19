import { describe, expect, it } from 'vitest'

import { buildPatrimonioChartData, getSymmetricAxisLimit } from './PatrimonioBarChart'


describe('buildPatrimonioChartData', () => {
  it('places a negative capital result exclusively in the loss series', () => {
    const [point] = buildPatrimonioChartData([
      {
        date: '2026-07-31',
        period: '2026-07',
        market_value: 20739.67,
        cost_basis: 22149.25,
        unrealized_pnl: -1409.58,
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
      ganho: 0,
      perda: -1409.58,
      twr: 8.7654,
      partial: false,
      estimated: true,
      source: 'portfolio_snapshot',
    })
  })

  it('places a positive capital result exclusively in the gain series', () => {
    const [point] = buildPatrimonioChartData([
      {
        date: '2026-06-30',
        market_value: 1250,
        cost_basis: 1000,
        unrealized_pnl: 225,
      },
    ])

    expect(point.resultado).toBe(225)
    expect(point.ganho).toBe(225)
    expect(point.perda).toBe(0)
    expect(point.twr).toBeNull()
    expect(point.source).toBe('unknown')
  })

  it('preserves zero TWR and zero capital result', () => {
    const [point] = buildPatrimonioChartData([
      {
        date: '2026-05-30',
        market_value: 1000,
        cost_basis: 1000,
        unrealized_pnl: 0,
        accumulated_return_pct: 0,
        history_source: 'db_derived_class_history',
      },
    ])

    expect(point.resultado).toBe(0)
    expect(point.ganho).toBe(0)
    expect(point.perda).toBe(0)
    expect(point.twr).toBe(0)
    expect(point.source).toBe('db_derived_class_history')
  })
})

describe('getSymmetricAxisLimit', () => {
  it('covers the applied capital plus positive gain and the negative loss', () => {
    const points = buildPatrimonioChartData([
      {
        date: '2026-06-30',
        market_value: 19486.43,
        cost_basis: 21338.20,
        unrealized_pnl: -1851.77,
      },
      {
        date: '2026-07-31',
        market_value: 23000,
        cost_basis: 21500,
        unrealized_pnl: 1500,
      },
    ])

    const limit = getSymmetricAxisLimit(points)

    expect(limit).toBeGreaterThan(23000)
    expect(limit).toBeGreaterThan(1851.77)
  })

  it('uses a safe domain for a zeroed portfolio', () => {
    const points = buildPatrimonioChartData([
      { date: '2026-07-31', market_value: 0, cost_basis: 0, unrealized_pnl: 0 },
    ])

    expect(getSymmetricAxisLimit(points)).toBe(1)
  })
})
