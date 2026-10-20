export type IncomeProjectionPoint = {
  month: number
  invested: number
  projectedBalance: number
  projectedReturn: number
}

export type IncomeProjection = {
  monthlyEffectiveRate: number
  totalInvested: number
  projectedBalance: number
  projectedReturn: number
  points: IncomeProjectionPoint[]
}

export type IncomeProjectionInput = {
  initialContribution: number
  monthlyContribution: number
  annualEffectiveRatePercent: number
  months: number
}

export function calculateIncomeProjection({
  initialContribution,
  monthlyContribution,
  annualEffectiveRatePercent,
  months,
}: IncomeProjectionInput): IncomeProjection {
  if (!Number.isFinite(initialContribution) || initialContribution < 0 || initialContribution > 1_000_000_000) {
    throw new RangeError('O aporte inicial deve estar entre R$ 0 e R$ 1 bilhão.')
  }
  if (!Number.isFinite(monthlyContribution) || monthlyContribution < 0 || monthlyContribution > 1_000_000_000) {
    throw new RangeError('O aporte mensal deve estar entre R$ 0 e R$ 1 bilhão.')
  }
  if (
    !Number.isFinite(annualEffectiveRatePercent)
    || annualEffectiveRatePercent <= -100
    || annualEffectiveRatePercent > 1000
  ) {
    throw new RangeError('A taxa anual deve ser maior que -100% e não pode ultrapassar 1.000%.')
  }
  if (!Number.isInteger(months) || months < 1 || months > 600) {
    throw new RangeError('O prazo deve ser um número inteiro entre 1 e 600 meses.')
  }

  const annualFactor = 1 + annualEffectiveRatePercent / 100
  const monthlyEffectiveRate = Math.pow(annualFactor, 1 / 12) - 1
  let balance = initialContribution
  const points: IncomeProjectionPoint[] = [{
    month: 0,
    invested: initialContribution,
    projectedBalance: balance,
    projectedReturn: 0,
  }]

  for (let month = 1; month <= months; month += 1) {
    // O rendimento incide primeiro; o aporte mensal ocorre no fim do mês.
    balance = balance * (1 + monthlyEffectiveRate) + monthlyContribution
    if (!Number.isFinite(balance)) {
      throw new RangeError('A projeção excedeu o limite numérico suportado.')
    }
    const invested = initialContribution + monthlyContribution * month
    points.push({
      month,
      invested,
      projectedBalance: balance,
      projectedReturn: balance - invested,
    })
  }

  const finalPoint = points[points.length - 1]
  return {
    monthlyEffectiveRate,
    totalInvested: finalPoint.invested,
    projectedBalance: finalPoint.projectedBalance,
    projectedReturn: finalPoint.projectedReturn,
    points,
  }
}
