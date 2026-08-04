import { describe, expect, it } from 'vitest'

import { reconcileIRPFYear } from './irpfYearSelection'

describe('reconcileIRPFYear', () => {
  it('preserva o ano atual quando ele existe na nova carteira', () => {
    expect(reconcileIRPFYear(2024, [2025, 2024, 2023], 2025)).toBe(2024)
  })

  it('seleciona o primeiro ano disponível quando o atual não existe', () => {
    expect(reconcileIRPFYear(2022, [2025, 2024, 2023], 2025)).toBe(2025)
  })

  it('usa o fallback quando a carteira não possui anos', () => {
    expect(reconcileIRPFYear(2024, [], 2025)).toBe(2025)
    expect(reconcileIRPFYear(2024, undefined, 2025)).toBe(2025)
  })
})
