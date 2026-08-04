import { describe, expect, it } from 'vitest'

import pageSource from './IRPFPage.tsx?raw'
import hookSource from '@/hooks/useIRPF.ts?raw'

describe('IRPFPage portfolio scope contract', () => {
  it('deriva consultas e downloads da carteira selecionada', () => {
    expect(pageSource).toContain('selectedPortfolioId')
    expect(pageSource).toContain('useIRPFAnos(portfolioId)')
    expect(pageSource).toContain('useIRPFReport(portfolioId, selectedYear, refreshKey)')
    expect(pageSource).toContain('/portfolios/${portfolioId}/irpf/${selectedYear}/pdf')
    expect(pageSource).toContain('/portfolios/${portfolioId}/irpf/${selectedYear}/csv')
  })

  it('reconcilia o ano e limpa estado visual quando a carteira muda', () => {
    expect(pageSource).toContain('reconcileIRPFYear(current, anos, fallbackYear)')
    expect(pageSource).toContain("setActiveTab('resumo')")
    expect(pageSource).toContain('setRefreshKey(false)')
    expect(pageSource).toContain('[portfolioId, anos, fallbackYear]')
  })

  it('mantém carteira e ano nas chaves do cache de IRPF', () => {
    expect(hookSource).toContain("queryKey: ['irpf-anos', portfolioId]")
    expect(hookSource).toContain("queryKey: ['irpf-report', portfolioId, year, refresh]")
  })
})
