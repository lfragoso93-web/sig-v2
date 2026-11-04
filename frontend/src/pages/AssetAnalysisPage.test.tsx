import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AssetAnalysisPage from './AssetAnalysisPage'
import api from '@/services/api'

vi.mock('@/services/api', () => ({ default: { get: vi.fn() } }))

describe('AssetAnalysisPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('searches the catalog and displays available cached analysis', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/assets/search') return { data: [{ id: 7, ticker: 'PETR4', name: 'Petrobras', asset_type: 'ACAO' }] }
      return { data: {
        asset: { id: 7, ticker: 'PETR4', name: 'Petrobras', asset_type: 'ACAO', currency: 'BRL', last_price: 37.5 },
        enrichment: { ticker: 'PETR4', asset_class: 'ACAO', coverage_status: 'PARTIAL', stock_fundamentals: { pe: 5.2, roe: 0.2 }, dividend_history: [] },
        price_history: [{ timestamp: '2026-11-03', close: 37.5 }],
        dividends: [], corporate_events: [], reports: [],
      } }
    })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><AssetAnalysisPage /></QueryClientProvider>)

    fireEvent.change(screen.getByLabelText('Buscar ativo por ticker ou nome'), { target: { value: 'PE' } })
    fireEvent.click(await screen.findByRole('button', { name: /PETR4.*Petrobras/ }))

    expect(await screen.findByText('Fundamentos de ações')).toBeDefined()
    expect(screen.getByText('5,2')).toBeDefined()
    expect(screen.getByText(/não consulta provedores ao abrir/i)).toBeDefined()
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/assets/analysis/7'))
  })
})
