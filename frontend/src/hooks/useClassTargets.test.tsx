import type { PropsWithChildren } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import api from '@/services/api'
import { useDeleteClassTarget, useUpsertClassTarget } from './useClassTargets'

vi.mock('@/services/api', () => ({
  default: {
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
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

describe('useClassTargets mutations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses the canonical class-targets route when saving a target', async () => {
    vi.mocked(api.put).mockResolvedValue({ data: { asset_type: 'FII', target_pct: 25 } })
    const { result } = renderHook(() => useUpsertClassTarget(46), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.mutateAsync({ asset_type: 'FII', target_pct: 25 })
    })

    expect(api.put).toHaveBeenCalledWith(
      '/portfolios/46/class-targets/FII',
      { asset_type: 'FII', target_pct: 25 }
    )
  })

  it('uses the canonical class-targets route when deleting a target', async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined })
    const { result } = renderHook(() => useDeleteClassTarget(46), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.mutateAsync('FII')
    })

    expect(api.delete).toHaveBeenCalledWith('/portfolios/46/class-targets/FII')
  })
})
