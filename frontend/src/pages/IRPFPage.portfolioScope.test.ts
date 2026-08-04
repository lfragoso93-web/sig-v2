import { describe, expect, it } from 'vitest'

import pageSource from './IRPFPage.tsx?raw'
import hookSource from '@/hooks/useIRPF.ts?raw'

describe('IRPFPage portfolio scope contract', () => {
  it('deriva consultas e downloads da carteira selecionada', () => {
    expect(pageSource).toContain('selectedPortfolioId')
    expect(pageSource).toContain('useIRPFAnos(portfolioId)')
    expect(pageSource).toContain('useIRPFCanonicalAnnualAssessment(portfolioId, selectedYear)')
    expect(pageSource).toContain('useIRPFCanonicalAssetsAssessment(portfolioId, selectedYear)')
    expect(pageSource).toContain('useIRPFCanonicalCapitalGainsAssessment(portfolioId, selectedYear)')
    expect(pageSource).toContain('useIRPFCanonicalIncomeAssessment(portfolioId, selectedYear)')
    expect(pageSource).not.toContain('useIRPFReport(')
    expect(pageSource).toContain('/portfolios/${portfolioId}/irpf/${selectedYear}/pdf')
    expect(pageSource).toContain('/portfolios/${portfolioId}/irpf/${selectedYear}/csv')
  })

  it('reconcilia o ano e limpa estado visual quando a carteira muda', () => {
    expect(pageSource).toContain('reconcileIRPFYear(current, anos, fallbackYear)')
    expect(pageSource).toContain("setActiveTab('resumo')")
    expect(pageSource).not.toContain('setRefreshKey')
    expect(pageSource).toContain('[portfolioId, anos, fallbackYear]')
  })

  it('mantém carteira e ano nas chaves canônicas do cache de IRPF', () => {
    expect(hookSource).toContain("queryKey: ['irpf-anos', portfolioId]")
    expect(hookSource).toContain("queryKey: ['irpf-canonical-annual', portfolioId, year]")
    expect(hookSource).toContain("queryKey: ['irpf-canonical-assets', portfolioId, year]")
    expect(hookSource).toContain("queryKey: ['irpf-canonical-capital-gains', portfolioId, year]")
    expect(hookSource).toContain("queryKey: ['irpf-canonical-income', portfolioId, year]")
  })
})
