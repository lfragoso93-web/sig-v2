import type { PropsWithChildren } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import api from '@/services/api'
import {
  parsePortfolioSummary,
  usePositions,
  type PortfolioSummary,
} from './usePortfolio'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
  },
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return function Wrapper({ children }: PropsWithChildren) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }
}

describe('usePositions', () => {
  it('mantém o estado de carregamento até a primeira resposta real', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => undefined))

    const { result } = renderHook(() => usePositions(46), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })
})

const validSummary: PortfolioSummary = {
  summary_version: 'summary.v2',
  total_patrimonio: 900,
  total_investido: 1000,
  lucro_total: -75,
  variacao_valor: -100,
  variacao_percentual: -10,
  ganho_nao_realizado: -100,
  ganho_realizado: 5,
  rentabilidade_total: -7.5,
  rentabilidade_acumulada: -7.5,
  rentabilidade_diaria: null,
  rentabilidade_source: 'snapshot_twr',
  dividendos_recebidos_12m: 20,
  total_proventos: 20,
  proventos_as_of: '2026-07-18',
  proventos_source: 'received_cash_dividends',
  has_partial_prices: false,
  assets_without_price: [],
  price_assets_total: 1,
  price_assets_covered: 1,
  price_coverage_pct: 100,
  usd_brl_rate: 5.5,
  valuation_mode: 'intraday',
  valuation_updated_at: '2026-07-18T12:00:00Z',
  performance_as_of: '2026-07-17',
  snapshot_id: 42,
  snapshot_date: '2026-07-17',
  summary_source: 'intraday_valuation_with_snapshot_twr',
  return_is_estimated: false,
  is_reconciled: true,
  reconciliation: {},
}

describe('parsePortfolioSummary', () => {
  it('preserva valores negativos do contrato válido', () => {
    expect(parsePortfolioSummary(validSummary).lucro_total).toBe(-75)
  })

  it('rejeita campo financeiro obrigatório ausente', () => {
    const { total_patrimonio: _missing, ...invalid } = validSummary

    expect(() => parsePortfolioSummary(invalid)).toThrow('total_patrimonio')
  })

  it('rejeita tipo financeiro inválido', () => {
    expect(() => parsePortfolioSummary({
      ...validSummary,
      total_patrimonio: '900',
    })).toThrow('total_patrimonio')
  })

  it('rejeita campo adicional fora de summary.v2', () => {
    expect(() => parsePortfolioSummary({
      ...validSummary,
      rentabilidade_legada: 10,
    })).toThrow('rentabilidade_legada')
  })
})
