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
}))

vi.mock('@/hooks/useAssetDetail', () => ({
  useAssetDetail: () => ({ data: undefined, isLoading: false }),
  useAssetCorporateLifecycle: () => ({ data: mocks.corporateLifecycle }),
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
})
