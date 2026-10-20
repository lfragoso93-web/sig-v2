import { describe, expect, it } from 'vitest'
import { calculateFixedIncomeComparison, fixedIncomeIncomeTaxRate } from './fixedIncomeComparison'

describe('fixedIncomeIncomeTaxRate', () => {
  it.each([
    [180, 0.225],
    [181, 0.20],
    [360, 0.20],
    [361, 0.175],
    [720, 0.175],
    [721, 0.15],
  ])('uses the legal income-tax band for %i days', (days, rate) => {
    expect(fixedIncomeIncomeTaxRate(days)).toBe(rate)
  })

  it('rejects non-positive or fractional durations', () => {
    expect(() => fixedIncomeIncomeTaxRate(0)).toThrow(RangeError)
    expect(() => fixedIncomeIncomeTaxRate(30.5)).toThrow(RangeError)
  })
})

describe('calculateFixedIncomeComparison', () => {
  const base = {
    principal: 10_000,
    daysToMaturity: 365,
    firstProductType: 'CDB' as const,
    firstAnnualEffectiveRatePercent: 12,
    secondProductType: 'LCI' as const,
    secondAnnualEffectiveRatePercent: 10,
  }

  it('calculates gross, tax, net value, and net annualized returns', () => {
    const result = calculateFixedIncomeComparison(base)

    expect(result.first.grossMaturityValue).toBeCloseTo(11_200)
    expect(result.first.incomeTaxRate).toBe(0.175)
    expect(result.first.incomeTax).toBeCloseTo(210)
    expect(result.first.netMaturityValue).toBeCloseTo(10_990)
    expect(result.first.netEffectiveAnnualRatePercent).toBeCloseTo(9.9)
    expect(result.second.netMaturityValue).toBeCloseTo(11_000)
  })

  it('returns the first-title rate that matches the second-title net value', () => {
    const result = calculateFixedIncomeComparison(base)
    const equivalent = calculateFixedIncomeComparison({
      ...base,
      firstAnnualEffectiveRatePercent: result.firstEquivalentRateForSecondScenario,
    })

    expect(equivalent.first.netMaturityValue).toBeCloseTo(result.second.netMaturityValue)
  })

  it('does not charge income tax on a negative taxable gross return', () => {
    const result = calculateFixedIncomeComparison({
      ...base,
      firstAnnualEffectiveRatePercent: -10,
    })

    expect(result.first.grossReturn).toBeLessThan(0)
    expect(result.first.incomeTax).toBe(0)
    expect(result.first.netMaturityValue).toBe(result.first.grossMaturityValue)
  })

  it('rejects invalid principal, term, and annual rates', () => {
    expect(() => calculateFixedIncomeComparison({ ...base, principal: 0 })).toThrow(RangeError)
    expect(() => calculateFixedIncomeComparison({ ...base, daysToMaturity: 29 })).toThrow(RangeError)
    expect(() => calculateFixedIncomeComparison({ ...base, daysToMaturity: 30.5 })).toThrow(RangeError)
    expect(() => calculateFixedIncomeComparison({ ...base, secondAnnualEffectiveRatePercent: -100 })).toThrow(RangeError)
  })
})
