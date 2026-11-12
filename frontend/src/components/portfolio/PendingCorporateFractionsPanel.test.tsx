import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PendingCorporateFractionsPanel from './PendingCorporateFractionsPanel'

const mocks = vi.hoisted(() => ({
  fractions: [] as unknown[],
  rights: [] as unknown[],
  settlements: [] as unknown[],
  upsertAsync: vi.fn(),
  deleteAsync: vi.fn(),
}))

vi.mock('@/hooks/usePortfolio', () => ({
  usePendingCorporateFractions: () => ({
    data: mocks.fractions,
    isLoading: false,
    error: null,
  }),
  usePortfolioCorporateRights: () => ({ data: mocks.rights }),
  useCorporateFractionSettlements: () => ({ data: mocks.settlements }),
  useUpsertCorporateFractionSettlement: () => ({
    mutateAsync: mocks.upsertAsync,
    isPending: false,
  }),
  useDeleteCorporateFractionSettlement: () => ({
    mutateAsync: mocks.deleteAsync,
    isPending: false,
  }),
}))

describe('PendingCorporateFractionsPanel', () => {
  beforeEach(() => {
    mocks.fractions = []
    mocks.rights = []
    mocks.settlements = []
    mocks.upsertAsync.mockReset().mockResolvedValue({})
    mocks.deleteAsync.mockReset().mockResolvedValue({})
  })

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
    expect(screen.getByRole('button', { name: /Informar leilão/i })).toBeTruthy()
    expect(screen.queryByText(/R\$/)).toBeNull()
  })

  it('permite informar manualmente o valor do leilão para fração pendente', async () => {
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

    fireEvent.click(screen.getByRole('button', { name: /Informar leilão/i }))
    fireEvent.change(screen.getByLabelText(/Valor recebido no leilão/i), {
      target: { value: '25,40' },
    })
    fireEvent.change(screen.getByLabelText(/Data do crédito/i), {
      target: { value: '2026-10-20' },
    })
    fireEvent.change(screen.getByLabelText(/Observação/i), {
      target: { value: 'Extrato corretora' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Salvar liquidação/i }))

    await waitFor(() => {
      expect(mocks.upsertAsync).toHaveBeenCalledWith({
        source_event_id: 'b3:nike34',
        gross_amount_brl: 25.4,
        settlement_date: '2026-10-20',
        notes: 'Extrato corretora',
      })
    })
  })

  it('preserva a data de crédito e observação salvas ao editar liquidação confirmada', async () => {
    mocks.fractions = [{
      source_event_id: 'b3:nike34',
      ticker: 'NIKE34',
      event_date: '2026-10-13',
      event_type: 'GRUPAMENTO',
      quantity_factor: 0.2,
      fractional_quantity: 0.2,
      settlement_status: 'SETTLED',
      unit_settlement_price_brl: 127,
      gross_amount_brl: 25.4,
      cost_basis_brl: 30.0,
      realized_pnl_brl: -4.6,
      cash_treatment: 'PORTFOLIO_USER_CONFIRMED_AUCTION',
      message: 'Fração vendida e valor creditado ao usuário.',
    }]
    mocks.settlements = [{
      id: 1,
      portfolio_id: 15,
      source_event_id: 'b3:nike34',
      ticker: 'NIKE34',
      gross_amount_brl: 25.4,
      settlement_date: '2026-10-21',
      notes: 'Extrato salvo',
      cash_treatment: 'PORTFOLIO_USER_CONFIRMED_AUCTION',
      event_date: '2026-10-21',
    }]

    render(<PendingCorporateFractionsPanel portfolioId={15} />)

    fireEvent.click(screen.getByRole('button', { name: /Editar/i }))
    expect((screen.getByLabelText(/Data do crédito/i) as HTMLInputElement).value).toBe('2026-10-21')
    expect((screen.getByLabelText(/Observação/i) as HTMLInputElement).value).toBe('Extrato salvo')
    fireEvent.change(screen.getByLabelText(/Valor recebido no leilão/i), {
      target: { value: '26,00' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Salvar liquidação/i }))

    await waitFor(() => {
      expect(mocks.upsertAsync).toHaveBeenCalledWith({
        source_event_id: 'b3:nike34',
        gross_amount_brl: 26,
        settlement_date: '2026-10-21',
        notes: 'Extrato salvo',
      })
    })
  })

  it('permite limpar uma liquidação confirmada manualmente', async () => {
    mocks.fractions = [{
      source_event_id: 'b3:nike34',
      ticker: 'NIKE34',
      event_date: '2026-10-13',
      event_type: 'GRUPAMENTO',
      quantity_factor: 0.2,
      fractional_quantity: 0.2,
      settlement_status: 'SETTLED',
      unit_settlement_price_brl: 127,
      gross_amount_brl: 25.4,
      cost_basis_brl: 30.0,
      realized_pnl_brl: -4.6,
      cash_treatment: 'PORTFOLIO_USER_CONFIRMED_AUCTION',
      message: 'Fração vendida e valor creditado ao usuário.',
    }]

    render(<PendingCorporateFractionsPanel portfolioId={15} />)

    expect(screen.getByText(/25,40/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Remover liquidação de NIKE34/i }))

    await waitFor(() => {
      expect(mocks.deleteAsync).toHaveBeenCalledWith('b3:nike34')
    })
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
    expect(screen.getByRole('button', { name: /Confirmar valor/i })).toBeTruthy()
  })

  it('mostra o valor do leilão liquidado para frações liquidadas', () => {
    mocks.fractions = [{
      source_event_id: 'b3:klbn-leilao-2026',
      ticker: 'KLBN11',
      event_date: '2026-03-01',
      event_type: 'GRUPAMENTO',
      quantity_factor: 1.0,
      fractional_quantity: 0.1,
      settlement_status: 'SETTLED',
      unit_settlement_price_brl: 3.94,
      gross_amount_brl: 0.39,
      cost_basis_brl: 1.29,
      realized_pnl_brl: -0.90,
      cash_treatment: 'PRO_RATA_AUCTION',
      message: 'Fração vendida e valor creditado ao usuário.',
    }]
    mocks.rights = []

    render(<PendingCorporateFractionsPanel portfolioId={15} />)

    expect(screen.getByText('KLBN11')).toBeTruthy()
    expect(screen.getByText('0,1')).toBeTruthy()
    expect(screen.getByText(/Leilão liquidado/)).toBeTruthy()
    expect(screen.getByText(/0,39/)).toBeTruthy()
  })
})
