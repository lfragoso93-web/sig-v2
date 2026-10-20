import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PendingCorporateFractionsPanel from './PendingCorporateFractionsPanel'

const mocks = vi.hoisted(() => ({
  fractions: [] as unknown[],
  rights: [] as unknown[],
}))

vi.mock('@/hooks/usePortfolio', () => ({
  usePendingCorporateFractions: () => ({
    data: mocks.fractions,
    isLoading: false,
    error: null,
  }),
  usePortfolioCorporateRights: () => ({ data: mocks.rights }),
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

    expect(screen.getByText('Calendário de Eventos Corporativos')).toBeTruthy()
    expect(screen.getByText('NIKE34')).toBeTruthy()
    expect(screen.getByText('0,2')).toBeTruthy()
    expect(screen.getByText('A confirmar')).toBeTruthy()
    expect(screen.getByText(/calculada pela quantidade da sua carteira/)).toBeTruthy()
    expect(screen.queryByText(/R\$/)).toBeNull()
  })

  it('não ocupa espaço quando não há frações pendentes', () => {
    mocks.fractions = []
    mocks.rights = []
    const { container } = render(<PendingCorporateFractionsPanel portfolioId={15} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows the attributed fractional cost and estimated result', () => {
    mocks.fractions = []
    mocks.rights = [{
      event_id: 81,
      source_event_id: 'b3:klbn-bonus-2025',
      ticker: 'KLBN11',
      event_type: 'BONIFICACAO',
      record_date: '2025-12-17',
      settlement_date: '2026-02-24',
      base_position: 10,
      settlement_status: 'AVAILABLE',
      components: [{
        component: 'ON',
        bonus_quantity: 0.1,
        whole_quantity: 0,
        fractional_quantity: 0.1,
        whole_units_formed: 0,
        component_shares_in_units: 0,
        residual_whole_quantity: 0,
        settlement_price_brl: 3.942352337,
        gross_amount_brl: 0.3942352337,
        attributed_cost_brl: 1.294564988922,
        fractional_cost_basis_brl: 1.294564988922,
        estimated_fractional_result_brl: -0.900329755222,
      }],
      gross_amount_brl: 1.9712797185,
      calculated_gross_amount_brl: 1.9712797185,
      bonus_cost_per_share_brl: 12.94564988922,
      attributed_bonus_cost_brl: 6.47282494461,
      fractional_cost_basis_brl: 6.47282494461,
      estimated_fractional_result_brl: -4.50154522611,
      cash_status: 'CALCULATED_NOT_CONFIRMED',
      cash_treatment: 'PRO_RATA_AUCTION_RIGHT',
      evidence_reference: 'issuer:klbn:bonus-and-auction:2025',
    }]

    render(<PendingCorporateFractionsPanel portfolioId={15} />)

    expect(screen.getByText('Custo atribuído à fração')).toBeTruthy()
    expect(screen.getByText('Resultado estimado')).toBeTruthy()
    expect(screen.getByText(/crédito individual não confirmado/)).toBeTruthy()
    expect(screen.getAllByText(/1,29/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/-0,90/).length).toBeGreaterThan(0)
  })
})
