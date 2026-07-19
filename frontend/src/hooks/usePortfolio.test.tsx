import type { PropsWithChildren } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import api from '@/services/api'
import { makePortfolioSummary } from '@/test/fixtures/portfolioSummary'
import {
  parsePortfolioSummary,
  usePositions,
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

const validSummary = makePortfolioSummary()

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
