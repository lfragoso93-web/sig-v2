import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import api from '@/services/api'
import { useDividends } from './useDividends'

vi.mock('@/services/api', () => ({ default: { get: vi.fn() } }))

describe('useDividends', () => {
  it('reads portfolio dividend projections from the supported endpoint', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [{
        id: 7,
        portfolio_id: 15,
        ticker: 'NIKE34',
        ex_date: '2026-09-20',
        payment_date: null,
        dividend_type: 'DIVIDENDO',
        total_received: 10,
      }],
    })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDividends(15), { wrapper })

    await waitFor(() => expect(result.current.data).toHaveLength(1))
    expect(api.get).toHaveBeenCalledWith('/portfolios/15/dividends')
    expect(result.current.data?.[0]).toMatchObject({
      ticker: 'NIKE34',
      type: 'DIVIDENDO',
      amount: 10,
      payment_date: '2026-09-20',
    })
    client.clear()
  })
})
