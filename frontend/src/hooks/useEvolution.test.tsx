import type { PropsWithChildren } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import api from '@/services/api'
import {
  PERIOD_DAYS,
  PERIOD_MONTHS,
  isDailyPeriod,
  useClassDailyEvolution,
  useClassMonthlyEvolution,
  useDailyEvolution,
  useMonthlyEvolution,
} from './useEvolution'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
  },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

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

describe('canonical monthly evolution hooks', () => {
  it('mapeia todos os períodos sem aproximação no componente', () => {
    expect(PERIOD_MONTHS).toEqual({
      '7d': 1,
      '15d': 1,
      '30d': 1,
      '6m': 6,
      '12m': 12,
      '24m': 24,
      'all': 0,
    })
    expect(PERIOD_DAYS['7d']).toBe(7)
    expect(PERIOD_DAYS['15d']).toBe(15)
    expect(PERIOD_DAYS['30d']).toBe(30)
    expect(isDailyPeriod('7d')).toBe(true)
    expect(isDailyPeriod('15d')).toBe(true)
    expect(isDailyPeriod('30d')).toBe(true)
    expect(isDailyPeriod('6m')).toBe(false)
  })

  it('mantém loading até a primeira resposta consolidada', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => undefined))

    const { result } = renderHook(() => useMonthlyEvolution(46, '12m'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('não converte loading diário em uma série vazia', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => undefined))

    const { result } = renderHook(() => useDailyEvolution(46, '6m'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('não converte loading diário por classe em uma série vazia', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => undefined))

    const { result } = renderHook(
      () => useClassDailyEvolution(46, 'ACAO', '6m'),
      { wrapper: createWrapper() },
    )

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('não consulta evolução por classe sem classe canônica disponível', () => {
    const { result } = renderHook(
      () => useClassMonthlyEvolution(46, null, '12m'),
      { wrapper: createWrapper() },
    )

    expect(result.current.fetchStatus).toBe('idle')
    expect(
      vi.mocked(api.get).mock.calls.some(([url]) => String(url).includes('/classes/')),
    ).toBe(false)
  })
})
