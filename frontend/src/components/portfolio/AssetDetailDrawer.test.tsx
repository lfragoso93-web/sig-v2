import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { CorporateLifecycleEvent } from '@/hooks/useAssetDetail'
import type { PositionGroup } from '@/hooks/usePortfolio'
import AssetDetailDrawer from './AssetDetailDrawer'

const mocks = vi.hoisted(() => ({
  corporateLifecycle: [] as CorporateLifecycleEvent[],
  dividends: [] as Array<{
    id: number
    portfolio_id: number
    ticker: string
    type: string
    amount: number
    payment_date: string
    date: string
  }>,
  enrichment: undefined as any,
}))

vi.mock('@/hooks/useAssetDetail', () => ({
  useAssetDetail: () => ({ data: undefined, isLoading: false }),
  useAssetCorporateLifecycle: () => ({ data: mocks.corporateLifecycle }),
  useAssetEnrichment: () => ({ data: mocks.enrichment, isLoading: false }),
  useAssetPortfolioInsights: () => ({ data: undefined, isLoading: false }),
}))

vi.mock('@/hooks/useTransactions', () => ({
  useTransactions: () => ({ data: { items: [] } }),
}))

vi.mock('@/hooks/useDividends', () => ({
  useDividends: () => ({ data: mocks.dividends }),
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

const asset = {
  id: 34,
  ticker: 'NIKE34',
  asset_type: 'BDR',
  asset_label: 'BDR',
  quantity: 1,
  average_price: 147.04,
  current_price: 150,
  current_value: 150,
  invested_value: 147.04,
  variation_value: 2.96,
  variation_percent: 2.01,
  allocation_pct: 100,
} as PositionGroup['positions'][number]

describe('AssetDetailDrawer corporate lifecycle', () => {
  it('renders portfolio dividends in the asset detail', () => {
    mocks.dividends = [{
      id: 7,
      portfolio_id: 15,
      ticker: 'NIKE34',
      type: 'DIVIDENDO',
      amount: 10,
      payment_date: '2026-10-01',
      date: '2026-09-20',
    }]

    render(<AssetDetailDrawer asset={asset} portfolioId={15} onClose={vi.fn()} />)

    expect(screen.getByText('Proventos (1)')).toBeTruthy()
    expect(screen.getByText('DIVIDENDO')).toBeTruthy()
    expect(screen.getByText('01/10/2026')).toBeTruthy()
    expect(screen.getAllByText(/R\$\s*10,00/)).toHaveLength(2)
  })

  beforeEach(() => {
    mocks.corporateLifecycle = []
    mocks.dividends = []
    mocks.enrichment = undefined
  })

  it('mostra a verdade econômica da venda da fração', () => {
    mocks.corporateLifecycle = [{
      source_event_id: 'nike34-grouping',
      ticker: 'NIKE34',
      event_date: '2026-10-13',
      event_type: 'GRUPAMENTO',
      quantity_factor: 0.2,
      fractional_quantity: 0.2,
      settlement_status: 'SETTLED',
      unit_settlement_price_brl: 80,
      gross_amount_brl: 16,
      cost_basis_brl: 29.41,
      realized_pnl_brl: -13.41,
      cash_treatment: 'AUCTION_SETTLEMENT',
      message: 'Fração vendida e valor creditado ao usuário.',
    }]

    render(<AssetDetailDrawer asset={asset} portfolioId={15} onClose={vi.fn()} />)

    expect(screen.getByText('Eventos corporativos (1)')).toBeTruthy()
    expect(screen.getByText('GRUPAMENTO · fator 0,2')).toBeTruthy()
    expect(screen.getByText('13/10/2026')).toBeTruthy()
    expect(screen.getByText('Fração vendida e valor creditado ao usuário.')).toBeTruthy()
    expect(screen.getByText(/Fração vendida: 0,2/).textContent).toMatch(
      /Valor creditado: R\$\s16,00/,
    )
    expect(screen.getByText(/Resultado realizado: -R\$\s13,41/)).toBeTruthy()
  })

  it('informa fração pendente sem apresentar crédito ou resultado realizado', () => {
    mocks.corporateLifecycle = [{
      source_event_id: 'pending-fraction',
      ticker: 'NIKE34',
      event_date: '2026-10-13',
      event_type: 'GRUPAMENTO',
      quantity_factor: 0.2,
      fractional_quantity: 0.2,
      settlement_status: 'PENDING_VALUE',
      unit_settlement_price_brl: null,
      gross_amount_brl: null,
      cost_basis_brl: null,
      realized_pnl_brl: null,
      cash_treatment: null,
      message: 'Fração pendente de liquidação; valor ainda não confirmado.',
    }]

    render(<AssetDetailDrawer asset={asset} portfolioId={15} onClose={vi.fn()} />)

    expect(screen.getByText('Fração pendente de liquidação; valor ainda não confirmado.')).toBeTruthy()
    expect(screen.getByText(/Fração pendente: 0,2/)).toBeTruthy()
    expect(screen.queryByText(/Valor creditado/)).toBeNull()
    expect(screen.queryByText(/Resultado realizado/)).toBeNull()
  })

  it('não apresenta evento não reconciliado como aplicado', () => {
    render(<AssetDetailDrawer asset={asset} portfolioId={15} onClose={vi.fn()} />)

    expect(screen.queryByText(/Eventos corporativos/)).toBeNull()
    expect(screen.queryByText(/Fração vendida/)).toBeNull()
  })

  it('renderiza fundamentos específicos para ETF sem métricas irrelevantes de ações', async () => {
    const { fireEvent } = await import('@testing-library/react')
    mocks.enrichment = {
      ticker: 'BOVA11',
      asset_class: 'ETF',
      coverage_status: 'FULL',
      fii_indicators: null,
      stock_fundamentals: null,
      etf_indicators: {
        symbol: 'BOVA11',
        benchmark: 'Índice Bovespa (IBOV)',
        expense_ratio: 0.1,
        manager: 'BlackRock (iShares)',
        dividend_policy: 'Reinvestimento Automático de Proventos',
        dividend_yield: null,
        net_assets: 12000000000,
        category: 'Renda Variável Brasil',
      },
      dividend_history: [],
    }

    render(<AssetDetailDrawer asset={{ ...asset, ticker: 'BOVA11', asset_type: 'ETF_NACIONAL' }} portfolioId={15} onClose={vi.fn()} />)

    // Clica na aba Fundamentos
    fireEvent.click(screen.getByText('Fundamentos & Imóveis'))

    expect(screen.getByText('Características do Fundo de Índice (ETF)')).toBeTruthy()
    expect(screen.getByText('Índice Bovespa (IBOV)')).toBeTruthy()
    expect(screen.getByText('BlackRock (iShares)')).toBeTruthy()
    expect(screen.getByText('0,10% a.a.')).toBeTruthy()
    // Garante que métricas corporativas de ações não são exibidas
    expect(screen.queryByText('P/L (Preço / Lucro)')).toBeNull()
    expect(screen.queryByText('Margem Líquida')).toBeNull()
    expect(screen.queryByText('Dívida Líquida')).toBeNull()
  })

  it('renderiza histórico de proventos declarados na aba de fundamentos', async () => {
    const { fireEvent } = await import('@testing-library/react')
    mocks.enrichment = {
      ticker: 'PETR4',
      asset_class: 'ACAO',
      coverage_status: 'FULL',
      fii_indicators: null,
      stock_fundamentals: {
        pe: 4.5,
        pb: 1.1,
        dividend_yield: 12.5,
        eps: 8.2,
        market_cap: 500000000000,
        net_revenue: 400000000000,
        net_income: 100000000000,
        ebitda: 150000000000,
        net_margin: 25.0,
        roe: 28.0,
        net_debt: 200000000000,
      },
      dividend_history: [
        {
          payment_date: '2026-05-20',
          record_date: '2026-04-15',
          ex_date: '2026-04-16',
          type: 'DIVIDENDO',
          value: 1.35,
        },
      ],
      dividend_metrics: {
        total_paid_12m: 1.35,
        payments_count_12m: 1,
        last_payment_date: '2026-05-20',
        frequency: 'Eventual',
      },
    }

    render(<AssetDetailDrawer asset={{ ...asset, ticker: 'PETR4', asset_type: 'ACAO' }} portfolioId={15} onClose={vi.fn()} />)

    fireEvent.click(screen.getByText('Fundamentos & Imóveis'))

    expect(screen.getByText('Histórico de Proventos Declarados')).toBeTruthy()
    expect(screen.getByText('Últimas distribuições de dividendos, JCP ou rendimentos por cota')).toBeTruthy()
    expect(screen.getByText('1 proventos')).toBeTruthy()
    expect(screen.getByText('Eventual')).toBeTruthy()
    expect(screen.getByText('Data Com')).toBeTruthy()
    expect(screen.getByText('Data Pag')).toBeTruthy()
    expect(screen.getByText('Valor Unitário')).toBeTruthy()
    expect(screen.getByText('15/04/2026')).toBeTruthy()
    expect(screen.getByText('20/05/2026')).toBeTruthy()
    expect(screen.getAllByText(/R\$\s*1,35/)).toHaveLength(2)
  })

})
