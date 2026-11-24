import { describe, expect, it } from 'vitest'

import { PERIOD_DAYS, PERIOD_MONTHS } from './useEvolution'


describe('patrimonio evolution periods', () => {
  it('uses zero as the explicit full-history contract', () => {
    expect(PERIOD_DAYS.all).toBe(0)
    expect(PERIOD_MONTHS.all).toBe(0)
  })

  it('keeps bounded periods deterministic', () => {
    expect(PERIOD_DAYS['7d']).toBe(7)
    expect(PERIOD_DAYS['15d']).toBe(15)
    expect(PERIOD_DAYS['30d']).toBe(30)
    expect(PERIOD_DAYS['12m']).toBe(365)
    expect(PERIOD_MONTHS['12m']).toBe(12)
    expect(PERIOD_DAYS['24m']).toBe(730)
    expect(PERIOD_MONTHS['24m']).toBe(24)
  })
})
