import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PendingCorporateFractionsPanel from './PendingCorporateFractionsPanel'

const mocks = vi.hoisted(() => ({ fractions: [] as unknown[] }))

vi.mock('@/hooks/usePortfolio', () => ({
  usePendingCorporateFractions: () => ({
    data: mocks.fractions,
    isLoading: false,
    error: null,
  }),
}))

describe('PendingCorporateFractionsPanel', () => {
  it('mostra quantidade pendente e deixa o valor como não confirmado', () => {
    mocks.fractions = [{
      source_event_id: 'b3:nike34',
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
      message: 'Aguardando leilão.',
    }]

    render(<PendingCorporateFractionsPanel portfolioId={15} />)

    expect(screen.getByText('Frações pendentes de liquidação')).toBeTruthy()
    expect(screen.getByText('NIKE34')).toBeTruthy()
    expect(screen.getByText('0,2')).toBeTruthy()
    expect(screen.getByText('A confirmar')).toBeTruthy()
    expect(screen.getByText(/calculada pela quantidade da sua carteira/)).toBeTruthy()
    expect(screen.queryByText(/R\$/)).toBeNull()
  })

  it('não ocupa espaço quando não há frações pendentes', () => {
    mocks.fractions = []
    const { container } = render(<PendingCorporateFractionsPanel portfolioId={15} />)
    expect(container.firstChild).toBeNull()
  })
})
