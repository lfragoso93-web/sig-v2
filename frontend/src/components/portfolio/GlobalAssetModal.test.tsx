import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { AssetPortfolioInsightResponse, AssetEnrichment } from '@/hooks/useAssetDetail'
import AssetDetailDrawer from './AssetDetailDrawer'

const mockInsight: AssetPortfolioInsightResponse = {
  ticker: 'PETR4',
  portfolio_id: 15,
  position: {
    is_held: true,
    quantity: 500,
    average_price: 30.0,
    invested_value: 15000.0,
    current_price: 40.0,
    current_value: 20000.0,
    capital_gain_value: 5000.0,
    capital_gain_percent: 33.33,
    dividends_received: 2000.0,
    total_return_value: 7000.0,
    total_return_percent: 46.67,
    portfolio_weight_percent: 20.0,
    class_weight_percent: 50.0,
    class_name: 'ACAO',
    class_label: 'Ações',
    class_current_allocation_percent: 40.0,
    class_target_percent: 30.0,
    yield_on_cost_percent: 13.33,
  },
  enrichment: {
    ticker: 'PETR4',
    coverage_status: 'FULL',
    fii_indicators: null,
    stock_fundamentals: {
      pe: 4.5,
      pb: 1.2,
      dividend_yield: 12.5,
      eps: 8.8,
      market_cap: 500000000000,
      net_revenue: 400000000000,
      net_income: 110000000000,
      ebitda: 180000000000,
      net_margin: 27.5,
      roe: 28.0,
      net_debt: 200000000000,
    },
  },
  ai_insights: {
    concentration_level: 'HIGH',
    concentration_message: 'Atenção: PETR4 representa 20.0% de todo o patrimônio da carteira.',
    income_assessment: 'Excelente geração de renda com Yield on Cost de 13.33%.',
    rebalancing_guidance: 'A classe Ações está sobre-alocada.',
    strategic_role: 'Empresa madura e geradora de caixa com distribuição relevante de dividendos/JCP.',
    explainable_summary: 'PETR4 cumpre o papel de empresa geradora de caixa e renda passiva.',
  },
}

vi.mock('@/hooks/useAssetDetail', () => ({
  useAssetDetail: () => ({
    data: {
      id: 1,
      ticker: 'PETR4',
      name: 'Petróleo Brasileiro S.A.',
      asset_type: 'ACAO',
      current_price: 40.0,
      price_history: [],
    },
    isLoading: false,
  }),
  useAssetCorporateLifecycle: () => ({ data: [] }),
  useAssetEnrichment: () => ({ data: mockInsight.enrichment }),
  useAssetPortfolioInsights: () => ({ data: mockInsight }),
}))

vi.mock('@/hooks/useTransactions', () => ({
  useTransactions: () => ({ data: { items: [] } }),
}))

vi.mock('@/hooks/useDividends', () => ({
  useDividends: () => ({ data: [] }),
}))

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => children,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

describe('GlobalAssetModal / AssetDetailDrawer enhancements (Issue #58)', () => {
  it('renders centralized dialog with tabs and switches between them', () => {
    render(<AssetDetailDrawer ticker="PETR4" portfolioId={15} onClose={vi.fn()} />)

    // Dialog role
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(screen.getByText('PETR4')).toBeTruthy()

    // 4 Tabs are present
    expect(screen.getByText('Visão Geral & Preço')).toBeTruthy()
    expect(screen.getByText('Na Minha Carteira')).toBeTruthy()
    expect(screen.getByText('Fundamentos & Imóveis')).toBeTruthy()
    expect(screen.getByText('Insights com IA')).toBeTruthy()

    // Switch to Tab: Na Minha Carteira
    fireEvent.click(screen.getByText('Na Minha Carteira'))
    expect(screen.getByText('Posição em Custódia')).toBeTruthy()
    expect(screen.getByText(/500,00 cotas/)).toBeTruthy()
    expect(screen.getByText('Ganho de Capital')).toBeTruthy()
    expect(screen.getByText('Peso no Portfólio Global')).toBeTruthy()
    expect(screen.getByText(/13,33%/)).toBeTruthy() // YoC

    // Switch to Tab: Fundamentos & Imóveis
    fireEvent.click(screen.getByText('Fundamentos & Imóveis'))
    expect(screen.getByText('Métricas de Valuation da Ação')).toBeTruthy()
    expect(screen.getByText('P/L (Preço / Lucro)')).toBeTruthy()
    expect(screen.getByText('4,50')).toBeTruthy()

    // Switch to Tab: Insights com IA
    fireEvent.click(screen.getByText('Insights com IA'))
    expect(screen.getByText('Diagnóstico Estratégico com IA')).toBeTruthy()
    expect(screen.getByText(/PETR4 cumpre o papel de empresa geradora de caixa/)).toBeTruthy()
    expect(screen.getByText('Concentração & Risco')).toBeTruthy()
    expect(screen.getByText('HIGH')).toBeTruthy()
  })
})
