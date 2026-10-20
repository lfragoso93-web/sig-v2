import { describe, expect, it } from 'vitest'
import { calculateIncomeProjection } from './incomeProjection'

describe('calculateIncomeProjection', () => {
  it('projects monthly contributions at zero return', () => {
    const result = calculateIncomeProjection({
      initialContribution: 500,
      monthlyContribution: 100,
      annualEffectiveRatePercent: 0,
      months: 12,
    })

    expect(result.totalInvested).toBe(1700)
    expect(result.projectedBalance).toBe(1700)
    expect(result.projectedReturn).toBe(0)
    expect(result.points).toHaveLength(13)
  })

  it('converts an effective annual rate into an equivalent monthly rate', () => {
    const result = calculateIncomeProjection({
      initialContribution: 1000,
      monthlyContribution: 0,
      annualEffectiveRatePercent: 100,
      months: 12,
    })

    expect(result.monthlyEffectiveRate).toBeCloseTo(Math.pow(2, 1 / 12) - 1)
    expect(result.projectedBalance).toBeCloseTo(2000)
    expect(result.totalInvested).toBe(1000)
    expect(result.projectedReturn).toBeCloseTo(1000)
  })

  it('adds each monthly contribution after that month return', () => {
    const result = calculateIncomeProjection({
      initialContribution: 0,
      monthlyContribution: 100,
      annualEffectiveRatePercent: 21.9391,
      months: 2,
    })

    expect(result.monthlyEffectiveRate).toBeCloseTo(0.0166667, 5)
    expect(result.points[1].projectedBalance).toBeCloseTo(100)
    expect(result.projectedBalance).toBeCloseTo(201.66667, 4)
  })

  it('rejects invalid contributions, rates, and horizons', () => {
    const base = {
      initialContribution: 0,
      monthlyContribution: 0,
      annualEffectiveRatePercent: 0,
      months: 12,
    }

    expect(() => calculateIncomeProjection({ ...base, initialContribution: -1 })).toThrow(RangeError)
    expect(() => calculateIncomeProjection({ ...base, monthlyContribution: 1_000_000_001 })).toThrow(RangeError)
    expect(() => calculateIncomeProjection({ ...base, annualEffectiveRatePercent: -100 })).toThrow(RangeError)
    expect(() => calculateIncomeProjection({ ...base, months: 600.5 })).toThrow(RangeError)
  })
})
