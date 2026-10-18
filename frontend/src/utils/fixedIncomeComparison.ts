import { FixedIncomeProductType, isFixedIncomeProductTaxExempt } from './fixedIncomeTaxTreatment'

export type FixedIncomeComparisonInput = {
  principal: number
  daysToMaturity: number
  firstProductType: FixedIncomeProductType
  firstAnnualEffectiveRatePercent: number
  secondProductType: FixedIncomeProductType
  secondAnnualEffectiveRatePercent: number
}

export type FixedIncomeScenario = {
  productType: FixedIncomeProductType
  grossMaturityValue: number
  grossReturn: number
  incomeTaxRate: number
  incomeTax: number
  netMaturityValue: number
  netEffectiveAnnualRatePercent: number
}

export type FixedIncomeComparison = {
  daysToMaturity: number
  first: FixedIncomeScenario
  second: FixedIncomeScenario
  firstEquivalentRateForSecondScenario: number
}

export function fixedIncomeIncomeTaxRate(days: number): number {
  if (!Number.isInteger(days) || days < 1) {
    throw new RangeError('O prazo deve ser um número inteiro positivo de dias.')
  }
  if (days <= 180) return 0.225
  if (days <= 360) return 0.20
  if (days <= 720) return 0.175
  return 0.15
}

function validateAnnualRate(value: number): void {
  if (!Number.isFinite(value) || value <= -100 || value > 1000) {
    throw new RangeError('A taxa efetiva anual deve ser maior que -100% e até 1.000%.')
  }
}

function calculateScenario(
  principal: number,
  days: number,
  productType: FixedIncomeProductType,
  annualRatePercent: number,
  incomeTaxRate: number,
): FixedIncomeScenario {
  const grossMaturityValue = principal * Math.pow(1 + annualRatePercent / 100, days / 365)
  if (!Number.isFinite(grossMaturityValue)) {
    throw new RangeError('A simulação excedeu o limite numérico suportado.')
  }

  const grossReturn = grossMaturityValue - principal
  const incomeTax = Math.max(grossReturn, 0) * incomeTaxRate
  const netMaturityValue = grossMaturityValue - incomeTax
  const netEffectiveAnnualRatePercent = principal > 0
    ? (Math.pow(netMaturityValue / principal, 365 / days) - 1) * 100
    : Number.NaN

  return {
    productType,
    grossMaturityValue,
    grossReturn,
    incomeTaxRate,
    incomeTax,
    netMaturityValue,
    netEffectiveAnnualRatePercent,
  }
}

export function calculateFixedIncomeComparison({
  principal,
  daysToMaturity,
  firstProductType,
  firstAnnualEffectiveRatePercent,
  secondProductType,
  secondAnnualEffectiveRatePercent,
}: FixedIncomeComparisonInput): FixedIncomeComparison {
  if (!Number.isFinite(principal) || principal <= 0 || principal > 1_000_000_000) {
    throw new RangeError('O valor aplicado deve ser maior que R$ 0 e até R$ 1 bilhão.')
  }
  if (!Number.isInteger(daysToMaturity) || daysToMaturity < 30 || daysToMaturity > 36_500) {
    throw new RangeError('O prazo deve estar entre 30 e 36.500 dias para excluir a estimativa de IOF.')
  }
  validateAnnualRate(firstAnnualEffectiveRatePercent)
  validateAnnualRate(secondAnnualEffectiveRatePercent)

  const progressiveRate = fixedIncomeIncomeTaxRate(daysToMaturity)
  const firstTaxRate = isFixedIncomeProductTaxExempt(firstProductType) ? 0 : progressiveRate
  const secondTaxRate = isFixedIncomeProductTaxExempt(secondProductType) ? 0 : progressiveRate
  const first = calculateScenario(
    principal,
    daysToMaturity,
    firstProductType,
    firstAnnualEffectiveRatePercent,
    firstTaxRate,
  )
  const second = calculateScenario(
    principal,
    daysToMaturity,
    secondProductType,
    secondAnnualEffectiveRatePercent,
    secondTaxRate,
  )

  const targetFactor = second.netMaturityValue / principal
  const equivalentGrossFactor = targetFactor >= 1
    ? 1 + ((targetFactor - 1) / (1 - firstTaxRate))
    : targetFactor
  const firstEquivalentRateForSecondScenario =
    (Math.pow(equivalentGrossFactor, 365 / daysToMaturity) - 1) * 100

  return {
    daysToMaturity,
    first,
    second,
    firstEquivalentRateForSecondScenario,
  }
}
