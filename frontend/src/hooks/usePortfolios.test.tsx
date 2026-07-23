import type { PropsWithChildren } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { patch } = vi.hoisted(() => ({
  patch: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  default: {
    patch,
  },
}))

import { useUpdatePortfolio } from './usePortfolios'

describe('useUpdatePortfolio', () => {
  beforeEach(() => {
    patch.mockReset()
  })

  it('usa PATCH e invalida a lista de carteiras', async () => {
    patch.mockResolvedValue({
      data: {
        id: 7,
        user_id: 1,
        name: 'Carteira renomeada',
        description: null,
        is_active: true,
        created_at: '2026-07-13T00:00:00Z',
        updated_at: '2026-07-13T00:00:00Z',
      },
    })

    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const invalidate = vi.spyOn(client, 'invalidateQueries')

    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useUpdatePortfolio(), { wrapper })

    await result.current.mutateAsync({ id: 7, name: 'Carteira renomeada' })

    expect(patch).toHaveBeenCalledWith('/portfolios/7', {
      name: 'Carteira renomeada',
    })
    await waitFor(() => expect(invalidate).toHaveBeenCalled())
  })
})
