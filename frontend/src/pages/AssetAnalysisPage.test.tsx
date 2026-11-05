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
        asset: { id: 7, ticker: 'PETR4', name: 'Petrobras', asset_type: 'ACAO', currency: 'BRL', last_price: 37.5, last_price_updated_at: '2026-11-03T18:00:00Z', sector: 'Energia' },
        enrichment: { ticker: 'PETR4', asset_class: 'ACAO', coverage_status: 'PARTIAL', stock_fundamentals: { pe: 5.2, roe: 0.2, market_cap: 1_000_000 }, dividend_metrics: { dy_12m: 8.4 }, capabilities: { price_history: true }, dividend_history: [] },
        price_history: [{ timestamp: '2026-11-03', close: 37.5, volume: 1000 }],
        dividends: [{ ex_date: '2026-10-01', value_per_unit: 0.5, type: 'DIVIDEND' }],
        corporate_events: [{ event_type: 'SPLIT', effective_date: '2026-08-10', requires_review: false }], reports: [],
      } }
    })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><AssetAnalysisPage /></QueryClientProvider>)

    fireEvent.change(screen.getByLabelText('Encontre um ativo no catálogo'), { target: { value: 'PE' } })
    fireEvent.click(await screen.findByRole('button', { name: /PETR4.*Petrobras/ }))

    expect(await screen.findByRole('heading', { name: 'Fundamentos e indicadores' })).toBeDefined()
    expect(screen.getByText('Cobertura parcial')).toBeDefined()
    expect(screen.getByText('Fundamentos de ações')).toBeDefined()
    expect(screen.getByText('5,2')).toBeDefined()
    expect(screen.getAllByText(/R\$\s?37,50/)).toHaveLength(2)
    expect(screen.getByText(/R\$\s?1\.000\.000,00/)).toBeDefined()
    expect(screen.getByText(/R\$\s?0,50/)).toBeDefined()
    expect(screen.getByRole('link', { name: /Histórico/ }).getAttribute('href')).toBe('#historico')
    expect(screen.getByRole('heading', { name: 'Eventos corporativos' })).toBeDefined()
    expect(screen.getByText('Nenhum relatório vinculado')).toBeDefined()
    expect(screen.getByText(/dados informativos armazenados no sistema/i)).toBeDefined()
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/assets/analysis/7'))
  })

  it('formats international asset values in the asset currency', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/assets/search') return { data: [{ id: 9, ticker: 'AAPL', name: 'Apple Inc.', asset_type: 'STOCK' }] }
      return { data: {
        asset: { id: 9, ticker: 'AAPL', name: 'Apple Inc.', asset_type: 'STOCK', currency: 'USD', last_price: 100 },
        enrichment: { ticker: 'AAPL', asset_class: 'STOCK', coverage_status: 'FULL', stock_fundamentals: { target_price: 120, market_cap_usd: 2_000_000 } },
        price_history: [], dividends: [], corporate_events: [], reports: [],
      } }
    })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><AssetAnalysisPage /></QueryClientProvider>)

    fireEvent.change(screen.getByLabelText('Encontre um ativo no catálogo'), { target: { value: 'AA' } })
    fireEvent.click(await screen.findByRole('button', { name: /AAPL.*Apple Inc/ }))

    expect(await screen.findByText(/US\$\s?100,00/)).toBeDefined()
    expect(screen.getByText(/US\$\s?2\.000\.000,00/)).toBeDefined()
    expect(screen.getByText(/Moeda de negociação: USD/)).toBeDefined()
    expect(screen.getByText('Cobertura completa')).toBeDefined()
  })

  it('preserves precision for very small crypto prices', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/assets/search') return { data: [{ id: 12, ticker: 'SHIB', name: 'Shiba Inu', asset_type: 'CRIPTO' }] }
      return { data: {
        asset: { id: 12, ticker: 'SHIB', name: 'Shiba Inu', asset_type: 'CRIPTO', currency: 'BTC', last_price: 0.00001234 },
        enrichment: { ticker: 'SHIB', asset_class: 'CRIPTO', coverage_status: 'UNSUPPORTED', crypto_indicators: { price_brl: 0.00001234 } },
        price_history: [{ timestamp: '2026-11-03', close: 0.00001234 }], dividends: [], corporate_events: [], reports: [],
      } }
    })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><AssetAnalysisPage /></QueryClientProvider>)

    fireEvent.change(screen.getByLabelText('Encontre um ativo no catálogo'), { target: { value: 'SH' } })
    fireEvent.click(await screen.findByRole('button', { name: /SHIB.*Shiba Inu/ }))

    expect(await screen.findByText('Cobertura não suportada')).toBeDefined()
    expect(screen.getByText(/R\$\s?0,00001234/)).toBeDefined()
    expect(screen.getAllByText(/BTC\s?0,00001234/).length).toBeGreaterThanOrEqual(1)
  })
})
